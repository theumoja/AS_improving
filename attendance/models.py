from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal


class User(AbstractUser):
    IS_ADMIN = 'ADMIN'
    IS_TEACHER = 'TEACHER'
    IS_STUDENT = 'STUDENT'
    IS_WARDEN = 'WARDEN'
    IS_LIBRARIAN = 'LIBRARIAN'
    IS_ACCOUNTANT = 'ACCOUNTANT'
    IS_REGISTRAR = 'REGISTRAR'
    IS_PARENT = 'PARENT'

    ROLE_CHOICES = [
        (IS_ADMIN, 'Admin'),
        (IS_TEACHER, 'Teacher/Lecturer'),
        (IS_STUDENT, 'Student'),
        (IS_WARDEN, 'Warden'),
        (IS_LIBRARIAN, 'Librarian'),
        (IS_ACCOUNTANT, 'Accountant'),
        (IS_REGISTRAR, 'Academic Registrar'),
        (IS_PARENT, 'Parent'),
    ]
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default=IS_STUDENT)


# ==================== INSTITUTION & ACADEMIC STRUCTURE ====================

class Institution(models.Model):
    TYPE_CHOICES = [
        ('TECHNICAL_COLLEGE', 'Technical College'),
        ('UNIVERSITY', 'University'),
        ('INSTITUTE', 'Institute'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=255)
    institution_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='TECHNICAL_COLLEGE')
    slogan = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(help_text="Full location and P. O. Box address")
    telephone_1 = models.CharField(max_length=20)
    telephone_2 = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    email = models.EmailField()
    academic_units = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Comma-separated academic units e.g., COLLEGES, FACULTIES, DEPARTMENTS"
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Faculty(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='faculties', null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Faculties"

    def __str__(self):
        return self.name


class Department(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name='departments')
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


# ==================== ACADEMIC PERIOD TRACKING ====================

class AcademicTerm(models.Model):
    TERM_CHOICES = [
        ('TERM_1', 'Term 1'),
        ('TERM_2', 'Term 2'),
        ('TERM_3', 'Term 3'),
        ('RECESS', 'Recess Term'),
    ]
    academic_year = models.CharField(max_length=9, help_text="E.g., 2025/2026")
    term = models.CharField(max_length=10, choices=TERM_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = ('academic_year', 'term')
        verbose_name = "Academic Term"

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("Start date must be strictly before end date.")

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.is_current:
            AcademicTerm.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.academic_year} - {self.get_term_display()}"


# ===================================================================

class Course(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')

    def __str__(self):
        return f"{self.code} - {self.name}"


class Stream(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='streams')

    def __str__(self):
        return self.name


class CourseUnit(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='units')

    def __str__(self):
        return f"{self.code} - {self.name}"


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    name = models.CharField(max_length=255)
    courses = models.ManyToManyField('Course', blank=True, related_name='teachers')

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    reg_number = models.CharField(max_length=50, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students')
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='students')

    def __str__(self):
        return f"{self.reg_number} - {self.name}"


# ==================== PARENT PROFILE ====================

class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    students = models.ManyToManyField(StudentProfile, related_name='parents', blank=True)

    def __str__(self):
        return self.name


# ==================== LIBRARY MODELS ====================

class Book(models.Model):
    title = models.CharField(max_length=255, unique=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    isbn = models.CharField(max_length=50, blank=True, null=True, unique=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    is_reserve = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.available_copies}/{self.total_copies})"


class ReserveRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='reserve_requests')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='reserve_requests')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reserve_requests')
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    purpose_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Reserve: {self.book.title} ({self.status})"


class LibraryRecord(models.Model):
    STATUS_CHOICES = [('ISSUED', 'Issued'), ('RETURNED', 'Returned')]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='library_records')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='library_records')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='records')
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ISSUED')
    remarks = models.TextField(blank=True, null=True)

    def clean(self):
        if not self.student and not self.teacher:
            raise ValidationError("Must have a student or teacher borrower.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        borrower = self.student.name if self.student else (self.teacher.name if self.teacher else "Unknown")
        return f"{self.book.title} - {borrower} ({self.status})"


# ==================== FINANCE & FEES MANAGEMENT MODULE ====================

class FeeElement(models.Model):
    ELEMENT_TYPES = [
        ('TUITION', 'Tuition Fee'),
        ('FUNCTIONAL', 'Functional Fee'),
        ('OTHER', 'Other / Sundry Fee'),
        ('GRADUATION', 'Graduation Fee'),
    ]
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=255)
    fee_type = models.CharField(max_length=20, choices=ELEMENT_TYPES, default='FUNCTIONAL')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name} ({self.get_fee_type_display()})"


