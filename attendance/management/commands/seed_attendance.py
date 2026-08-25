import random
from datetime import datetime, timedelta, time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from attendance.models import (
    User, AcademicTerm, Department, Course, Stream, CourseUnit,
    TeacherProfile, StudentProfile, ParentProfile, Book, ReserveRequest,
    LibraryRecord, StudentTermFee, FeePaymentTransaction, StaffPaymentRecord,
    TimetableBatch, TimetableEntry, AttendanceSession, AttendanceRecord,
    Hostel, Room, RoomAllocation, DisciplinaryRecord, Exam, GradeScale,
    MarksEntry, Transcript, Supplier, InventoryItem, Asset, Procurement,
    StockMovement, Vehicle, Route, TransportAllocation, TripLog, Qualification,
    LeaveRequest, PerformanceEvaluation, OnlineCourse, Lesson, Assignment,
    Submission, OnlineExam, OnlineExamQuestion, OnlineExamAnswer, Note
)

User = get_user_model()

# Exact Roster provided in your query
STUDENT_ROSTER = [
    ("2024/116", "Sarah Wasswa"),
    ("2024/117", "Sarah Okello"),
    ("2024/118", "Harriet Otim"),
    ("2024/119", "Musa Otim"),
    ("2024/120", "Ivan Kato"),
    ("2024/121", "Joy Mugisha"),
    ("2024/122", "Brenda Mwenge"),
    ("2024/123", "Derrick Wasswa"),
    ("2024/124", "Musa Kato"),
    ("2024/125", "Joy Mukasa"),
    ("2024/126", "Sarah Mukasa"),
    ("2024/127", "Abel Okello"),
    ("2024/128", "Brenda Kato"),
]


class Command(BaseCommand):
    help = 'Seeds targeted roster students with 60+ days of dense attendance session records.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚀 Seeding core structure and custom student attendance dataset...'))

        # ------------------------------------------------------------------
        # 1. ADMIN & ACADEMIC BASICS
        # ------------------------------------------------------------------
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@utc.ac.ug',
                'role': User.IS_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()

        today_date = timezone.localdate()
        current_term, _ = AcademicTerm.objects.get_or_create(
            academic_year='2025/2026',
            term='TERM_3',
            defaults={
                'start_date': today_date - timedelta(days=90),
                'end_date': today_date + timedelta(days=30),
                'is_current': True
            }
        )

        dept, _ = Department.objects.get_or_create(name='Computing & Information Technology')
        course, _ = Course.objects.get_or_create(code='BIT2025', defaults={'name': 'Bachelor of IT', 'department': dept})
        stream, _ = Stream.objects.get_or_create(name='Stream A', course=course)

        course_units = []
        unit_names = ['Database Systems', 'Software Engineering', 'Computer Networks', 'Web Development', 'Cyber Security']
        for idx, u_name in enumerate(unit_names, start=1):
            cu, _ = CourseUnit.objects.get_or_create(code=f"BIT{100+idx}", defaults={'name': u_name, 'course': course})
            course_units.append(cu)

        # Teachers
        teachers = []
        for i in range(1, 4):
            u, _ = User.objects.get_or_create(username=f"lecturer_{i}", defaults={'email': f"lecturer{i}@utc.ac.ug", 'role': User.IS_TEACHER})
            u.set_password('teacher123')
            u.save()
            tp, _ = TeacherProfile.objects.get_or_create(user=u, defaults={'name': f"Lecturer {i}"})
            teachers.append(tp)

        # ------------------------------------------------------------------
        # 2. CREATE TARGETED STUDENT ROSTER
        # ------------------------------------------------------------------
        students = []
        for reg_num, full_name in STUDENT_ROSTER:
            clean_username = f"std_{reg_num.replace('/', '_')}"
            u, created = User.objects.get_or_create(
                username=clean_username,
                defaults={'email': f"{clean_username}@utc.ac.ug", 'role': User.IS_STUDENT}
            )
            if created:
                u.set_password('student123')
                u.save()

            sp, _ = StudentProfile.objects.get_or_create(
                reg_number=reg_num,
                defaults={
                    'user': u,
                    'name': full_name,
                    'course': course,
                    'stream': stream
                }
            )
            students.append(sp)

        self.stdout.write(self.style.SUCCESS(f'✅ Seeded {len(students)} target roster students.'))

        # ------------------------------------------------------------------
        # 3. GENERATE DENSE ATTENDANCE HISTORY (PAST 60 DAYS)
        # ------------------------------------------------------------------
        tb, _ = TimetableBatch.objects.get_or_create(
            week_start_date=today_date - timedelta(days=60),
            defaults={'is_active': True, 'term': current_term}
        )

        statuses = ['PRESENT', 'PRESENT', 'PRESENT', 'PRESENT', 'LATE', 'ABSENT']
        session_count = 0
        record_count = 0

        # Generate sessions covering weekdays for the last 60 days
        for day_offset in range(60, 0, -1):
            past_date = today_date - timedelta(days=day_offset)
            
            # Skip weekends (Saturday=5, Sunday=6)
            if past_date.weekday() in (5, 6):
                continue

            day_code_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI'}
            day_str = day_code_map[past_date.weekday()]

            # Generate 2 sessions per weekday
            for s_idx in range(2):
                c_unit = course_units[(day_offset + s_idx) % len(course_units)]
                t_prof = teachers[s_idx % len(teachers)]
                
                start_h = 8 if s_idx == 0 else 14
                
                te, _ = TimetableEntry.objects.get_or_create(
                    batch=tb,
                    day=day_str,
                    start_time=time(start_h, 0),
                    end_time=time(start_h + 2, 0),
                    course_unit=c_unit,
                    defaults={'teacher': t_prof, 'stream': stream}
                )

                # Create Session with past timestamp
                atts = AttendanceSession.objects.create(
                    timetable_entry=te,
                    teacher_latitude=Decimal('0.347596'),
                    teacher_longitude=Decimal('32.582520')
                )
                session_count += 1

                # Seed attendance record for every target student
                for std in students:
                    # Give Abel Okello & Brenda Kato higher attendance consistency (~95%)
                    if std.reg_number in ["2024/127", "2024/128"]:
                        status = 'PRESENT' if random.random() < 0.92 else 'LATE'
                    else:
                        status = random.choice(statuses)

                    AttendanceRecord.objects.create(
                        session=atts,
                        student=std,
                        status=status
                    )
                    record_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'🎉 SUCCESS: Generated {session_count} attendance sessions and {record_count} student attendance logs across 60 days!'
        ))