from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, F
from django.contrib import messages
from django.http import HttpResponse
from datetime import date

from attendance.models import (
    StudentProfile, Hostel, AcademicTerm, Faculty, Department, Course, User
)
from .models import ResidenceApplication, StudentApprovalRequest


@login_required
def students_dashboard(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    total_students = StudentProfile.objects.count()
    active_students = StudentProfile.objects.filter(user__is_active=True, is_blocked=False).count()
    inactive_students = StudentProfile.objects.filter(user__is_active=False).count()
    blocked_students = StudentProfile.objects.filter(is_blocked=True).count()
    
    pct_active = round((active_students / total_students * 100), 2) if total_students > 0 else 0.0

    # Summary by Academic Status
    academic_statuses = StudentProfile.objects.values('academic_status').annotate(
        male=Count('pk', filter=Q(gender='MALE')),
        female=Count('pk', filter=Q(gender='FEMALE')),
        total=Count('pk')
    )

    # Summary by Billing Categories
    billing_categories = StudentProfile.objects.values('billing_category').annotate(
        male=Count('pk', filter=Q(gender='MALE')),
        female=Count('pk', filter=Q(gender='FEMALE')),
        total=Count('pk')
    )

    # Summary by Intake
    intakes = StudentProfile.objects.values('intake').annotate(
        male=Count('pk', filter=Q(gender='MALE')),
        female=Count('pk', filter=Q(gender='FEMALE')),
        total=Count('pk')
    )

    # Summary by Sponsorship
    sponsorships = StudentProfile.objects.values('sponsorship').annotate(
        male=Count('pk', filter=Q(gender='MALE')),
        female=Count('pk', filter=Q(gender='FEMALE')),
        total=Count('pk')
    )

    context = {
        'active_students': active_students,
        'inactive_students': inactive_students,
        'blocked_students': blocked_students,
        'pct_active': pct_active,
        'academic_statuses': academic_statuses,
        'billing_categories': billing_categories,
        'intakes': intakes,
        'sponsorships': sponsorships,
    }
    return render(request, 'attendance/students_records/dashboard.html', context)

import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Q
from .models import User, ResidenceApplication, StudentProfile, AcademicTerm, Hostel

@login_required
def residence_applications(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    # ==================== POST ACTION HANDLERS ====================
    if request.method == "POST":
        action = request.POST.get('action')

        # 1. Create Single Residence Application
        if action == 'create':
            reg_number = request.POST.get('reg_number')
            term_id = request.POST.get('academic_term')
            res_type = request.POST.get('residence_type', 'CAMPUS')
            hall_id = request.POST.get('hall')
            payment_status = request.POST.get('payment_status', 'PENDING')

            try:
                student = StudentProfile.objects.get(reg_number=reg_number)
                term = AcademicTerm.objects.get(id=term_id)
                hall = Hostel.objects.get(id=hall_id) if hall_id else None

                ResidenceApplication.objects.create(
                    student=student,
                    academic_term=term,
                    residence_type=res_type,
                    hall=hall,
                    payment_status=payment_status
                )
                messages.success(request, f"Residence application created for {student.name}.")
            except StudentProfile.DoesNotExist:
                messages.error(request, f"Student reg number '{reg_number}' not found.")
            except Exception as e:
                messages.error(request, f"Error creating application: {str(e)}")

        # 2. Edit Application
        elif action == 'edit':
            app_id = request.POST.get('app_id')
            app_obj = get_object_or_404(ResidenceApplication, id=app_id)

            term_id = request.POST.get('academic_term')
            res_type = request.POST.get('residence_type')
            hall_id = request.POST.get('hall')
            payment_status = request.POST.get('payment_status')

            if term_id:
                app_obj.academic_term_id = term_id
            if res_type:
                app_obj.residence_type = res_type
            app_obj.hall_id = hall_id if hall_id else None
            if payment_status:
                app_obj.payment_status = payment_status

            app_obj.save()
            messages.success(request, "Residence application updated successfully.")

        # 3. Delete Application
        elif action == 'delete':
            app_id = request.POST.get('app_id')
            app_obj = get_object_or_404(ResidenceApplication, id=app_id)
            app_obj.delete()
            messages.success(request, "Residence application deleted successfully.")

        # 4. Upload CSV Student Applications
        elif action == 'upload_csv':
            csv_file = request.FILES.get('csv_file')
            if not csv_file or not csv_file.name.endswith('.csv'):
                messages.error(request, "Please upload a valid .csv file.")
            else:
                try:
                    file_data = csv_file.read().decode('utf-8')
                    csv_data = csv.DictReader(io.StringIO(file_data))
                    count = 0

                    for row in csv_data:
                        reg_num = row.get('reg_number', '').strip()
                        term_id = row.get('term_id', '').strip()
                        res_type = row.get('residence_type', 'CAMPUS').strip()
                        hall_id = row.get('hall_id', '').strip()
                        pay_status = row.get('payment_status', 'PENDING').strip()

                        student = StudentProfile.objects.filter(reg_number=reg_num).first()
                        term = AcademicTerm.objects.filter(id=term_id).first() if term_id else AcademicTerm.objects.filter(is_current=True).first()

                        if student and term:
                            hall = Hostel.objects.filter(id=hall_id).first() if hall_id else None
                            ResidenceApplication.objects.update_or_create(
                                student=student,
                                academic_term=term,
                                defaults={
                                    'residence_type': res_type,
                                    'hall': hall,
                                    'payment_status': pay_status
                                }
                            )
                            count += 1
                    messages.success(request, f"Successfully processed {count} records from CSV.")
                except Exception as e:
                    messages.error(request, f"CSV processing error: {str(e)}")

        return redirect(request.get_full_path())

    # ==================== GET / FILTERING & SEARCH ====================
    res_type = request.GET.get('residence_type', '')
    term_id = request.GET.get('academic_term', '')
    hall_id = request.GET.get('hall', '')
    payment_tab = request.GET.get('status', request.GET.get('tab', 'all')).lower()
    search_query = request.GET.get('q', '').strip()

    apps = ResidenceApplication.objects.select_related('student', 'academic_term', 'hall')

    if search_query:
        apps = apps.filter(
            Q(student__reg_number__icontains=search_query) |
            Q(student__name__icontains=search_query)
        )
    if res_type:
        apps = apps.filter(residence_type=res_type)
    if term_id:
        apps = apps.filter(academic_term_id=term_id)
    if hall_id:
        apps = apps.filter(hall_id=hall_id)
    if payment_tab == 'paid':
        apps = apps.filter(payment_status='PAID')
    elif payment_tab == 'pending':
        apps = apps.filter(payment_status='PENDING')

    context = {
        'applications': apps,
        'terms': AcademicTerm.objects.all(),
        'halls': Hostel.objects.all(),
        'students': StudentProfile.objects.all(),
        'current_tab': payment_tab,
    }
    return render(request, 'attendance/students_records/residence_applications.html', context)




from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q
from django.contrib import messages
from .models import StudentProfile, Faculty, Department, Course, Stream, User

@login_required
def invalid_dob_students(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    today = date.today()
    min_age_date = date(today.year - 10, today.month, today.day)

    # Handle POST Actions: Add, Edit, Delete
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            reg_number = request.POST.get('reg_number')
            name = request.POST.get('name')
            dob = request.POST.get('date_of_birth') or None
            course_code = request.POST.get('course')
            stream_id = request.POST.get('stream')

            if StudentProfile.objects.filter(reg_number=reg_number).exists():
                messages.error(request, f"Student with registration number '{reg_number}' already exists.")
            else:
                user = User.objects.create_user(username=reg_number, role=User.IS_STUDENT)
                course = get_object_or_404(Course, pk=course_code)
                stream = get_object_or_404(Stream, pk=stream_id)
                
                StudentProfile.objects.create(
                    reg_number=reg_number,
                    user=user,
                    name=name,
                    date_of_birth=dob,
                    course=course,
                    stream=stream
                )
                messages.success(request, f"Student record for {name} ({reg_number}) created successfully.")

        elif action == 'edit':
            reg_number = request.POST.get('reg_number')
            student = get_object_or_404(StudentProfile, reg_number=reg_number)
            student.name = request.POST.get('name', student.name)
            
            dob = request.POST.get('date_of_birth')
            student.date_of_birth = dob if dob else None
            
            course_code = request.POST.get('course')
            if course_code:
                student.course = get_object_or_404(Course, pk=course_code)
                
            stream_id = request.POST.get('stream')
            if stream_id:
                student.stream = get_object_or_404(Stream, pk=stream_id)

            student.save()
            messages.success(request, f"Updated record for {student.name} ({student.reg_number}).")

        elif action == 'delete':
            reg_number = request.POST.get('reg_number')
            student = get_object_or_404(StudentProfile, reg_number=reg_number)
            user = student.user
            student.delete()
            if user:
                user.delete()
            messages.success(request, f"Student record {reg_number} deleted successfully.")

        return redirect('attendance:invalid_dob_students')

    # GET Request Processing
    group_by = request.GET.get('group_by', 'programme').lower()

    # Query for invalid DOB (Missing, Future Date, or under 10 years old)
    invalid_qs = StudentProfile.objects.filter(
        Q(date_of_birth__isnull=True) | 
        Q(date_of_birth__gt=today) | 
        Q(date_of_birth__gt=min_age_date)
    ).select_related('course__department__faculty', 'stream')

    context = {
        'invalid_students': invalid_qs,
        'group_by': group_by,
        'faculties': Faculty.objects.all(),
        'departments': Department.objects.all(),
        'courses': Course.objects.all(),
        'streams': Stream.objects.all(),
        'today_str': today.strftime('%Y-%m-%d'),
        'min_age_str': min_age_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'attendance/students_records/invalid_dob.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponse
from .models import StudentProfile, User  # Adjust import paths to match your app structure

@login_required
@transaction.atomic
def blocked_students_management(request):
    # Support both custom role check and Django staff status
    if not (request.user.is_staff or getattr(request.user, 'role', None) == getattr(User, 'IS_ADMIN', 'ADMIN')):
        return HttpResponse("Unauthorized", status=403)

    if request.method == 'POST':
        # Safely capture reg_number matching the template field name
        reg_number = request.POST.get('reg_number') or request.POST.get('student_id')
        action = request.POST.get('action') # 'block' or 'unblock'
        
        student = get_object_or_404(StudentProfile, reg_number=reg_number)
        student.is_blocked = (action == 'block')
        student.save()

        student_name = getattr(student, 'name', None) or getattr(student, 'full_name', student.reg_number)
        status_text = 'Blocked' if student.is_blocked else 'Unblocked'
        
        messages.success(request, f"Student {student_name} status updated to {status_text}.")
        return redirect('attendance:blocked_students')

    # Query Search and Status Filtering
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'ALL').upper()

    students = StudentProfile.objects.select_related('user', 'course')

    if query:
        students = students.filter(
            Q(reg_number__icontains=query) | 
            Q(name__icontains=query)
        )

    if status_filter == 'BLOCKED':
        students = students.filter(is_blocked=True)
    elif status_filter == 'UNBLOCKED':
        students = students.filter(is_blocked=False)

    return render(request, 'attendance/students_records/blocked_students.html', {
        'students': students,
        'status_filter': status_filter,
        'query': query,
    })

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from .models import User, StudentApprovalRequest, StudentProfile

@login_required
def students_approvals(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    # ==================== HANDLE POST (CRUD & APPROVALS) ====================
    if request.method == 'POST':
        action = request.POST.get('action')
        request_id = request.POST.get('request_id')

        if action == 'create':
            student_id = request.POST.get('student')
            req_type = request.POST.get('request_type')
            status = request.POST.get('status', 'PENDING')
            notes = request.POST.get('payload_data', '{}').strip()

            try:
                payload = json.loads(notes) if notes.startswith('{') or notes.startswith('[') else {"notes": notes}
            except json.JSONDecodeError:
                payload = {"notes": notes}

            student = StudentProfile.objects.filter(pk=student_id).first() if student_id else None

            StudentApprovalRequest.objects.create(
                student=student,
                request_type=req_type,
                requested_by=request.user,
                payload_data=payload,
                status=status
            )
            messages.success(request, "Approval request created successfully.")

        elif action == 'edit':
            approval_req = get_object_or_404(StudentApprovalRequest, id=request_id)
            student_id = request.POST.get('student')
            req_type = request.POST.get('request_type')
            status = request.POST.get('status')
            notes = request.POST.get('payload_data', '{}').strip()

            try:
                payload = json.loads(notes) if notes.startswith('{') or notes.startswith('[') else {"notes": notes}
            except json.JSONDecodeError:
                payload = {"notes": notes}

            approval_req.student = StudentProfile.objects.filter(pk=student_id).first() if student_id else None
            approval_req.request_type = req_type
            approval_req.status = status
            approval_req.payload_data = payload
            approval_req.save()
            messages.success(request, f"Request #REQ-{approval_req.id} updated successfully.")

        elif action == 'delete':
            approval_req = get_object_or_404(StudentApprovalRequest, id=request_id)
            approval_req.delete()
            messages.success(request, f"Request #REQ-{request_id} deleted successfully.")

        elif action in ['approve', 'reject']:
            approval_req = get_object_or_404(StudentApprovalRequest, id=request_id)
            approval_req.status = 'APPROVED' if action == 'approve' else 'REJECTED'
            approval_req.reviewed_by = request.user
            approval_req.save()
            messages.success(request, f"Request #REQ-{approval_req.id} status updated to {approval_req.status}.")

        return redirect(request.path)

    # ==================== HANDLE GET (FETCH ALL RECORDS FOR FRONTEND FILTERING) ====================
    requests_qs = StudentApprovalRequest.objects.select_related('student', 'requested_by').all()
    students = StudentProfile.objects.all()

    return render(request, 'attendance/students_records/approvals.html', {
        'approval_requests': requests_qs,
        'students': students,
        'request_type_choices': StudentApprovalRequest.REQUEST_TYPES,
        'status_choices': StudentApprovalRequest.STATUS_CHOICES,
    })