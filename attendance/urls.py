from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from attendance import views_admin, views_users, views_analytics, views
from django.urls import path, reverse_lazy

app_name = 'attendance'

urlpatterns = [
    # Baseline Root Landing Page Routing
    path('', views_users.home, name='home'),
    path('my-apps/', views_users.my_apps, name='my_apps'),
    
    # Auth routing infrastructure
    path('login/', views.custom_login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Execution Environment Hubs
    path('dashboard/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('teacher/dashboard/', views_users.teacher_dashboard, name='teacher_dashboard'),
    path('student/dashboard/', views_users.student_dashboard, name='student_dashboard'),

    # Data pipeline ingest arrays
    path('admin-ui/upload/courses/', views_admin.bulk_upload_courses, name='bulk_upload_courses'),
    path('admin-ui/upload/teachers/', views_admin.bulk_upload_teachers, name='bulk_upload_teachers'),
    path('admin-ui/upload/students/', views_admin.bulk_upload_students, name='bulk_upload_students'),

    # 1. Dashboard directory listing all streams/classes and their timetable statuses
    path('timetable/manage/', views_admin.manage_timetable, name='manage_timetable'),
    # 2. Scoped interactive matrix editor for a specific stream/class
    path('timetable/upload/<int:stream_id>/', views_admin.upload_timetable, name='upload_timetable'),
    #path('admin-ui/upload/timetable/', views_admin.upload_timetable, name='upload_timetable'),

    # Outbound structural export arrays
    path('admin-ui/export/credentials/<str:role_type>/', views_admin.export_credentials, name='export_credentials'),
    path('admin-ui/download-template/<str:template_type>/', views_admin.download_template, name='download_template'),

    # Interactive interface transaction routes
    path('teacher/attendance/mark/<int:entry_id>/', views_users.mark_attendance, name='mark_attendance'),

    # Telemetry streaming engine data feeds
    path('analytics/global/json/', views_analytics.global_analytics_data, name='global_analytics_data'),

    # Student report download
    path('student/report/download/', views_users.download_student_report, name='download_student_report'),
    
    # Core Directory Management Views
    path('user-admin/manage-teachers/', views_admin.manage_teachers, name='manage_teachers'),
    path('user-admin/manage-students/', views_admin.manage_students, name='manage_students'),
    path('user-admin/manage-courses/', views_admin.manage_courses, name='manage_courses'),
    path('user-admin/manage-course-units/', views_admin.manage_course_units, name='manage_course_units'),

    # =========================================================================
    # CRITICAL RECORD EDIT / DELETE ROUTING ENGINE
    # =========================================================================
    
    # Teachers CRUD Extensions (Standard Auto-Increment Integer Keys)
    path('user-admin/manage-teachers/edit/<int:pk>/', views_admin.edit_teacher, name='edit_teacher'),
    path('user-admin/manage-teachers/delete/<int:pk>/', views_admin.delete_teacher, name='delete_teacher'),

    # Students CRUD Extensions (FIXED: Uses path to accommodate slashes in Reg Numbers)
    path('user-admin/manage-students/edit/<path:pk>/', views_admin.edit_student, name='edit_student'),
    path('user-admin/manage-students/delete/<path:pk>/', views_admin.delete_student, name='delete_student'),

    # Courses CRUD Extensions (String Alphanumeric Primary Keys)
    path('user-admin/manage-courses/edit/<str:pk>/', views_admin.edit_course, name='edit_course'),
    path('user-admin/manage-courses/delete/<str:pk>/', views_admin.delete_course, name='delete_course'),

    # Course Units CRUD Extensions (String Alphanumeric Primary Keys)
    path('user-admin/manage-course-units/edit/<str:pk>/', views_admin.edit_course_unit, name='edit_course_unit'),
    path('user-admin/manage-course-units/delete/<str:pk>/', views_admin.delete_course_unit, name='delete_course_unit'),
    path('change-password/', views.change_password_view, name='change_password'),

    path('management/streams/', views_admin.manage_streams, name='manage_streams'),
    path('management/streams/edit/<int:stream_id>/', views_admin.edit_stream, name='edit_stream'),
    path('management/streams/delete/<int:stream_id>/', views_admin.delete_stream, name='delete_stream'),
    path('management/streams/bulk-upload/', views_admin.bulk_upload_streams, name='bulk_upload_streams'),


    # Department Management Routes
    path('departments/', views_admin.manage_departments, name='manage_departments'),
    path('departments/edit/<int:pk>/', views_admin.edit_department, name='edit_department'),
    path('departments/delete/<int:pk>/', views_admin.delete_department, name='delete_department'),
    path('departments/reports/', views_admin.admin_report_page, name='admin_report_page'),
    path('student/download-card/', views_users.download_attendance_card, name='download_attendance_card'),


    path('departments/add/', views_admin.add_department, name='add_department'),
    path('analytics/', views_admin.analytics_dashboard, name='analytics_dashboard'),
    path('admin-ui/upload/timetable/pdf/', views_admin.export_timetable_pdf, name='export_timetable_pdf'),


    # 1. Admin Role & User Management Dashboard
    path('admin_ui/users/', views_admin.manage_users, name='manage_users'),
    path('library/reserve/apply/<int:book_id>/', views_users.apply_reserve_book, name='apply_reserve_book'),

    # 2. Lodgings & Hostel Overview (Viewable by everyone based on template permissions)
    path('lodgings/', views_users.view_lodgings, name='view_lodgings'),

    # 3. Lodging Allocation Execution Endpoint (Strictly processed by Wardens)
    path('lodgings/allocate/', views_users.allocate_or_reallocate, name='allocate_or_reallocate'),
    path('staff-payments/disburse/', views_users.disburse_payment_view, name='disburse_payment'),
    path('library/upload-books/', views_users.upload_books, name='upload_books'),

    
    # In attendance/urls.py inside urlpatterns:
    path('library/dashboard/', views_users.librarian_dashboard, name='librarian_dashboard'),
    path('library/manage/', views_users.manage_library, name='manage_library'),
    path('library/issue/', views_users.issue_book, name='issue_book'),
    path('library/return/<int:record_id>/', views_users.return_book, name='return_book'),
    path('library/books/add/', views_users.add_book, name='add_book'),

    path('library/reader/', views_users.library_reader_dashboard, name='library_reader_dashboard'),
    
    path('finance/', views_users.fees_dashboard, name='fees_dashboard'),
    path('staff_payments_dashboard/', views_users.staff_payments_dashboard, name='staff_payments_dashboard'),
    path('finance/record/', views_users.record_payment_attempt, name='record_payment_attempt'),
    path('finance/confirm/<int:transaction_id>/', views_users.confirm_student_payment, name='confirm_student_payment'),


    path('fees/confirm/<int:transaction_id>/', views_users.confirm_student_payment, name='confirm_student_payment'),
    
    # New Management CRUD routing gates
    path('fees/edit/<int:transaction_id>/', views_users.edit_fee_transaction, name='edit_fee_transaction'),
    path('fees/delete/<int:transaction_id>/', views_users.delete_fee_transaction, name='delete_fee_transaction'),
    path('staff-payments/edit/<int:payment_id>/', views_users.edit_staff_payment, name='edit_staff_payment'),
    path('staff-payments/delete/<int:payment_id>/', views_users.delete_staff_payment, name='delete_staff_payment'),
    path('accountant-dashboard/', views_users.accountant_dashboard, name='accountant_dashboard'),


    path('disciplinary/', views_users.disciplinary_dashboard, name='disciplinary_dashboard'),
    path('disciplinary/add/', views_users.add_complaint, name='add_complaint'),
    path('disciplinary/delete/<int:record_id>/', views_users.delete_complaint, name='delete_complaint'),
    path('complaint/<int:pk>/edit/', views_users.edit_complaint, name='edit_complaint'),    

    # In attendance/urls.py
    path('warden-dashboard/', views_users.warden_dashboard, name='warden_dashboard'),


    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html', # Custom email template
             success_url=reverse_lazy('attendance:password_reset_done')    # Namespaced success redirect
         ), 
         name='password_reset'),
         
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
         
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url=reverse_lazy('attendance:password_reset_complete') # Namespaced success redirect
         ), 
         name='password_reset_confirm'),
         
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),

   # Examination
    # Examination
    path('exams/', views_admin.manage_exams, name='manage_exams'),
    path('exams/edit/<int:exam_id>/', views_admin.edit_exam, name='edit_exam'),
    path('exams/marks/<int:exam_id>/save-single/', views_users.save_single_mark, name='save_single_mark'),
    path('exams/delete/<int:exam_id>/', views_admin.delete_exam, name='delete_exam'),
    path('exams/marks/<int:exam_id>/', views_users.manage_marks, name='manage_marks'),
    path('exams/marks/delete/<int:mark_id>/', views_users.delete_mark, name='delete_mark'),
    path('exams/grades/', views_admin.view_grades, name='view_grades'),
    path('exams/report-card/<str:student_id>/<int:term_id>/', views_users.generate_report_card, name='generate_report_card'),
    path('exams/transcript/<str:student_id>/<int:term_id>/', views_admin.generate_transcript, name='generate_transcript'),
    path('exams/ranking/', views_admin.exam_ranking, name='exam_ranking'),

    # Inventory
    path('inventory/', views_admin.manage_inventory, name='manage_inventory'),
    path('inventory/procurement/', views_admin.manage_procurement, name='manage_procurement'),
    path('inventory/assets/', views_admin.asset_tracking, name='asset_tracking'),
    path('inventory/stock-report/', views_admin.stock_report, name='stock_report'),

    # Transport
    path('transport/vehicles/', views_admin.manage_vehicles, name='manage_vehicles'),
    path('allocate/transport/', views_admin.allocate_transport, name='allocate_transport'),
    path('allocate/transport/edit/<int:pk>/', views_admin.edit_transport_allocation, name='edit_transport_allocation'),
    path('allocate/transport/delete/<int:pk>/', views_admin.delete_transport_allocation, name='delete_transport_allocation'),

    path('transport/trips/', views_admin.trip_log, name='trip_log'),
    path('transport/dashboard/', views_users.transport_dashboard, name='transport_dashboard'),

    # Human Resources
    path('hr/leave/apply/', views_users.apply_leave, name='apply_leave'),
    path('hr/leave/approve/<int:leave_id>/', views_admin.approve_leave, name='approve_leave'),
    path('hr/performance/', views_admin.manage_performance, name='manage_performance'),
    path('hr/qualifications/', views_admin.manage_qualifications, name='manage_qualifications'),
    path('hr/dashboard/', views_admin.hr_dashboard, name='hr_dashboard'),

    # Parent Portal
    path('parent/dashboard/', views_users.parent_dashboard, name='parent_dashboard'),
    path('admin_ui/link-parent/', views_admin.link_parent_student, name='link_parent_student'),

    # Online Learning
    path('online/courses/', views_users.manage_online_courses, name='manage_online_courses'),
    path('online/course/<int:course_id>/', views_users.view_course_materials, name='view_course_materials'),
    path('online/assignment/<int:assignment_id>/submit/', views_users.submit_assignment, name='submit_assignment'),
    path('online/assignment/grade/<int:submission_id>/', views_users.grade_assignment, name='grade_assignment'),
    path('online/exam/<int:exam_id>/take/', views_users.take_online_exam, name='take_online_exam'),
    path('online/exams/', views_users.manage_online_exams, name='manage_online_exams'),

    # Registrar
    path('registrar/dashboard/', views_users.registrar_dashboard, name='registrar_dashboard'),  # define if needed
    path('admin_ui/admissions/', views_admin.manage_admissions, name='manage_admissions'),
    path('admin_ui/transfers/', views_admin.manage_student_transfers, name='manage_student_transfers'),
    ]