class TuitionAmount(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='tuition_amounts')
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='tuition_amounts')
    fee_element = models.ForeignKey(FeeElement, on_delete=models.CASCADE, related_name='tuition_amounts', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('course', 'term', 'fee_element')

    def __str__(self):
        return f"Tuition: {self.course.code} ({self.term}) - {self.amount}"


class FunctionalFee(models.Model):
    element = models.ForeignKey(FeeElement, on_delete=models.CASCADE, limit_choices_to={'fee_type': 'FUNCTIONAL'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, help_text="Leave blank if standard for all programs")
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='functional_fees')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_mandatory = models.BooleanField(default=True)

    def __str__(self):
        return f"Functional Fee: {self.element.name} ({self.term}) - {self.amount}"


class OtherFee(models.Model):
    element = models.ForeignKey(FeeElement, on_delete=models.CASCADE, limit_choices_to={'fee_type': 'OTHER'})
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Other Fee: {self.name} - {self.amount}"


class FeeWaiver(models.Model):
    WAIVER_TYPES = [
        ('PERCENTAGE', 'Percentage Discount (%)'),
        ('FIXED', 'Fixed Amount Discount'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='waivers')
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='waivers')
    waiver_type = models.CharField(max_length=20, choices=WAIVER_TYPES, default='PERCENTAGE')
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Discount percentage or exact amount")
    reason = models.TextField()
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role__in': ['ADMIN', 'ACCOUNTANT']})
    date_granted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Waiver: {self.student.name} ({self.term}) - {self.value}"


class FeeApproval(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    title = models.CharField(max_length=255)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE)
    details = models.TextField()
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fee_approval_requests')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='fee_approvals_given')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Approval Request: {self.title} [{self.status}]"


class Affiliate(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    revenue_share_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Affiliate: {self.name} ({self.code})"


class GraduationFee(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='graduation_fees')
    academic_year = models.CharField(max_length=9, help_text="E.g., 2025/2026")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_paid = models.BooleanField(default=False)
    clearance_status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('CLEARED', 'Cleared')], default='PENDING')

    def __str__(self):
        return f"Graduation Fee: {self.student.name} - {self.amount}"


class FeeStructureCopy(models.Model):
    source_term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='source_copies')
    target_term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='target_copies')
    copied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    copied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Copy from {self.source_term} to {self.target_term}"


class StudentTermFee(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='term_fees')
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='student_fees')
    total_fees_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('student', 'term')

    @property
    def remaining_balance(self):
        return self.total_fees_due - self.total_amount_paid

    def __str__(self):
        return f"{self.student.name} ({self.term}) - Balance: {self.remaining_balance}"


class FeePaymentTransaction(models.Model):
    PAYMENT_METHODS = [
        ('BANK_DEPOSIT', 'Bank Deposit'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('CASH', 'Cash'),
    ]
    term_fee_account = models.ForeignKey(StudentTermFee, on_delete=models.CASCADE, related_name='transactions', null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='BANK_DEPOSIT')
    reference_number = models.CharField(max_length=100, unique=True)
    is_confirmed = models.BooleanField(default=False)
    date_recorded = models.DateTimeField(auto_now_add=True)
    date_confirmed = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'ACCOUNTANT'})

    def __str__(self):
        return f"{self.reference_number} - {self.amount}"


class StaffPaymentRecord(models.Model):
    PAYMENT_METHODS = [
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('CASH', 'Cash'),
    ]
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='staff_payments', limit_choices_to={'role__in': ['ADMIN','TEACHER','WARDEN','LIBRARIAN','ACCOUNTANT']})
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='BANK_TRANSFER')
    reference_number = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    term = models.ForeignKey(AcademicTerm, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_payouts')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='processed_staff_salaries', limit_choices_to={'role': 'ACCOUNTANT'})

    def __str__(self):
        return f"{self.reference_number} - {self.staff.username} ({self.amount})"


# ==================== TIMETABLE & ATTENDANCE ====================

class TimetableBatch(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    week_start_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_revoked = models.BooleanField(default=False)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='timetable_batches', null=True)


class TimetableEntry(models.Model):
    DAYS_OF_WEEK = [
        ('MON','Monday'),('TUE','Tuesday'),('WED','Wednesday'),
        ('THU','Thursday'),('FRI','Friday'),('SAT','Saturday'),('SUN','Sunday')
    ]
    batch = models.ForeignKey(TimetableBatch, on_delete=models.CASCADE, related_name='entries')
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    course_unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='entries')


