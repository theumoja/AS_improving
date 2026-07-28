from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import (
    User, AcademicTerm, Department, Course, Stream, CourseUnit,
    TeacherProfile, StudentProfile, ParentProfile,
    Book, ReserveRequest, LibraryRecord,
    StudentTermFee, FeePaymentTransaction, StaffPaymentRecord,
    TimetableBatch, TimetableEntry, AttendanceSession, AttendanceRecord,
    Hostel, Room, RoomAllocation,
    DisciplinaryRecord,
    Exam, GradeScale, MarksEntry, Transcript,
    Supplier, InventoryItem, Asset, Procurement, StockMovement,
    Vehicle, Route, TransportAllocation, TripLog,
    Qualification, LeaveRequest, PerformanceEvaluation,
    OnlineCourse, Lesson, Assignment, Submission,
    OnlineExam, OnlineExamQuestion, OnlineExamAnswer, Note
)


# ---------- Custom User Admin ----------
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Permissions', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


# ---------- Academic Term ----------
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ('academic_year', 'term', 'start_date', 'end_date', 'is_current', 'days_count')
    list_filter = ('academic_year', 'is_current')
    search_fields = ('academic_year', 'term')

    def days_count(self, obj):
        if obj.start_date and obj.end_date:
            return (obj.end_date - obj.start_date).days
        return 0
    days_count.short_description = "Total Days"


# ---------- Department ----------
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


# ---------- Course ----------
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department')
    list_filter = ('department',)
    search_fields = ('code', 'name')


# ---------- Stream ----------
class StreamAdmin(admin.ModelAdmin):
    list_display = ('name', 'course')
    list_filter = ('course',)
    search_fields = ('name',)


# ---------- CourseUnit ----------
class CourseUnitAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'course')
    list_filter = ('course',)
    search_fields = ('code', 'name')


# ---------- Teacher Profile ----------
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'course_list')
    search_fields = ('name', 'user__username')
    filter_horizontal = ('courses',)

    def course_list(self, obj):
        return ", ".join([c.code for c in obj.courses.all()])
    course_list.short_description = "Courses"


# ---------- Student Profile ----------
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('reg_number', 'name', 'course', 'stream', 'user')
    list_filter = ('course', 'stream')
    search_fields = ('reg_number', 'name', 'user__username')


# ---------- Parent Profile ----------
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'phone', 'student_list')
    search_fields = ('name', 'user__username')
    filter_horizontal = ('students',)

    def student_list(self, obj):
        return ", ".join([s.reg_number for s in obj.students.all()])
    student_list.short_description = "Students"


# ---------- Library ----------
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'total_copies', 'available_copies', 'is_reserve')
    list_filter = ('is_reserve', 'department')
    search_fields = ('title', 'author', 'isbn')


class ReserveRequestAdmin(admin.ModelAdmin):
    list_display = ('book', 'applicant', 'request_date', 'status')
    list_filter = ('status',)
    search_fields = ('book__title', 'student__name', 'teacher__name')

    def applicant(self, obj):
        return obj.student.name if obj.student else (obj.teacher.name if obj.teacher else "Unknown")
    applicant.short_description = "Applicant"


class LibraryRecordAdmin(admin.ModelAdmin):
    list_display = ('book', 'borrower', 'issue_date', 'due_date', 'return_date', 'status')
    list_filter = ('status',)
    search_fields = ('book__title', 'student__name', 'teacher__name')

    def borrower(self, obj):
        return obj.student.name if obj.student else (obj.teacher.name if obj.teacher else "Unknown")
    borrower.short_description = "Borrower"


# ---------- Finance ----------
class StudentTermFeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'total_fees_due', 'total_amount_paid', 'fee_status')
    list_filter = ('term',)
    search_fields = ('student__name', 'student__reg_number')

    def fee_status(self, obj):
        if obj.remaining_balance <= 0:
            return "Cleared"
        elif obj.total_amount_paid > 0:
            return "Partially Paid"
        return "Unpaid"
    fee_status.short_description = "Status"


class FeePaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'term_fee_account', 'amount', 'payment_method', 'is_confirmed', 'date_recorded')
    list_filter = ('is_confirmed', 'payment_method')
    search_fields = ('reference_number',)


class StaffPaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'staff', 'amount', 'payment_date', 'payment_method', 'term')
    list_filter = ('payment_method', 'term')
    search_fields = ('reference_number', 'staff__username')


# ---------- Timetable & Attendance ----------
class TimetableBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'week_start_date', 'is_active', 'is_revoked', 'term')
    list_filter = ('is_active', 'is_revoked', 'term')


class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ('day', 'start_time', 'end_time', 'course_unit', 'teacher', 'stream', 'batch')
    list_filter = ('day', 'teacher', 'stream')
    search_fields = ('course_unit__name', 'teacher__name')


class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('timetable_entry', 'date_marked', 'teacher_latitude', 'teacher_longitude')
    list_filter = ('date_marked',)


class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'status')
    list_filter = ('status', 'session__date_marked')
    search_fields = ('student__name',)


# ---------- Hostel ----------
class HostelAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    search_fields = ('name',)


class RoomAdmin(admin.ModelAdmin):
    list_display = ('name_or_number', 'hostel', 'capacity')
    list_filter = ('hostel',)


class RoomAllocationAdmin(admin.ModelAdmin):
    list_display = ('student', 'room', 'term', 'allocated_by', 'allocated_at')
    list_filter = ('term', 'room__hostel')
    search_fields = ('student__name', 'room__name_or_number')


# ---------- Disciplinary ----------
class DisciplinaryRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'severity', 'date_logged', 'reported_by')
    list_filter = ('severity', 'term')
    search_fields = ('student__name', 'subject')


# ---------- Examination ----------
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'course_unit', 'term', 'exam_date', 'total_marks', 'is_published')
    list_filter = ('term', 'is_published')
    search_fields = ('name', 'course_unit__name')


class GradeScaleAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_score', 'max_score', 'grade_point', 'remark')


class MarksEntryAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'marks_obtained', 'grade', 'entered_by')
    list_filter = ('exam', 'grade')
    search_fields = ('student__name', 'exam__name')


class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'generated_date')
    list_filter = ('term',)
    search_fields = ('student__name',)


# ---------- Inventory ----------
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email')
    search_fields = ('name', 'contact_person')


class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'unit_price', 'supplier', 'reorder_level')
    list_filter = ('category', 'supplier')
    search_fields = ('name',)


class AssetAdmin(admin.ModelAdmin):
    list_display = ('asset_tag', 'item', 'serial_number', 'assigned_to', 'status')
    list_filter = ('status',)
    search_fields = ('asset_tag', 'serial_number')


class ProcurementAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity', 'unit_cost', 'supplier', 'status', 'expected_delivery')
    list_filter = ('status', 'supplier')
    search_fields = ('item__name',)


class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('item', 'movement_type', 'quantity', 'date', 'reference')
    list_filter = ('movement_type',)
    search_fields = ('item__name', 'reference')


# ---------- Transport ----------
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'model', 'capacity', 'driver_name', 'status')
    list_filter = ('status',)
    search_fields = ('registration_number', 'driver_name')


class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'vehicle', 'start_location', 'end_location', 'departure_time', 'arrival_time')
    list_filter = ('vehicle',)
    search_fields = ('name',)


class TransportAllocationAdmin(admin.ModelAdmin):
    list_display = ('student', 'route', 'term', 'is_active')
    list_filter = ('term', 'is_active')
    search_fields = ('student__name', 'route__name')


class TripLogAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'route', 'departure_time', 'arrival_time', 'driver_name')
    list_filter = ('vehicle', 'route')
    search_fields = ('driver_name',)


# ---------- HR ----------
class QualificationAdmin(admin.ModelAdmin):
    list_display = ('staff', 'qualification_name', 'institution', 'year_awarded')
    search_fields = ('staff__username', 'qualification_name')


class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('staff', 'leave_type', 'start_date', 'end_date', 'status', 'date_applied')
    list_filter = ('status', 'leave_type')
    search_fields = ('staff__username',)


