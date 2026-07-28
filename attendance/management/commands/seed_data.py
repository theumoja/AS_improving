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


class Command(BaseCommand):
    help = 'Comprehensive database seeder filling all 47 models with 20+ entries each.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚀 Starting enterprise database seed (20+ entries per table)...'))

        # ==========================================
        # 1. CORE INSTITUTIONAL USERS & STAFF ROLES
        # ==========================================
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

        accountant_user, _ = User.objects.get_or_create(
            username='sam_accountant',
            defaults={'email': 'sam.accountant@utc.ac.ug', 'role': User.IS_ACCOUNTANT}
        )
        accountant_user.set_password('accountant123')
        accountant_user.save()

        librarian_user, _ = User.objects.get_or_create(
            username='jane_librarian',
            defaults={'email': 'jane.librarian@utc.ac.ug', 'role': User.IS_LIBRARIAN}
        )
        librarian_user.set_password('librarian123')
        librarian_user.save()

        warden_user, _ = User.objects.get_or_create(
            username='mary_warden',
            defaults={'email': 'mary.warden@utc.ac.ug', 'role': User.IS_WARDEN}
        )
        warden_user.set_password('warden123')
        warden_user.save()

        registrar_user, _ = User.objects.get_or_create(
            username='reg_okello',
            defaults={'email': 'reg.okello@utc.ac.ug', 'role': User.IS_REGISTRAR}
        )
        registrar_user.set_password('registrar123')
        registrar_user.save()

        self.stdout.write('✅ Institutional administrative staff users created.')

        # ==========================================
        # 2. ACADEMIC TERMS (20 TERMS)
        # ==========================================
        AcademicTerm.objects.all().delete()
        today_date = timezone.localdate()
        
        years = ['2022/2023', '2023/2024', '2024/2025', '2025/2026', '2026/2027']
        terms = ['TERM_1', 'TERM_2', 'TERM_3', 'RECESS']
        term_objects = []

        day_offset = -1000
        for yr in years:
            for t in terms:
                is_curr = (yr == '2025/2026' and t == 'TERM_3')
                s_date = today_date + timedelta(days=day_offset)
                e_date = s_date + timedelta(days=80)
                term_objects.append(
                    AcademicTerm(
                        academic_year=yr,
                        term=t,
                        start_date=s_date,
                        end_date=e_date,
                        is_current=is_curr
                    )
                )
                day_offset += 90

        AcademicTerm.objects.bulk_create(term_objects)
        all_terms = list(AcademicTerm.objects.all())
        current_term = AcademicTerm.objects.get(academic_year='2025/2026', term='TERM_3')
        self.stdout.write(f'✅ Seeded {len(all_terms)} Academic Terms.')

        # ==========================================
        # 3. DEPARTMENTS, COURSES, UNITS & STREAMS (20 EACH)
        # ==========================================
        dept_names = [
            'Computing & Information Technology', 'Business Administration', 'School of Education',
            'Civil Engineering', 'Electrical Engineering', 'Mechanical Engineering',
            'Health Sciences', 'Agriculture & Environmental', 'School of Law', 'Architecture & Design',
            'Mass Communication & Journalism', 'Hospitality & Tourism', 'Procurement & Logistics',
            'Applied Mathematics', 'Physics & Physical Sciences', 'Chemical Engineering',
            'Fine Art & Industrial Design', 'Social Sciences', 'Foreign Languages', 'Biomedical Laboratory'
        ]
        
        departments = []
        courses = []
        course_units = []
        streams = []

        for i, d_name in enumerate(dept_names, start=1):
            dept, _ = Department.objects.get_or_create(name=d_name)
            departments.append(dept)

            c_code = f"CRS{i:02d}"
            course, _ = Course.objects.get_or_create(
                code=c_code,
                defaults={'name': f"Bachelor of {d_name}", 'department': dept}
            )
            courses.append(course)

            cu_code = f"UNIT{i:02d}"
            unit, _ = CourseUnit.objects.get_or_create(
                code=cu_code,
                defaults={'name': f"Advanced Principles of {d_name}", 'course': course}
            )
            course_units.append(unit)

            stream, _ = Stream.objects.get_or_create(
                name=f"Class Stream {i:02d} - A",
                course=course
            )
            streams.append(stream)

        self.stdout.write(f'✅ Seeded {len(departments)} Departments, {len(courses)} Courses, {len(course_units)} Units & {len(streams)} Streams.')

        # ==========================================
        # 4. TEACHERS, STUDENTS & PARENTS (20+ EACH)
        # ==========================================
        teachers = []
        for i in range(1, 21):
            username = f"teacher_{i:02d}"
            u, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f"{username}@utc.ac.ug", 'role': User.IS_TEACHER}
            )
            if created:
                u.set_password('teacher123')
                u.save()
            tp, _ = TeacherProfile.objects.get_or_create(user=u, defaults={'name': f"Prof. Instructor {i:02d}"})
            tp.courses.add(courses[(i - 1) % len(courses)])
            teachers.append(tp)

        students = []
        for i in range(1, 26):
            reg_num = f"2025/REG/{i:03d}"
            username = f"student_{i:02d}"
            u, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f"{username}@utc.ac.ug", 'role': User.IS_STUDENT}
            )
            if created:
                u.set_password('student123')
                u.save()
            sp, _ = StudentProfile.objects.get_or_create(
                reg_number=reg_num,
                defaults={
                    'user': u,
                    'name': f"Student Candidate {i:02d}",
                    'course': courses[(i - 1) % len(courses)],
                    'stream': streams[(i - 1) % len(streams)]
                }
            )
            students.append(sp)

        parents = []
        for i in range(1, 21):
            username = f"parent_{i:02d}"
            u, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f"{username}@utc.ac.ug", 'role': User.IS_PARENT}
            )
            if created:
                u.set_password('parent123')
                u.save()
            pp, _ = ParentProfile.objects.get_or_create(
                user=u,
                defaults={'name': f"Parent Guardian {i:02d}", 'phone': f"+256770000{i:02d}"}
            )
            pp.students.add(students[(i - 1) % len(students)])
            parents.append(pp)

        self.stdout.write(f'✅ Seeded {len(teachers)} Teachers, {len(students)} Students, and {len(parents)} Parents.')

        # ==========================================
        # 5. HOSTELS, ROOMS & ALLOCATIONS (20 EACH)
        # ==========================================
        hostels = []
        rooms = []
        room_allocations = []

        for i in range(1, 21):
            h, _ = Hostel.objects.get_or_create(
                name=f"Residential Hall {i:02d}",
                defaults={'location': f"Campus Zone {chr(65 + (i % 6))}"}
            )
            hostels.append(h)

            r, _ = Room.objects.get_or_create(
                hostel=h,
                name_or_number=f"Room {100 + i}",
                defaults={'capacity': 4}
            )
            rooms.append(r)

            ra, _ = RoomAllocation.objects.get_or_create(
                student=students[i - 1],
                term=current_term,
                defaults={'room': r, 'allocated_by': warden_user}
            )
            room_allocations.append(ra)

        self.stdout.write(f'✅ Seeded {len(hostels)} Hostels, {len(rooms)} Rooms, and {len(room_allocations)} Allocations.')

        # ==========================================
        # 6. LIBRARY BOOKS, REQUESTS & RECORDS (20 EACH)
        # ==========================================
        books = []
        reserve_requests = []
        library_records = []

        for i in range(1, 21):
            bk, _ = Book.objects.get_or_create(
                isbn=f"978-0-13-10200{i:02d}",
                defaults={
                    'title': f"Academic Reference Volume {i:02d}",
                    'author': f"Author Scholar {i:02d}",
                    'total_copies': 10,
                    'available_copies': 5,
                    'department': departments[(i - 1) % len(departments)],
                    'is_reserve': (i % 2 == 0)
                }
            )
            books.append(bk)

            rr, _ = ReserveRequest.objects.get_or_create(
                student=students[i - 1],
                book=bk,
                defaults={
                    'status': random.choice(['PENDING', 'APPROVED', 'COMPLETED']),
                    'purpose_notes': f"Research reference requirement module {i:02d}"
                }
            )
            reserve_requests.append(rr)

            lr, _ = LibraryRecord.objects.get_or_create(
                student=students[i - 1],
                book=bk,
                defaults={
                    'issue_date': today_date - timedelta(days=15),
                    'due_date': today_date + timedelta(days=15),
                    'status': 'ISSUED',
                    'remarks': 'Standard library checkout'
                }
            )
            library_records.append(lr)

        self.stdout.write(f'✅ Seeded {len(books)} Books, {len(reserve_requests)} Reserve Requests, and {len(library_records)} Library Records.')

        # ==========================================
        # 7. FINANCIAL LEDGERS & SALARIES (20 EACH)
        # ==========================================
        term_fees = []
        fee_transactions = []
        staff_salaries = []

        for i in range(1, 21):
            stf, _ = StudentTermFee.objects.get_or_create(
                student=students[i - 1],
                term=current_term,
                defaults={
                    'total_fees_due': Decimal('1800000.00'),
                    'total_amount_paid': Decimal('1200000.00')
                }
            )
            term_fees.append(stf)

            txn, _ = FeePaymentTransaction.objects.get_or_create(
                reference_number=f"PAY-TXN-2025-{i:03d}",
                defaults={
                    'term_fee_account': stf,
                    'amount': Decimal('1200000.00'),
                    'payment_method': 'BANK_DEPOSIT',
                    'is_confirmed': True,
                    'processed_by': accountant_user
                }
            )
            fee_transactions.append(txn)

            spr, _ = StaffPaymentRecord.objects.get_or_create(
                reference_number=f"SAL-PAY-2025-{i:03d}",
                defaults={
                    'staff': teachers[i - 1].user,
                    'amount': Decimal('3200000.00'),
                    'payment_date': today_date - timedelta(days=5),
                    'payment_method': 'BANK_TRANSFER',
                    'description': f"Monthly Salary Payment {i:02d}",
                    'term': current_term,
                    'processed_by': accountant_user
                }
            )
            staff_salaries.append(spr)

        self.stdout.write(f'✅ Seeded {len(term_fees)} Term Fees, {len(fee_transactions)} Fee Transactions & {len(staff_salaries)} Staff Payments.')

        # ==========================================
        # 8. DISCIPLINARY RECORDS (20 ENTRIES)
        # ==========================================
        disciplinary_records = []
        for i in range(1, 21):
            disc, _ = DisciplinaryRecord.objects.get_or_create(
                student=students[i - 1],
                subject=f"Disciplinary Hearing #{i:02d}",
                defaults={
                    'details': f"Student involved in minor campus guideline infraction #{i:02d}",
                    'severity': random.choice(['MILD', 'SEVERE', 'VERY_SEVERE']),
                    'reported_by': teachers[i - 1].user,
                    'term': current_term
                }
            )
            disciplinary_records.append(disc)

        self.stdout.write(f'✅ Seeded {len(disciplinary_records)} Disciplinary Records.')

        # ==========================================
        # 9. TIMETABLE & ATTENDANCE LOGS (20 EACH)
        # ==========================================
        batches = []
        entries = []
        sessions = []
        attendance_records = []

        days = ['MON', 'TUE', 'WED', 'THU', 'FRI']

        for i in range(1, 21):
            tb, _ = TimetableBatch.objects.get_or_create(
                week_start_date=today_date - timedelta(weeks=i),
                defaults={'is_active': (i == 1), 'is_revoked': False, 'term': current_term}
            )
            batches.append(tb)

            te, _ = TimetableEntry.objects.get_or_create(
                batch=tb,
                day=days[i % 5],
                start_time=time(9, 0),
                end_time=time(11, 0),
                course_unit=course_units[i - 1],
                defaults={'teacher': teachers[i - 1], 'stream': streams[i - 1]}
            )
            entries.append(te)

            atts, _ = AttendanceSession.objects.get_or_create(
                timetable_entry=te,
                defaults={
                    'teacher_latitude': Decimal('0.347596'),
                    'teacher_longitude': Decimal('32.582520')
                }
            )
            sessions.append(atts)

            ar, _ = AttendanceRecord.objects.get_or_create(
                session=atts,
                student=students[i - 1],
                defaults={'status': 'PRESENT'}
            )
            attendance_records.append(ar)

        self.stdout.write(f'✅ Seeded {len(batches)} Batches, {len(entries)} Entries, {len(sessions)} Sessions & {len(attendance_records)} Attendance Records.')

        # ==========================================
        # 10. EXAMINATIONS & MARKS (20 EACH)
        # ==========================================
        grade_scales = []
        exams = []
        marks_entries = []
        transcripts = []

        grade_data = [
            ('A+', 90, 100, 5.0, 'Exceptional'), ('A', 80, 89, 4.0, 'Excellent'),
            ('B+', 75, 79, 3.5, 'Very Good'), ('B', 70, 74, 3.0, 'Good'),
            ('C+', 65, 69, 2.5, 'Fairly Good'), ('C', 60, 64, 2.0, 'Satisfactory'),
            ('D+', 55, 59, 1.5, 'Pass'), ('D', 50, 54, 1.0, 'Bare Pass'),
            ('F', 0, 49, 0.0, 'Fail'), ('Distinction', 85, 100, 4.5, 'High Distinction'),
            ('Merit', 75, 84, 3.5, 'Honors'), ('Credit', 65, 74, 2.5, 'Credit Pass'),
            ('Pass', 50, 64, 1.5, 'General Pass'), ('Marginal Fail', 45, 49, 0.5, 'Re-sit Required'),
            ('Ungraded', 0, 0, 0.0, 'Audit'), ('A- Honors', 82, 85, 4.2, 'Top Class'),
            ('B- Satisfactory', 67, 69, 2.7, 'Average'), ('Upper Second', 72, 77, 3.2, 'Commendable'),
            ('Lower Second', 62, 66, 2.2, 'Acceptable'), ('Sub-Pass', 48, 51, 0.8, 'Warning Pass')
        ]

        for name, min_s, max_s, gp, rem in grade_data:
            gs, _ = GradeScale.objects.get_or_create(
                name=name,
                defaults={'min_score': min_s, 'max_score': max_s, 'grade_point': Decimal(str(gp)), 'remark': rem}
            )
            grade_scales.append(gs)

        for i in range(1, 21):
            ex, _ = Exam.objects.get_or_create(
                name=f"End of Term Exam #{i:02d}",
                course_unit=course_units[i - 1],
                term=current_term,
                defaults={
                    'exam_date': today_date + timedelta(days=10),
                    'start_time': time(9, 0),
                    'end_time': time(12, 0),
                    'total_marks': 100,
                    'is_published': True
                }
            )
            exams.append(ex)

            me, _ = MarksEntry.objects.get_or_create(
                student=students[i - 1],
                exam=ex,
                defaults={
                    'marks_obtained': Decimal('84.50'),
                    'grade': grade_scales[1],
                    'remarks': 'Outstanding Performance',
                    'entered_by': teachers[i - 1].user
                }
            )
            marks_entries.append(me)

            tr, _ = Transcript.objects.get_or_create(
                student=students[i - 1],
                term=current_term
            )
            transcripts.append(tr)

        self.stdout.write(f'✅ Seeded {len(grade_scales)} Grade Scales, {len(exams)} Exams, {len(marks_entries)} Marks & {len(transcripts)} Transcripts.')

        # ==========================================
        # 11. INVENTORY & ASSETS (20 EACH)
        # ==========================================
        suppliers = []
        inventory_items = []
        assets = []
        procurements = []
        stock_movements = []

        categories = ['FURNITURE', 'ELECTRONICS', 'STATIONERY', 'SPORTS', 'LAB', 'OTHER']

        for i in range(1, 21):
            sup, _ = Supplier.objects.get_or_create(
                name=f"Enterprise Supplier {i:02d}",
                defaults={
                    'contact_person': f"Vendor Representative {i:02d}",
                    'phone': f"+256780000{i:02d}",
                    'email': f"vendor{i:02d}@suppliers.com",
                    'address': f"Plot {i}, Industrial Park Road"
                }
            )
            suppliers.append(sup)

            item, _ = InventoryItem.objects.get_or_create(
                name=f"Institutional Inventory Item {i:02d}",
                defaults={
                    'category': categories[i % len(categories)],
                    'quantity': 100,
                    'unit_price': Decimal('150000.00'),
                    'supplier': sup,
                    'location': f"Main Central Store Depot {i:02d}",
                    'reorder_level': 15,
                    'description': f"Standard inventory supply item #{i:02d}"
                }
            )
            inventory_items.append(item)

            ast, _ = Asset.objects.get_or_create(
                asset_tag=f"UTC-AST-2025-{i:03d}",
                defaults={
                    'item': item,
                    'serial_number': f"SN-990022-{i:03d}",
                    'purchase_date': today_date - timedelta(days=200),
                    'warranty_expiry': today_date + timedelta(days=500),
                    'assigned_to': teachers[i - 1].user,
                    'status': 'IN_USE'
                }
            )
            assets.append(ast)

            proc, _ = Procurement.objects.get_or_create(
                item=item,
                quantity=20,
                unit_cost=Decimal('150000.00'),
                supplier=sup,
                defaults={
                    'expected_delivery': today_date + timedelta(days=14),
                    'status': 'APPROVED',
                    'approved_by': admin_user
                }
            )
            procurements.append(proc)

            sm, _ = StockMovement.objects.get_or_create(
                item=item,
                quantity=50,
                movement_type='IN',
                reference=f"INV-REF-{i:03d}",
                defaults={'remarks': f"Initial store stock input batch {i:02d}"}
            )
            stock_movements.append(sm)

        self.stdout.write(f'✅ Seeded {len(suppliers)} Suppliers, {len(inventory_items)} Items, {len(assets)} Assets, {len(procurements)} Procurements & {len(stock_movements)} Stock Movements.')

        # ==========================================
        # 12. TRANSPORTation MODULE (20 EACH)
        # ==========================================
        vehicles = []
        routes = []
        transport_allocations = []
        trip_logs = []

        for i in range(1, 21):
            veh, _ = Vehicle.objects.get_or_create(
                registration_number=f"UBX {100 + i}A",
                defaults={
                    'model': f"Toyota Coaster Bus Model {i:02d}",
                    'capacity': 30,
                    'driver_name': f"Driver Officer {i:02d}",
                    'driver_contact': f"+256700000{i:02d}",
                    'status': 'ACTIVE'
                }
            )
            vehicles.append(veh)

            rt, _ = Route.objects.get_or_create(
                name=f"Transport Route Line {i:02d}",
                defaults={
                    'vehicle': veh,
                    'start_location': f"Campus Terminal {i:02d}",
                    'end_location': f"Suburban Hub {i:02d}",
                    'departure_time': time(7, 0),
                    'arrival_time': time(8, 30),
                    'days_of_week': 'MON,TUE,WED,THU,FRI'
                }
            )
            routes.append(rt)

            ta, _ = TransportAllocation.objects.get_or_create(
                student=students[i - 1],
                term=current_term,
                defaults={'route': rt, 'is_active': True}
            )
            transport_allocations.append(ta)

            tl, _ = TripLog.objects.get_or_create(
                vehicle=veh,
                route=rt,
                departure_time=timezone.now() - timedelta(hours=4),
                defaults={
                    'arrival_time': timezone.now() - timedelta(hours=2),
                    'driver_name': veh.driver_name,
                    'mileage_start': 10000 + (i * 100),
                    'mileage_end': 10050 + (i * 100),
                    'remarks': f"Daily route commute log #{i:02d}"
                }
            )
            trip_logs.append(tl)

        self.stdout.write(f'✅ Seeded {len(vehicles)} Vehicles, {len(routes)} Routes, {len(transport_allocations)} Allocations & {len(trip_logs)} Trip Logs.')

        # ==========================================
        # 13. HUMAN RESOURCES & EVALUATIONS (20 EACH)
        # ==========================================
        qualifications = []
        leave_requests = []
        performance_evaluations = []

        leave_types = ['ANNUAL', 'SICK', 'MATERNITY', 'PATERNITY', 'OTHER']

        for i in range(1, 21):
            qual, _ = Qualification.objects.get_or_create(
                staff=teachers[i - 1].user,
                qualification_name=f"Master of Science Degree {i:02d}",
                defaults={
                    'institution': f"National University {i:02d}",
                    'year_awarded': 2015 + (i % 8)
                }
            )
            qualifications.append(qual)

            lr, _ = LeaveRequest.objects.get_or_create(
                staff=teachers[i - 1].user,
                start_date=today_date + timedelta(days=10),
                end_date=today_date + timedelta(days=20),
                defaults={
                    'leave_type': leave_types[i % len(leave_types)],
                    'reason': f"Annual sabbatical and leave duration #{i:02d}",
                    'status': 'APPROVED',
                    'approved_by': admin_user
                }
            )
            leave_requests.append(lr)

            pe, _ = PerformanceEvaluation.objects.get_or_create(
                staff=teachers[i - 1].user,
                term=current_term,
                defaults={
                    'evaluator': admin_user,
                    'score': 85 + (i % 15),
                    'comments': f"Exceptional teaching and academic performance rating #{i:02d}"
                }
            )
            performance_evaluations.append(pe)

        self.stdout.write(f'✅ Seeded {len(qualifications)} Qualifications, {len(leave_requests)} Leave Requests & {len(performance_evaluations)} Performance Evaluations.')

        # ==========================================
        # 14. E-LEARNING & ONLINE LMS (20 EACH)
        # ==========================================
        online_courses = []
        lessons = []
        assignments = []
        submissions = []
        online_exams = []
        online_questions = []
        online_answers = []
        notes = []

        for i in range(1, 21):
            oc, _ = OnlineCourse.objects.get_or_create(
                name=f"E-Learning Module Course {i:02d}",
                course_unit=course_units[i - 1],
                defaults={
                    'description': f"Online learning module setup for unit {i:02d}",
                    'instructor': teachers[i - 1],
                    'start_date': today_date - timedelta(days=30),
                    'end_date': today_date + timedelta(days=60),
                    'is_active': True
                }
            )
            online_courses.append(oc)

            les, _ = Lesson.objects.get_or_create(
                online_course=oc,
                title=f"Lesson Lecture #{i:02d}",
                defaults={
                    'content': f"Interactive lesson contents and lecture notes for module #{i:02d}",
                    'video_url': f"https://learning.utc.ac.ug/videos/lecture_{i:02d}",
                    'order': i
                }
            )
            lessons.append(les)

            assign, _ = Assignment.objects.get_or_create(
                lesson=les,
                title=f"Practical Assignment #{i:02d}",
                defaults={
                    'description': f"Solve exercises detailed in lecture packet #{i:02d}",
                    'due_date': timezone.now() + timedelta(days=7),
                    'max_score': 100
                }
            )
            assignments.append(assign)

            sub, _ = Submission.objects.get_or_create(
                assignment=assign,
                student=students[i - 1],
                defaults={
                    'score': Decimal('92.00'),
                    'feedback': 'Excellent analysis and problem solving.',
                    'graded_by': teachers[i - 1].user
                }
            )
            submissions.append(sub)

            oe, _ = OnlineExam.objects.get_or_create(
                online_course=oc,
                title=f"Online Continuous Assessment #{i:02d}",
                defaults={
                    'description': f"Digital test for module unit #{i:02d}",
                    'start_time': timezone.now() - timedelta(hours=2),
                    'end_time': timezone.now() + timedelta(hours=2),
                    'total_marks': 50,
                    'is_published': True
                }
            )
            online_exams.append(oe)

            oeq, _ = OnlineExamQuestion.objects.get_or_create(
                online_exam=oe,
                question_text=f"Explain core concepts regarding practical scenario #{i:02d}?",
                defaults={'marks': 10}
            )
            online_questions.append(oeq)

            oea, _ = OnlineExamAnswer.objects.get_or_create(
                question=oeq,
                student=students[i - 1],
                defaults={
                    'answer_text': f"Comprehensive student response for online question #{i:02d}",
                    'score': Decimal('9.50'),
                    'graded_by': teachers[i - 1].user
                }
            )
            online_answers.append(oea)

            nt, _ = Note.objects.get_or_create(
                online_course=oc,
                title=f"Revision Reference Note #{i:02d}",
                defaults={'content': f"Important exam preparation summary guidelines for course #{i:02d}"}
            )
            notes.append(nt)

        self.stdout.write(f'✅ Seeded {len(online_courses)} Online Courses, {len(lessons)} Lessons, {len(assignments)} Assignments, {len(submissions)} Submissions, {len(online_exams)} Online Exams, {len(online_questions)} Questions, {len(online_answers)} Answers & {len(notes)} Notes.')

        # ==========================================
        # COMPLETION SUMMARY
        # ==========================================
        self.stdout.write(self.style.SUCCESS('\n🎉 SUCCESS: All 47 tables fully seeded with at least 20 entries each! Database is ready.'))