"""
Bulk-import UTC Bushenyi's HEMIS exports into the database.

WHAT THIS DOES
  1. GROUP USERS - STAFF PORTAL (.pdf)      -> User + StaffRole
  2. ALL_Programmes.xlsx                    -> Department, Course
  3. STUDENTS-DATA-TEMPLATE*.xlsx (any #)   -> Faculty, Course, Campus,
                                                AcademicYear, Semester, Intake,
                                                User + StudentProfile + StudentTermFee
  4. COURSE-UNIT-REPORT.xlsx                -> Department, CourseUnit

  ALL_Programmes.xlsx is processed before the student/course-unit files so its
  richer Department/Course records (department names, approval status, study
  level, award, duration measure, etc.) exist first — the other two imports
  then match against those records by code instead of creating bare placeholders.

WHERE TO PUT THIS FILE
  <your_app>/management/commands/import_hemis_data.py
  (create empty __init__.py in both management/ and management/commands/
  if they don't already exist)

  Then update the import below:
      from <your_app>.models import (...)
  to point at the app that actually holds these models.

HOW TO RUN
  python manage.py import_hemis_data                       # uses ~/Downloads
  python manage.py import_hemis_data --dir /path/to/files
  python manage.py import_hemis_data --dry-run              # parse only, write nothing
  python manage.py import_hemis_data --no-emails             # skip staff emails, CSV only
  python manage.py import_hemis_data --no-student-csv        # skip the student CSV
  python manage.py import_hemis_data --test-email you@x.com  # redirect all staff emails to you@x.com
  python manage.py import_hemis_data --no-test-email         # force real staff addresses this run

CREDENTIAL DELIVERY
  * Staff (teacher, HOD, dean, registrar, admin, etc.) accounts are emailed
    their username + a freshly generated random password, using whatever
    email backend is already configured in settings.py. EVERY newly created
    staff account - whether its email was sent successfully, failed to send,
    or was never attempted (--no-emails) - is ALSO written to a
    staff_credentials_fallback_<timestamp>.csv file in --dir, tagged with an
    email_status column ('sent' / 'failed' / 'skipped_no_emails'). This is a
    deliberate belt-and-suspenders: a successful send is never a reason to
    lose the only record of a plaintext temporary password.
  * TEST_EMAIL_OVERRIDE (near the top of this file) can redirect every staff
    credential email to one test address instead of each staff member's real
    .email, e.g. while testing the send path. Set it to None to send to real
    addresses again, or leave it set and pass --no-test-email for a one-off
    real run without editing the file. The fallback CSV always records the
    real staff email regardless of this setting.
  * Student accounts are never emailed. Every created student's name and
    password (their registration number - see PASSWORD POLICY below) is
    written to a student_credentials_<timestamp>.csv file in --dir instead.
  * Both CSVs contain unhashed passwords - distribute securely and delete
    promptly. See --no-staff-fallback-file / --no-student-csv to suppress
    either file.

PASSWORD POLICY
  * Students: username AND password are both the student's registration
    number.
  * Everyone else: a unique, randomly generated password per account (see
    generate_strong_password()) - nobody shares a role-wide password.

REQUIREMENTS
  pip install openpyxl pdfplumber
  A working email backend configured in settings.py (EMAIL_BACKEND,
  EMAIL_HOST*, DEFAULT_FROM_EMAIL) for staff credential emails to send.
"""

import csv
import glob
import os
import re
import secrets
import string
from datetime import date, timedelta

import openpyxl
import pdfplumber

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from attendance.models import (
    User, StaffRole, StudentProfile, StudentTermFee,
    Institution, Faculty, Department, Course, CourseUnit,
    Campus, AcademicYear, AcademicTerm, Semester, Intake,
)


# ==================== CONFIGURATION & CONSTANTS ====================

# Password policy
# ----------------
#   * Students   -> username AND password are both the student's registration
#                   number (see safe_username()/import_student_file()). This
#                   intentionally trades password secrecy for something every
#                   student already has memorized; advise students to change
#                   it on first login if your app supports that.
#   * Every other role (teacher, HOD, dean, registrar, admin, etc.) gets its
#     own randomly generated password at account-creation time - see
#     generate_strong_password(). Nobody shares a role-wide password anymore,
#     so compromising one account never exposes the rest. The generated
#     password is only ever available at creation time via the credentials
#     CSV report, so distribute and then purge that file promptly.
STRONG_PASSWORD_LENGTH = 14
STRONG_PASSWORD_SPECIALS = '!@#$%^&*()-_=+'

# Credential delivery
# -------------------
#   * Staff (teachers, HODs, deans, registrars, admins, etc.) are emailed
#     their username + temporary password directly, using whatever email
#     backend is already configured in settings.py (EMAIL_BACKEND,
#     EMAIL_HOST*, DEFAULT_FROM_EMAIL). Regardless of whether that email
#     succeeds, fails (bad address, SMTP outage, etc.), or is never attempted
#     (--no-emails), the account's credentials are ALSO recorded in the
#     staff_credential_fallback CSV so a plaintext temporary password is
#     never lost to a send that silently didn't land, or to admin error -
#     see staff_credential_fallback in handle() below.
#   * Students are never emailed (their accounts are usually created in bulk
#     before they have a personal email on file). Instead every created
#     student's name + password (their registration number) is written to
#     one plain CSV file for the registrar/admin office to distribute.
# Edit SYSTEM_NAME to match your institution/portal's actual name.
SYSTEM_NAME = "UTC Bushenyi HEMIS Portal"