class PerformanceEvaluationAdmin(admin.ModelAdmin):
    list_display = ('staff', 'score', 'evaluator', 'evaluation_date', 'term')
    list_filter = ('term',)
    search_fields = ('staff__username',)


# ---------- Online Learning ----------
class OnlineCourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'course_unit', 'instructor', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'instructor')
    search_fields = ('name',)


class LessonAdmin(admin.ModelAdmin):
    list_display = ('online_course', 'title', 'order', 'video_url')
    list_filter = ('online_course',)
    search_fields = ('title',)


class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'title', 'due_date', 'max_score')
    search_fields = ('title',)


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'submitted_at', 'score', 'graded_by')
    list_filter = ('assignment',)
    search_fields = ('student__name',)


class OnlineExamAdmin(admin.ModelAdmin):
    list_display = ('online_course', 'title', 'start_time', 'end_time', 'total_marks', 'is_published')
    list_filter = ('is_published',)
    search_fields = ('title',)


class OnlineExamQuestionAdmin(admin.ModelAdmin):
    list_display = ('online_exam', 'question_text', 'marks')
    list_filter = ('online_exam',)


class OnlineExamAnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'student', 'answer_text', 'score', 'graded_by')
    list_filter = ('question__online_exam',)
    search_fields = ('student__name',)


class NoteAdmin(admin.ModelAdmin):
    list_display = ('online_course', 'title', 'uploaded_at')
    list_filter = ('online_course',)
    search_fields = ('title',)


# ---------- Register all models ----------
admin.site.register(User, CustomUserAdmin)
admin.site.register(AcademicTerm, AcademicTermAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Stream, StreamAdmin)
admin.site.register(CourseUnit, CourseUnitAdmin)
admin.site.register(TeacherProfile, TeacherProfileAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(ParentProfile, ParentProfileAdmin)

admin.site.register(Book, BookAdmin)
admin.site.register(ReserveRequest, ReserveRequestAdmin)
admin.site.register(LibraryRecord, LibraryRecordAdmin)

admin.site.register(StudentTermFee, StudentTermFeeAdmin)
admin.site.register(FeePaymentTransaction, FeePaymentTransactionAdmin)
admin.site.register(StaffPaymentRecord, StaffPaymentRecordAdmin)

admin.site.register(TimetableBatch, TimetableBatchAdmin)
admin.site.register(TimetableEntry, TimetableEntryAdmin)
admin.site.register(AttendanceSession, AttendanceSessionAdmin)
admin.site.register(AttendanceRecord, AttendanceRecordAdmin)

admin.site.register(Hostel, HostelAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(RoomAllocation, RoomAllocationAdmin)

admin.site.register(DisciplinaryRecord, DisciplinaryRecordAdmin)

admin.site.register(Exam, ExamAdmin)
admin.site.register(GradeScale, GradeScaleAdmin)
admin.site.register(MarksEntry, MarksEntryAdmin)
admin.site.register(Transcript, TranscriptAdmin)

admin.site.register(Supplier, SupplierAdmin)
admin.site.register(InventoryItem, InventoryItemAdmin)
admin.site.register(Asset, AssetAdmin)
admin.site.register(Procurement, ProcurementAdmin)
admin.site.register(StockMovement, StockMovementAdmin)

admin.site.register(Vehicle, VehicleAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(TransportAllocation, TransportAllocationAdmin)
admin.site.register(TripLog, TripLogAdmin)

admin.site.register(Qualification, QualificationAdmin)
admin.site.register(LeaveRequest, LeaveRequestAdmin)
admin.site.register(PerformanceEvaluation, PerformanceEvaluationAdmin)

admin.site.register(OnlineCourse, OnlineCourseAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(OnlineExam, OnlineExamAdmin)
admin.site.register(OnlineExamQuestion, OnlineExamQuestionAdmin)
admin.site.register(OnlineExamAnswer, OnlineExamAnswerAdmin)
admin.site.register(Note, NoteAdmin)