class AttendanceSession(models.Model):
    timetable_entry = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE)
    date_marked = models.DateField(auto_now_add=True)
    teacher_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    teacher_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [('PRESENT','Present'), ('ABSENT','Absent')]
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)


# ==================== HOSTEL ====================

class Hostel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    location = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class Room(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='rooms')
    name_or_number = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=4)

    def __str__(self):
        return f"{self.hostel.name} - Room {self.name_or_number}"


class RoomAllocation(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='room_allocations')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='allocations')
    allocated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'WARDEN'})
    allocated_at = models.DateTimeField(auto_now=True)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='room_allocations', null=True)

    class Meta:
        unique_together = ('student', 'term')

    def __str__(self):
        return f"{self.student.name} -> {self.room} ({self.term})"


# ==================== DISCIPLINARY ====================

class DisciplinaryRecord(models.Model):
    SEVERITY_LEVELS = [
        ('MILD', 'Mild'),
        ('SEVERE', 'Severe'),
        ('VERY_SEVERE', 'Very Severe'),
        ('SUSPENDED_2W', 'Suspended 2 weeks'),
        ('INDEF_SUSPENDED', 'Indefinitely Suspended'),
        ('EXPELLED', 'Expelled'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='disciplinary_logs')
    subject = models.CharField(max_length=255)
    details = models.TextField()
    severity = models.CharField(max_length=15, choices=SEVERITY_LEVELS, default='MILD')
    date_logged = models.DateTimeField(auto_now_add=True)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_incidents')
    term = models.ForeignKey(AcademicTerm, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.subject} - {self.student.name}"


# ==================== EXAMINATION MODULE ====================

class Exam(models.Model):
    name = models.CharField(max_length=255)
    course_unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='exams')
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='exams')
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    total_marks = models.PositiveIntegerField(default=100)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.course_unit.code}"


class GradeScale(models.Model):
    name = models.CharField(max_length=50)
    min_score = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField()
    grade_point = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    remark = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-min_score']

    def __str__(self):
        return f"{self.name} ({self.min_score}-{self.max_score})"


class MarksEntry(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='marks')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='marks')
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade = models.ForeignKey(GradeScale, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='entered_marks')
    date_entered = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'exam')

    def __str__(self):
        return f"{self.student.name} - {self.exam.name}: {self.marks_obtained}"


class Transcript(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='transcripts')
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='transcripts')
    generated_date = models.DateField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='transcripts/', blank=True, null=True)

    def __str__(self):
        return f"Transcript - {self.student.name} ({self.term})"


# ==================== INVENTORY MODULE ====================

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    CATEGORY_CHOICES = [
        ('FURNITURE', 'Furniture'),
        ('ELECTRONICS', 'Electronics'),
        ('STATIONERY', 'Stationery'),
        ('SPORTS', 'Sports Equipment'),
        ('LAB', 'Lab Equipment'),
        ('OTHER', 'Other'),
    ]
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    location = models.CharField(max_length=255, blank=True)
    reorder_level = models.PositiveIntegerField(default=10)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.quantity})"


class Asset(models.Model):
    asset_tag = models.CharField(max_length=50, unique=True)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='assets')
    serial_number = models.CharField(max_length=100, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets')
    status = models.CharField(max_length=20, choices=[('IN_USE','In Use'),('AVAILABLE','Available'),('MAINTENANCE','Maintenance'),('DISPOSED','Disposed')], default='AVAILABLE')

    def __str__(self):
        return f"{self.asset_tag} - {self.item.name}"


class Procurement(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED','Requested'),
        ('APPROVED','Approved'),
        ('ORDERED','Ordered'),
        ('RECEIVED','Received'),
        ('CANCELLED','Cancelled'),
    ]
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='procurements')
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='procurements')
    request_date = models.DateField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_procurements')

    def __str__(self):
        return f"{self.item.name} x{self.quantity} - {self.status}"