# Test-email override
# --------------------
#   * When set to an address, EVERY staff credential email is redirected to
#     that address instead of the real staff member's email - handy for
#     testing the send path without spamming real inboxes. The email
#     subject is tagged with the real recipient so you can still tell whose
#     credentials you're looking at, and the fallback CSV always carries the
#     real staff email regardless of this setting.
#   * Set this back to None to resume sending to each staff member's real
#     .email address (production behaviour).
#   * Can also be overridden per-run from the command line without touching
#     this constant - see --test-email / --no-test-email below.
TEST_EMAIL_OVERRIDE = "okellojm125@gmail.com"  # <- set to None for production

STAFF_EMAIL_SUBJECT = f"Your {SYSTEM_NAME} account"
STAFF_EMAIL_BODY_TEMPLATE = """\
Dear {display_name},

An account has been created for you on the {system_name}.

    Username: {username}
    Temporary password: {password}

Please log in and change this password as soon as possible. If you did not
expect this email, please contact the system administrator.

This is an automated message - please do not reply to it.
"""

ROLE_TEXT_TO_CODE = {
    'SYSTEM SUPPORT': User.IS_SYSTEM_SUPPORT,
    'SYSTEM ADMINISTRATOR': User.IS_SYSTEM_ADMIN,
    'ACADEMIC REGISTRAR': User.IS_REGISTRAR,
    'ASSISTANT ACADEMIC REGISTRAR': User.IS_ASSISTANT_REGISTRAR,
    'ASSISTANT REGISTRAR': User.IS_ASSISTANT_REGISTRAR,
    'LECTURER': User.IS_TEACHER,
    'HOD': User.IS_HOD,
    'DEAN OF STUDENTS': User.IS_DEAN,
    'FINANCE': User.IS_FINANCE,
    'ACCOUNTANT': User.IS_ACCOUNTANT,
    'POINT OF SERVICE': User.IS_POINT_OF_SERVICE,
    'PRINCIPAL': User.IS_PRINCIPAL,
    'WARDEN': User.IS_WARDEN,
    'LIBRARIAN': User.IS_LIBRARIAN,
    'ADMIN': User.IS_ADMIN,
    'PARENT': User.IS_PARENT,
}

TITLE_TEXT_TO_CODE = {
    'MR': 'MR.', 'MRS': 'MRS.', 'MISS': 'MISS',
    'DR': 'DR.', 'ENG': 'ENG.', 'PROF': 'PROF.',
}

ROMAN_TO_INT = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}

# Positional column mapping for STUDENTS-DATA-TEMPLATE.xlsx (1-indexed)
COL_NAME = 1
COL_GENDER = 2
COL_STUDENT_NUMBER = 3
COL_REG_NO = 4
COL_EMAIL = 5
COL_PHONE = 6
COL_SPONSORSHIP_TYPE = 7      # mislabelled "DATE OF BIRTH" in export
COL_SPONSORSHIP_SCHEME = 8    # mislabelled "DISTRICT" in export
COL_NATIONALITY = 9
COL_CAMPUS = 10
COL_PROGRAMME_TYPE = 11
COL_IS_ENROLLED = 12
COL_ENROLLMENT_TOKEN = 13
COL_ENROLLMENT_CONDITION = 14
COL_REGISTRATION_TYPE = 15
COL_REGISTRATION_STATUS = 16
COL_IS_REGISTERED = 17
COL_PROVISIONAL_REG_TYPE = 18
COL_REGISTRATION_CONDITION = 19
COL_TUITION_INVOICE = 20
COL_TUITION_PAID = 21
COL_TUITION_DUE = 22
COL_FUNCTIONAL_INVOICE = 23
COL_FUNCTIONAL_PAID = 24
COL_FUNCTIONAL_DUE = 25
COL_OTHER_INVOICE = 26
COL_OTHER_PAID = 27
COL_OTHER_DUE = 28
COL_TOTAL_INVOICED = 29
COL_TOTAL_PAID = 30

DATA_START_ROW = 4
TITLE_ROW, TITLE_COL = 1, 3

# Positional column mapping for ALL_Programmes.xlsx (1-indexed).
# Unlike the student template, this export has a real header row at row 1,
# so data starts at row 2.
PROG_COL_DEPARTMENT_ID = 1
PROG_COL_DEPARTMENT_CODE = 2
PROG_COL_DEPARTMENT_TITLE = 3
PROG_COL_PROGRAMME_CODE = 4
PROG_COL_PROGRAMME_TITLE = 5
PROG_COL_IS_MODULAR = 6
PROG_COL_CREATE_APPROVAL_STATUS = 7
PROG_COL_DURATION_MEASURE_ID = 8
PROG_COL_STUDY_LEVEL_ID = 9
PROG_COL_DURATION_MEASURE = 10
PROG_COL_DURATION_MEASURE_LABEL = 11
PROG_COL_STUDY_LEVEL = 12
PROG_COL_STUDY_LEVEL_LABEL = 13
PROG_COL_AWARD = 14
PROG_COL_AWARD_LABEL = 15
PROG_COL_VERSION_TITLE = 16

