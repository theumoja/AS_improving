import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model

from attendance.models import (
    Institution,
    Faculty,
    Department,
    Course,
    Stream,
    AcademicTerm,
    StudentProfile,
    StudentTermFee,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Imports student enrollment and registration data from CSV files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to the CSV file to import",
        )
        parser.add_argument(
            "--term",
            type=str,
            default="2025/2026",
            help="Academic Year (e.g. 2025/2026)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options["file"]
        academic_year = options["term"]

        # 1. Setup default reference objects
        institution, _ = Institution.objects.get_or_create(
            name="Default Institution",
            defaults={"email": "info@institution.ac.ug", "address": "Main Campus"},
        )
        faculty, _ = Faculty.objects.get_or_create(
            name="General Faculty", defaults={"institution": institution}
        )
        department, _ = Department.objects.get_or_create(
            name="General Department", defaults={"faculty": faculty}
        )
        default_course, _ = Course.objects.get_or_create(
            code="GEN101",
            defaults={"name": "General Studies", "department": department},
        )
        default_stream, _ = Stream.objects.get_or_create(
            name="Stream A", course=default_course
        )

        term, _ = AcademicTerm.objects.get_or_create(
            academic_year=academic_year,
            term="TERM_1",
            defaults={
                "start_date": "2026-01-01",
                "end_date": "2026-05-30",
                "is_current": True,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(f"Processing data from: {file_path}")
        )

        created_count = 0
        updated_count = 0

        with open(file_path, mode="r", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                # Extract and clean row values
                full_name = (
                    row.get("Full Name")
                    or row.get("Name")
                    or row.get("student_name")
                    or "Unknown Student"
                ).strip()

                email = (
                    row.get("Email")
                    or row.get("Email Address")
                    or row.get("email")
                    or f"student_{get_random_string(6).lower()}@institution.ac.ug"
                ).strip()

                reg_no = (
                    row.get("Registration Number")
                    or row.get("Reg No")
                    or row.get("reg_number")
                    or f"REG/{get_random_string(6).upper()}"
                ).strip()

                # Correct gender parsing
                gender_raw = (
                    row.get("Gender") or row.get("gender") or ""
                ).strip().upper()

                if gender_raw.startswith("F") or "FEMALE" in gender_raw:
                    gender = "FEMALE"
                elif gender_raw.startswith("M") or "MALE" in gender_raw:
                    gender = "MALE"
                else:
                    gender = None

                course_code = row.get("Course Code") or row.get("course")
                course_obj = default_course
                if course_code and course_code.strip():
                    course_obj, _ = Course.objects.get_or_create(
                        code=course_code.strip(),
                        defaults={"name": course_code.strip(), "department": department},
                    )

                stream_name = row.get("Stream") or "Stream A"
                stream_obj, _ = Stream.objects.get_or_create(
                    name=stream_name.strip(), course=course_obj
                )

                # 2. Get or Create User Account
                username = email if email else reg_no.replace("/", "_")
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": full_name.split()[0] if full_name else "",
                        "last_name": " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else "",
                        "role": User.IS_STUDENT,
                    },
                )

                if user_created:
                    user.set_password("Student@123")
                    user.save()

                # 3. Safely update or create StudentProfile to prevent UNIQUE constraint collisions
                profile_by_reg = StudentProfile.objects.filter(reg_number=reg_no).first()
                profile_by_user = StudentProfile.objects.filter(user=user).first()

                if profile_by_reg:
                    student_profile = profile_by_reg
                    # Remove conflicting user profile if linked elsewhere
                    if profile_by_user and profile_by_user != student_profile:
                        profile_by_user.delete()

                    student_profile.user = user
                    student_profile.name = full_name
                    student_profile.course = course_obj
                    student_profile.stream = stream_obj
                    student_profile.gender = gender
                    student_profile.academic_status = row.get("Status") or "ACTIVE"
                    student_profile.sponsorship = row.get("Sponsorship") or "PRIVATE"
                    student_profile.save()
                    profile_created = False

                elif profile_by_user:
                    # If reg_number changed, remove old primary key record to free user_id
                    profile_by_user.delete()
                    student_profile = StudentProfile.objects.create(
                        user=user,
                        reg_number=reg_no,
                        name=full_name,
                        course=course_obj,
                        stream=stream_obj,
                        gender=gender,
                        academic_status=row.get("Status") or "ACTIVE",
                        sponsorship=row.get("Sponsorship") or "PRIVATE",
                    )
                    profile_created = True

                else:
                    student_profile = StudentProfile.objects.create(
                        user=user,
                        reg_number=reg_no,
                        name=full_name,
                        course=course_obj,
                        stream=stream_obj,
                        gender=gender,
                        academic_status=row.get("Status") or "ACTIVE",
                        sponsorship=row.get("Sponsorship") or "PRIVATE",
                    )
                    profile_created = True

                # 4. Safe Fee Calculation
                fees_due_raw = row.get("Fees Due") or "0.00"
                fees_paid_raw = row.get("Fees Paid") or "0.00"

                try:
                    fees_due = Decimal(str(fees_due_raw).replace(",", "").strip())
                except Exception:
                    fees_due = Decimal("0.00")

                try:
                    fees_paid = Decimal(str(fees_paid_raw).replace(",", "").strip())
                except Exception:
                    fees_paid = Decimal("0.00")

                StudentTermFee.objects.get_or_create(
                    student=student_profile,
                    term=term,
                    defaults={
                        "total_fees_due": fees_due,
                        "total_amount_paid": fees_paid,
                    },
                )

                if profile_created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully imported! Created: {created_count}, Updated: {updated_count}"
            )
        )