class StockMovement(models.Model):
    MOVEMENT_TYPES = [('IN','Stock In'), ('OUT','Stock Out')]
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='movements')
    quantity = models.IntegerField()
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES)
    date = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.item.name} {self.movement_type} {self.quantity}"


# ==================== TRANSPORT MODULE ====================

class Vehicle(models.Model):
    registration_number = models.CharField(max_length=20, unique=True)
    model = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    driver_name = models.CharField(max_length=255)
    driver_contact = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=[('ACTIVE','Active'),('MAINTENANCE','Maintenance'),('INACTIVE','Inactive')], default='ACTIVE')

    def __str__(self):
        return f"{self.registration_number} - {self.model}"


class Route(models.Model):
    name = models.CharField(max_length=255)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, related_name='routes')
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    days_of_week = models.CharField(max_length=50, help_text="Comma-separated e.g., MON,WED,FRI")

    def __str__(self):
        return self.name


class TransportAllocation(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='transport_allocations')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='allocations')
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='transport_allocations')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'term')

    def __str__(self):
        return f"{self.student.name} - {self.route.name}"


class TripLog(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='trips')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='trips')
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField(null=True, blank=True)
    driver_name = models.CharField(max_length=255, blank=True)
    mileage_start = models.PositiveIntegerField(default=0)
    mileage_end = models.PositiveIntegerField(default=0)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.vehicle.registration_number} - {self.route.name} ({self.departure_time})"


# ==================== HUMAN RESOURCE ====================

class Qualification(models.Model):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qualifications', limit_choices_to={'role__in': ['ADMIN','TEACHER','WARDEN','LIBRARIAN','ACCOUNTANT']})
    qualification_name = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    year_awarded = models.IntegerField()
    certificate_file = models.FileField(upload_to='qualifications/', blank=True, null=True)

    def __str__(self):
        return f"{self.staff.username} - {self.qualification_name}"


class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('ANNUAL','Annual'),
        ('SICK','Sick'),
        ('MATERNITY','Maternity'),
        ('PATERNITY','Paternity'),
        ('OTHER','Other'),
    ]
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[('PENDING','Pending'),('APPROVED','Approved'),('REJECTED','Rejected')], default='PENDING')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_leaves')
    date_applied = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.username} - {self.leave_type} ({self.start_date} to {self.end_date})"


class PerformanceEvaluation(models.Model):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluations')
    evaluator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='given_evaluations')
    evaluation_date = models.DateField(auto_now_add=True)
    score = models.PositiveIntegerField(help_text="Score out of 100")
    comments = models.TextField(blank=True)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='evaluations', null=True)

    def __str__(self):
        return f"{self.staff.username} - {self.score}%"


# ==================== ONLINE LEARNING MODULE ====================

class OnlineCourse(models.Model):
    name = models.CharField(max_length=255)
    course_unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='online_courses')
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='online_courses')
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    online_course = models.ForeignKey(OnlineCourse, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    attachment = models.FileField(upload_to='lessons/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.online_course.name} - {self.title}"


class Assignment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateTimeField()
    max_score = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='submissions/')
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='graded_submissions')

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"{self.student.name} - {self.assignment.title}"


class OnlineExam(models.Model):
    online_course = models.ForeignKey(OnlineCourse, on_delete=models.CASCADE, related_name='online_exams')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    total_marks = models.PositiveIntegerField(default=100)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class OnlineExamQuestion(models.Model):
    online_exam = models.ForeignKey(OnlineExam, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    marks = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.online_exam.title} - Q{self.id}"


class OnlineExamAnswer(models.Model):
    question = models.ForeignKey(OnlineExamQuestion, on_delete=models.CASCADE, related_name='answers')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='online_exam_answers')
    answer_text = models.TextField()
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='graded_answers')

    class Meta:
        unique_together = ('question', 'student')

    def __str__(self):
        return f"{self.student.name} - {self.question.online_exam.title}"


class Note(models.Model):
    online_course = models.ForeignKey(OnlineCourse, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=255)
    content = models.TextField()
    file = models.FileField(upload_to='notes/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.online_course.name} - {self.title}"


class CourseUnitDocument(models.Model):
    course_unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='course_unit_documents/')
    uploaded_by = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='uploaded_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.course_unit.code} - {self.title}"