PROGRAMMES_DATA_START_ROW = 2  # row 1 is the header row


# ==================== UTILITY PARSING FUNCTIONS ====================

def clean(value):
    """None-safe string stripping; converts empty strings to None."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def parse_name_or_none(cell):
    return clean(cell)


def split_full_name(full_name):
    """Splits full name string into surname, first_name, and other_names."""
    parts = (full_name or '').split()
    surname = parts[0] if parts else ''
    first_name = parts[1] if len(parts) > 1 else ''
    other_names = ' '.join(parts[2:]) if len(parts) > 2 else ''
    return surname, first_name, other_names


def normalize_gender(raw):
    if not raw:
        return None
    raw = raw.strip().upper()
    if raw.startswith('M'):
        return 'MALE'
    if raw.startswith('F'):
        return 'FEMALE'
    return None


def normalize_title(raw):
    if not raw:
        return None
    key = raw.strip().upper().rstrip('.')
    return TITLE_TEXT_TO_CODE.get(key)


def to_decimal(value):
    if value in (None, ''):
        return 0
    if isinstance(value, (int, float)):
        return value
    digits = re.sub(r'[^\d.]', '', str(value))
    return float(digits) if digits else 0


def to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().upper() in ('YES', 'TRUE', '1')


def username_from_email(email):
    return email.strip().lower()


def safe_username(reg_or_student_number):
    return re.sub(r'[^\w.@+-]', '-', reg_or_student_number.strip())


def role_code_from_text(text):
    key = re.sub(r'\s*\d+\s*$', '', text.strip().upper())
    return ROLE_TEXT_TO_CODE.get(key)


def generate_strong_password(length=STRONG_PASSWORD_LENGTH):
    """Generates a cryptographically random password unique to one account.

    Guarantees at least one lowercase letter, one uppercase letter, one
    digit, and one special character, then fills the remainder from the
    full character set and shuffles - so every call produces a different,
    hard-to-guess password even for accounts created in the same batch.
    """
    if length < 8:
        length = 8

    required = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(STRONG_PASSWORD_SPECIALS),
    ]
    all_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + STRONG_PASSWORD_SPECIALS
    required += [secrets.choice(all_chars) for _ in range(length - len(required))]

    rng = secrets.SystemRandom()
    rng.shuffle(required)
    return ''.join(required)


def staff_display_name(user):
    parts = [p for p in (user.title, user.surname, user.other_names) if p]
    return ' '.join(parts) or user.username


def send_staff_credentials_email(user, plain_password, test_email=None):
    """Emails a newly created staff account its username + temporary password.

    If test_email is given, the message is redirected to that address
    instead of user.email (with the real recipient noted in the subject
    line), so the send path can be exercised without touching real staff
    inboxes. Pass test_email=None (the default) for production behaviour.

    Raises whatever exception the configured email backend raises (SMTP
    errors, connection failures, etc.) - the caller is responsible for
    catching it and falling back to the CSV log so credentials are never
    silently lost.
    """
    recipient = test_email or user.email
    subject = STAFF_EMAIL_SUBJECT
    if test_email:
        subject = f"[TEST - real recipient: {user.email}] {STAFF_EMAIL_SUBJECT}"
    body = STAFF_EMAIL_BODY_TEMPLATE.format(
        display_name=staff_display_name(user),
        system_name=SYSTEM_NAME,
        username=user.username,
        password=plain_password,
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=None,  # falls back to settings.DEFAULT_FROM_EMAIL
        recipient_list=[recipient],
        fail_silently=False,
    )


def parse_title_block(text):
    """Parses structural metadata from the spreadsheet title header block."""
    info = {
        'faculty_name': None, 'faculty_code': None,
        'academic_year': None, 'semester_roman': None, 'intake_month': None,
        'programme_name': None, 'programme_code': None, 'study_year': None,
    }
    lines = [l.strip() for l in (text or '').split('\n') if l.strip()]
    name_code_re = re.compile(r'^(.*?)\(([A-Z0-9]+)\)\s*$')

    for line in lines:
        upper = line.upper()
        if upper.startswith('SCHOOL:'):
            rest = line.split(':', 1)[1].strip()
            m = name_code_re.match(rest)
            if m:
                info['faculty_name'] = m.group(1).strip()
                info['faculty_code'] = m.group(2).strip()
        elif upper.startswith('ACADEMIC YEAR'):
            info['academic_year'] = line.split('YEAR', 1)[1].strip()
        elif upper.startswith('SEMESTER'):
            info['semester_roman'] = line.split()[-1].strip()
        elif upper.startswith('INTAKE'):
            info['intake_month'] = line.split()[-1].strip().upper()
        elif upper.startswith('PROGRAMME:'):
            rest = line.split(':', 1)[1].strip()
            m = name_code_re.match(rest)
            if m:
                info['programme_name'] = m.group(1).strip()
                info['programme_code'] = m.group(2).strip()
        elif upper.startswith('STUDY YEAR:'):
            digits = re.search(r'\d+', line)
            info['study_year'] = int(digits.group()) if digits else None

    return info


def entry_year_from_number(number):
    """Infers 4-digit entry academic year from student ID prefixes."""
    if not number:
        return None
    digits = re.match(r'(\d{2})', number.strip())
    if not digits:
        return None
    yy = int(digits.group(1))
    if 0 <= yy <= 79:
        return 2000 + yy
    return None


# ==================== LOOKUP AND CREATION HELPERS ====================

_academic_term_dates_warned = False


def get_or_create_academic_term(academic_year_str, semester_roman):
    global _academic_term_dates_warned
    term_code = f"SEMESTER_{ROMAN_TO_INT.get(semester_roman, 1)}"
    term, created = AcademicTerm.objects.get_or_create(
        academic_year=academic_year_str or 'UNKNOWN',
        term=term_code,
        defaults={
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=120),
        },
    )
    if created and not _academic_term_dates_warned:
        print("WARNING: AcademicTerm records created with PLACEHOLDER dates "
              "(today to +120 days). Update start/end dates via admin interface.")
        _academic_term_dates_warned = True
    return term


def get_or_create_academic_year(name):
    if not name:
        return None
    obj, _ = AcademicYear.objects.get_or_create(name=name)
    return obj


def get_or_create_semester(roman):
    if not roman:
        return None
    n = ROMAN_TO_INT.get(roman)
    if not n:
        return None
    obj, _ = Semester.objects.get_or_create(name=f'Semester {n}')
    return obj


def get_or_create_intake(month_word):
    if not month_word:
        return None
    obj, _ = Intake.objects.get_or_create(name=month_word.upper())
    return obj


def get_or_create_campus(name):
    if not name:
        return None
    obj, _ = Campus.objects.get_or_create(name=name.strip())
    return obj


def get_or_create_faculty(name, code):
    if not name and not code:
        return None
    obj, _ = Faculty.objects.get_or_create(
        code=code or None,
        defaults={'name': name or code},
    )
    return obj


def get_or_create_course(code, name):
    if not code:
        return None
    obj, _ = Course.objects.get_or_create(
        code=code, defaults={'name': name or code}
    )
    return obj


# ==================== INGESTION SUBSYSTEMS ====================

def import_group_users(pdf_path, dry_run, stats, send_emails=True, test_email=None):
    print(f"\n--- Processing Staff Directory: {os.path.basename(pdf_path)} ---")
    with pdfplumber.open(pdf_path) as pdf:
        rows = []
        for page in pdf.pages:
            for table in page.extract_tables():
                header, *body = table
                rows.extend(body)

    for row in rows:
        if not row or not row[0] or not row[0].strip().isdigit():
            continue
        _, title_raw, surname, other_names, email, phone, roles_raw, verified_raw, _ = (
            row + [None] * 9
        )[:9]

        email = clean(email)
        if not email:
            stats['staff_skipped'] += 1
            continue

        role_codes = []
        if roles_raw and roles_raw.strip() != '-':
            for chunk in roles_raw.split(';'):
                code = role_code_from_text(chunk)
                if code:
                    role_codes.append(code)
                else:
                    print(f"  WARNING: Unrecognized staff role '{chunk.strip()}' for {email}.")

        primary_role = role_codes[0] if role_codes else User.IS_STUDENT
        if not role_codes:
            print(f"  WARNING: {email} has no valid role code in export. Assign manually.")

        if dry_run:
            print(f"  [dry-run] Staff user evaluated: {email} (Roles: {role_codes or 'None'})")
            stats['staff_seen'] += 1
            continue

        with transaction.atomic():
            username = username_from_email(email)
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email},
            )
            user.email = email
            user.title = normalize_title(title_raw)
            user.surname = clean(surname)
            user.other_names = clean(other_names)
            user.phone_number = clean(phone)
            user.role = primary_role
            user.is_verified = to_bool(verified_raw)
            user.is_staff = True
            plain_password = None
            if created:
                plain_password = generate_strong_password()
                user.set_password(plain_password)
            user.save()

            StaffRole.objects.filter(user=user).exclude(role__in=role_codes).delete()
            for code in role_codes:
                StaffRole.objects.get_or_create(user=user, role=code)

            stats['staff_created' if created else 'staff_updated'] += 1

        # Send the email (or fall back to the CSV log) after the transaction
        # above has committed, so a slow/failing email backend never holds a
        # database transaction open.
        if created:
            if send_emails:
                try:
                    send_staff_credentials_email(user, plain_password, test_email=test_email)
                    stats['staff_emails_sent'] += 1
                    # Email succeeded, but still log to the fallback CSV as a safety
                    # net - a "sent" status here means "don't distribute this again",
                    # not "this row can be discarded". Losing the only copy of a
                    # plaintext temporary password to a send we can't fully verify
                    # (spam-filtered, bounced silently, wrong mailbox, etc.) is worse
                    # than one extra row in a file that gets purged after distribution.
                    stats['staff_credential_fallback'].append(
                        (username, email, primary_role, plain_password, 'sent')
                    )
                except Exception as exc:
                    print(f"  WARNING: Could not email credentials to {email} ({exc}). "
                          f"Falling back to CSV log for this account.")
                    stats['staff_emails_failed'] += 1
                    stats['staff_credential_fallback'].append(
                        (username, email, primary_role, plain_password, 'failed')
                    )
            else:
                stats['staff_credential_fallback'].append(
                    (username, email, primary_role, plain_password, 'skipped_no_emails')
                )


def import_student_file(xlsx_path, dry_run, stats):
    print(f"\n--- Processing Student Registry: {os.path.basename(xlsx_path)} ---")
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    title_text = ws.cell(row=TITLE_ROW, column=TITLE_COL).value
    meta = parse_title_block(title_text)
    study_year = meta['study_year'] or 1

    if dry_run:
        # Read-only lookups only: get_or_create_* below would otherwise write
        # Faculty/Course/AcademicYear/Semester/Intake/AcademicTerm rows even
        # during a "parse only" dry run. Use .filter().first() instead so a
        # dry run never touches the database.
        course = Course.objects.filter(code=meta['programme_code']).first() if meta['programme_code'] else None
        if not course:
            print(f"  WARNING: Course '{meta['programme_code']}' not yet in the database "
                  f"(dry-run; would be created/resolved by ALL_Programmes or this file on a "
                  f"real run) - {os.path.basename(xlsx_path)}.")
    else:
        faculty = get_or_create_faculty(meta['faculty_name'], meta['faculty_code'])
        course = get_or_create_course(meta['programme_code'], meta['programme_name'])
        academic_year = get_or_create_academic_year(meta['academic_year'])
        semester = get_or_create_semester(meta['semester_roman'])
        intake = get_or_create_intake(meta['intake_month'])
        academic_term = get_or_create_academic_term(meta['academic_year'], meta['semester_roman'])

        if not course:
            print(f"  ERROR: Could not resolve Course from header in {os.path.basename(xlsx_path)}. File skipped.")
            return

    for row_idx in range(DATA_START_ROW, ws.max_row + 1):
        name = parse_name_or_none(ws.cell(row=row_idx, column=COL_NAME).value)
        if not name:
            continue

        reg_no = clean(ws.cell(row=row_idx, column=COL_REG_NO).value)
        student_number = clean(ws.cell(row=row_idx, column=COL_STUDENT_NUMBER).value)
        email = clean(ws.cell(row=row_idx, column=COL_EMAIL).value)

        if not reg_no:
            print(f"  WARNING: Missing registration number on row {row_idx} ({name}) - record skipped.")
            stats['students_skipped'] += 1
            continue

        if dry_run:
            print(f"  [dry-run] Student record evaluated: {reg_no} ({name})")
            stats['students_seen'] += 1
            continue

        surname, first_name, other_names = split_full_name(name)
        entry_year = entry_year_from_number(student_number or reg_no)
        entry_academic_year = None
        if entry_year:
            entry_academic_year = get_or_create_academic_year(f"{entry_year}/{entry_year + 1}")

        try:
            with transaction.atomic():
                # Per policy: a student's username AND password are both their
                # registration number. safe_username() only sanitizes characters
                # that Django's username field can't store (e.g. stray slashes);
                # the password is set from the untouched reg_no so it matches
                # exactly what's printed on the student's documents.
                username = safe_username(reg_no)
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={'email': email or ''},
                )
                if email:
                    user.email = email
                user.surname = surname
                user.other_names = ' '.join(filter(None, [first_name, other_names])) or None
                user.phone_number = clean(ws.cell(row=row_idx, column=COL_PHONE).value)
                user.role = User.IS_STUDENT
                if user_created:
                    user.set_password(reg_no)
                user.save()

                profile, profile_created = StudentProfile.objects.get_or_create(
                    reg_number=reg_no,
                    defaults={'user': user, 'course': course},
                )
                profile.user = user
                profile.student_number = student_number
                profile.surname = surname
                profile.first_name = first_name
                profile.other_names = other_names
                profile.phone_number = clean(ws.cell(row=row_idx, column=COL_PHONE).value)
                profile.email = email
                profile.nationality = clean(ws.cell(row=row_idx, column=COL_NATIONALITY).value)

                profile.campus = get_or_create_campus(ws.cell(row=row_idx, column=COL_CAMPUS).value)
                profile.course = course
                profile.year_of_study = study_year
                profile.entry_academic_year = entry_academic_year
                profile.academic_year = academic_year
                profile.semester = semester
                profile.intake = intake

                profile.gender = normalize_gender(ws.cell(row=row_idx, column=COL_GENDER).value)

                sponsorship_type = clean(ws.cell(row=row_idx, column=COL_SPONSORSHIP_TYPE).value)
                profile.sponsorship_type = sponsorship_type.upper() if sponsorship_type else None
                profile.sponsorship_scheme = clean(ws.cell(row=row_idx, column=COL_SPONSORSHIP_SCHEME).value)

                programme_type = clean(ws.cell(row=row_idx, column=COL_PROGRAMME_TYPE).value)
                profile.programme_type = programme_type.upper() if programme_type else None

                profile.is_enrolled = to_bool(ws.cell(row=row_idx, column=COL_IS_ENROLLED).value)
                profile.enrollment_token = clean(ws.cell(row=row_idx, column=COL_ENROLLMENT_TOKEN).value)
                profile.enrollment_condition = clean(ws.cell(row=row_idx, column=COL_ENROLLMENT_CONDITION).value)

                profile.is_registered = to_bool(ws.cell(row=row_idx, column=COL_IS_REGISTERED).value)
                profile.registration_type = clean(ws.cell(row=row_idx, column=COL_REGISTRATION_TYPE).value)
                profile.registration_status = clean(ws.cell(row=row_idx, column=COL_REGISTRATION_STATUS).value)
                profile.provisional_registration_type = clean(
                    ws.cell(row=row_idx, column=COL_PROVISIONAL_REG_TYPE).value
                )
                profile.registration_condition = clean(ws.cell(row=row_idx, column=COL_REGISTRATION_CONDITION).value)
                profile.save()

                fee, _ = StudentTermFee.objects.get_or_create(student=profile, term=academic_term)
                fee.tuition_invoice_amount = to_decimal(ws.cell(row=row_idx, column=COL_TUITION_INVOICE).value)
                fee.tuition_amount_paid = to_decimal(ws.cell(row=row_idx, column=COL_TUITION_PAID).value)
                fee.tuition_amount_due = to_decimal(ws.cell(row=row_idx, column=COL_TUITION_DUE).value)
                fee.functional_fees_invoice_amount = to_decimal(ws.cell(row=row_idx, column=COL_FUNCTIONAL_INVOICE).value)
                fee.functional_fees_amount_paid = to_decimal(ws.cell(row=row_idx, column=COL_FUNCTIONAL_PAID).value)
                fee.functional_fees_amount_due = to_decimal(ws.cell(row=row_idx, column=COL_FUNCTIONAL_DUE).value)
                fee.other_fees_invoice_amount = to_decimal(ws.cell(row=row_idx, column=COL_OTHER_INVOICE).value)
                fee.other_fees_amount_paid = to_decimal(ws.cell(row=row_idx, column=COL_OTHER_PAID).value)
                fee.other_fees_amount_due = to_decimal(ws.cell(row=row_idx, column=COL_OTHER_DUE).value)
                fee.total_fees_due = to_decimal(ws.cell(row=row_idx, column=COL_TOTAL_INVOICED).value)
                fee.total_amount_paid = to_decimal(ws.cell(row=row_idx, column=COL_TOTAL_PAID).value)
                fee.save()

        except Exception as exc:
            print(f"  DATABASE ERROR on row {row_idx} ({name}, {reg_no}): {exc}")
            stats['students_failed'] += 1
            continue

        stats['students_created' if profile_created else 'students_updated'] += 1
        if user_created:
            stats['student_credentials'].append((name, reg_no))


def import_all_programmes(xlsx_path, dry_run, stats):
    """ALL_Programmes.xlsx -> Department, Course.

    Seeds the canonical Department and Course (= 'Programme') records with
    the full metadata this export carries (approval status, study level,
    award, duration measure, modular flag, source system ids). Run this
    before the student and course-unit imports so those resolve against
    these richer records by code rather than creating bare placeholders.
    """
    print(f"\n--- Processing Programmes: {os.path.basename(xlsx_path)} ---")
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    for row_idx in range(PROGRAMMES_DATA_START_ROW, ws.max_row + 1):
        programme_code = clean(ws.cell(row=row_idx, column=PROG_COL_PROGRAMME_CODE).value)
        if not programme_code:
            continue

        dept_code = clean(ws.cell(row=row_idx, column=PROG_COL_DEPARTMENT_CODE).value)
        dept_title = clean(ws.cell(row=row_idx, column=PROG_COL_DEPARTMENT_TITLE).value)
        dept_source_id = clean(ws.cell(row=row_idx, column=PROG_COL_DEPARTMENT_ID).value)
        programme_title = clean(ws.cell(row=row_idx, column=PROG_COL_PROGRAMME_TITLE).value)

        if dry_run:
            print(f"  [dry-run] Programme evaluated: {programme_code} - {programme_title} ({dept_code})")
            stats['programmes_seen'] += 1
            continue

        with transaction.atomic():
            department = None
            if dept_code:
                department, _ = Department.objects.get_or_create(
                    code=dept_code,
                    defaults={'name': dept_title or dept_code, 'source_department_id': dept_source_id},
                )
                changed = False
                if dept_title and department.name != dept_title:
                    department.name = dept_title
                    changed = True
                if dept_source_id and department.source_department_id != dept_source_id:
                    department.source_department_id = dept_source_id
                    changed = True
                if changed:
                    department.save()

            course, created = Course.objects.get_or_create(
                code=programme_code,
                defaults={'name': programme_title or programme_code, 'department': department},
            )
            course.name = programme_title or programme_code
            if department:
                course.department = department

            course.is_modular = to_bool(ws.cell(row=row_idx, column=PROG_COL_IS_MODULAR).value)

            approval_raw = clean(ws.cell(row=row_idx, column=PROG_COL_CREATE_APPROVAL_STATUS).value)
            course.create_approval_status = approval_raw.upper() if approval_raw else 'PENDING'

            duration_measure_raw = clean(ws.cell(row=row_idx, column=PROG_COL_DURATION_MEASURE).value)
            course.duration_measure = duration_measure_raw.upper() if duration_measure_raw else 'YEAR'
            course.duration_measure_source_id = clean(
                ws.cell(row=row_idx, column=PROG_COL_DURATION_MEASURE_ID).value
            )
            course.duration_measure_label = clean(
                ws.cell(row=row_idx, column=PROG_COL_DURATION_MEASURE_LABEL).value
            )

            study_level_raw = clean(ws.cell(row=row_idx, column=PROG_COL_STUDY_LEVEL).value)
            course.study_level = study_level_raw.upper() if study_level_raw else None
            course.study_level_source_id = clean(ws.cell(row=row_idx, column=PROG_COL_STUDY_LEVEL_ID).value)
            course.study_level_label = clean(ws.cell(row=row_idx, column=PROG_COL_STUDY_LEVEL_LABEL).value)

            course.award = clean(ws.cell(row=row_idx, column=PROG_COL_AWARD).value)
            course.award_label = clean(ws.cell(row=row_idx, column=PROG_COL_AWARD_LABEL).value)
            course.version_title = clean(ws.cell(row=row_idx, column=PROG_COL_VERSION_TITLE).value)

            course.save()

            stats['programmes_created' if created else 'programmes_updated'] += 1


def import_course_units(xlsx_path, dry_run, stats):
    print(f"\n--- Processing Course Units: {os.path.basename(xlsx_path)} ---")
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    unmatched_departments = set()
    faculty = Faculty.objects.first() if Faculty.objects.count() == 1 else None

    for row_idx in range(2, ws.max_row + 1):
        code = clean(ws.cell(row=row_idx, column=1).value)
        if not code:
            continue
        title = clean(ws.cell(row=row_idx, column=2).value)
        dept_code = clean(ws.cell(row=row_idx, column=3).value)
        parent_department = clean(ws.cell(row=row_idx, column=4).value)
        serviced_raw = clean(ws.cell(row=row_idx, column=5).value)
        credit_units = ws.cell(row=row_idx, column=6).value
        contact_hours = ws.cell(row=row_idx, column=7).value
        lecture_hours = ws.cell(row=row_idx, column=8).value
        practical_hours = ws.cell(row=row_idx, column=9).value
        field_work_hours = ws.cell(row=row_idx, column=10).value

        if dry_run:
            print(f"  [dry-run] Course unit evaluated: {code} - {title}")
            stats['units_seen'] += 1
            continue

        with transaction.atomic():
            department = None
            if dept_code:
                department, _ = Department.objects.get_or_create(
                    code=dept_code,
                    defaults={'name': parent_department or dept_code, 'faculty': faculty},
                )
                changed = False
                if parent_department and department.name != parent_department:
                    department.name = parent_department
                    changed = True
                # get_or_create()'s defaults are only applied at creation time, so if
                # ALL_Programmes already created this Department (the normal case, since
                # it runs first), a Faculty resolved here would otherwise never get
                # attached. Backfill it explicitly whenever it's still unset.
                if faculty and not department.faculty:
                    department.faculty = faculty
                    changed = True
                if changed:
                    department.save()

            # Match the department's existing Course via the Department FK rather than
            # guessing a code. The previous heuristic (code == 'N' + dept_code) only
            # worked when dept_code itself started with 'D' (DCE -> NDCE, DME -> NDME,
            # etc.); it silently failed for dept_code 'ICT' (real programme code is
            # 'NDICT', not 'NICT'), spawning a bogus placeholder Course('ICT') instead of
            # linking to the real programme. Prefer a National Diploma-level course when
            # a department has several, since that's the report's usual representative
            # programme for a department's units; fall back to any course in that
            # department, then to the guess (kept for departments not yet seeded by
            # ALL_Programmes), then to a bare placeholder as a last resort.
            course = None
            if department:
                dept_courses = Course.objects.filter(department=department).order_by('code')
                course = dept_courses.filter(code__startswith='N').first() or dept_courses.first()
            if not course and dept_code:
                course = Course.objects.filter(code='N' + dept_code).first()
            if course and department and not course.department:
                course.department = department
                course.save()
            if not course:
                course, _ = Course.objects.get_or_create(
                    code=dept_code or 'UNASSIGNED',
                    defaults={'name': parent_department or 'Unassigned', 'department': department},
                )
                unmatched_departments.add(dept_code)

            unit, created = CourseUnit.objects.get_or_create(
                code=code,
                defaults={'name': title or code, 'course': course},
            )
            unit.name = title or code
            unit.department = department
            unit.contact_hours = contact_hours or None
            unit.lecture_hours = lecture_hours or None
            unit.practical_hours = practical_hours or None
            unit.field_work_hours = field_work_hours or None
            if isinstance(credit_units, (int, float)) and credit_units:
                unit.credit_units = int(credit_units)
            unit.save()

            if serviced_raw:
                dept_codes = [c.strip() for c in re.split('[,/;]', serviced_raw) if c.strip()]
                serviced_depts = Department.objects.filter(code__in=dept_codes)
                unit.serviced_departments.set(serviced_depts)

            stats['units_created' if created else 'units_updated'] += 1

    if unmatched_departments:
        print(f"  WARNING: Could not match department codes to existing Courses: "
              f"{sorted(unmatched_departments)}. Units assigned to fallback placeholders.")


# ==================== DJANGO MANAGEMENT COMMAND ENTRY POINT ====================

class Command(BaseCommand):
    help = ("Import UTC Bushenyi's Group Users PDF, ALL_Programmes export, "
            "Students Data templates, and Course Unit report.")

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir', default=os.path.expanduser('~/Downloads'),
            help="Directory path holding import source files (defaults to ~/Downloads)",
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Executes parsing and validation without writing changes to the database.",
        )
        parser.add_argument(
            '--no-emails', action='store_true',
            help="Don't email staff their credentials - send every newly created staff "
                 "account straight to the fallback CSV file instead.",
        )
        parser.add_argument(
            '--no-staff-fallback-file', action='store_true',
            help="Suppresses the CSV written for staff whose credentials could not be "
                 "emailed (or all staff, if --no-emails was passed).",
        )
        parser.add_argument(
            '--no-student-csv', action='store_true',
            help="Suppresses output generation of the student name/password CSV file.",
        )
        parser.add_argument(
            '--test-email', default=TEST_EMAIL_OVERRIDE,
            help="Route ALL staff credential emails to this address instead of each "
                 "staff member's real .email (useful for testing the send path "
                 "without emailing real staff). Defaults to the TEST_EMAIL_OVERRIDE "
                 "constant at the top of this file; pass --no-test-email to force "
                 "real addresses for a single run regardless of that constant.",
        )
        parser.add_argument(
            '--no-test-email', action='store_true',
            help="Force sending to each staff member's real email for this run, "
                 "overriding TEST_EMAIL_OVERRIDE / --test-email.",
        )

    def handle(self, *args, **options):
        directory = options['dir']
        dry_run = options['dry_run']
        send_emails = not options['no_emails']
        test_email = None if options['no_test_email'] else options['test_email']

        if send_emails and test_email:
            print(f"TEST EMAIL MODE: all staff credential emails will be sent to "
                  f"{test_email} instead of each staff member's real address. "
                  f"Pass --no-test-email (or set TEST_EMAIL_OVERRIDE = None in the "
                  f"script) to resume sending to real addresses.\n")

        def find_files(pattern):
            return sorted(glob.glob(os.path.join(directory, pattern)))

        pdf_files = find_files('*roup*sers*.pdf') or find_files('*.pdf')
        programme_files = find_files('*Programmes*.xlsx') or find_files('*programmes*.xlsx')
        student_files = find_files('*STUDENTS-DATA-TEMPLATE*.xlsx')
        course_unit_files = find_files('*COURSE-UNIT-REPORT*.xlsx')

        if not (pdf_files or programme_files or student_files or course_unit_files):
            self.stderr.write(f"No valid import assets found in directory: {directory}")
            return

        stats = {
            'staff_seen': 0, 'staff_created': 0, 'staff_updated': 0, 'staff_skipped': 0,
            'staff_emails_sent': 0, 'staff_emails_failed': 0,
            'programmes_seen': 0, 'programmes_created': 0, 'programmes_updated': 0,
            'students_seen': 0, 'students_created': 0, 'students_updated': 0,
            'students_skipped': 0, 'students_failed': 0,
            'units_seen': 0, 'units_created': 0, 'units_updated': 0,
            'staff_credential_fallback': [],   # (username, email, role, password, email_status) - EVERY staff account created this run, regardless of email outcome
            'student_credentials': [],         # (student_name, password==reg_no) - every student created
        }

        for path in pdf_files:
            import_group_users(path, dry_run, stats, send_emails=send_emails, test_email=test_email)

        # Run ALL_Programmes first to seed canonical Department/Course records
        # before student files and course units try to resolve/create them.
        for path in programme_files:
            import_all_programmes(path, dry_run, stats)

        # Enforce student files execution before course units to establish base Course records
        for path in student_files:
            import_student_file(path, dry_run, stats)

        for path in course_unit_files:
            import_course_units(path, dry_run, stats)

        print("\n=== HEMIS INGESTION SUMMARY ===")
        skip_keys = ('staff_credential_fallback', 'student_credentials')
        for key, value in stats.items():
            if key not in skip_keys:
                print(f"  {key}: {value}")

        if not dry_run and stats['staff_credential_fallback'] and not options['no_staff_fallback_file']:
            out_path = os.path.join(
                directory, f"staff_credentials_fallback_{timezone.now():%Y%m%d_%H%M%S}.csv"
            )
            with open(out_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['username', 'email', 'role', 'temporary_password', 'email_status'])
                writer.writerows(stats['staff_credential_fallback'])
            print(f"\n{len(stats['staff_credential_fallback'])} staff account(s) written to fallback CSV "
                  f"(as a safety net, this includes accounts whose email sent successfully, not just "
                  f"failures/skips - see the email_status column; {stats['staff_emails_sent']} sent, "
                  f"{stats['staff_emails_failed']} failed): {out_path}")
            print("SECURITY WARNING: This file contains unhashed temporary passwords, "
                  "including for accounts already emailed successfully. Securely distribute/purge "
                  "credentials and delete this file immediately.")

        if not dry_run and stats['student_credentials'] and not options['no_student_csv']:
            out_path = os.path.join(
                directory, f"student_credentials_{timezone.now():%Y%m%d_%H%M%S}.csv"
            )
            with open(out_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['student_name', 'password'])
                writer.writerows(stats['student_credentials'])
            print(f"\nStudent credentials CSV ({len(stats['student_credentials'])} students) "
                  f"written to: {out_path}")
            print("SECURITY WARNING: This file contains unhashed passwords (registration "
                  "numbers). Securely distribute it to the registrar's office and purge "
                  "this file immediately afterward.")