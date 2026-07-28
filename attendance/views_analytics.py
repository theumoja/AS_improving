from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required

from attendance.models import User, AttendanceRecord, CourseUnit, TeacherProfile

@login_required
def global_analytics_data(request):
    if request.user.role not in [User.IS_ADMIN, User.IS_TEACHER]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    # 1. Group directly by the session's DateField (No TruncDate needed)
    history = AttendanceRecord.objects.filter(status='PRESENT')\
        .values('session__date_marked')\
        .annotate(count=Count('id'))\
        .order_by('session__date_marked')

    # Safe extraction parsing to prevent crashes from any anomalies
    historical_labels = []
    historical_counts = []
    for item in history:
        date_val = item['session__date_marked']
        if date_val:
            if hasattr(date_val, 'strftime'):
                historical_labels.append(date_val.strftime('%Y-%m-%d'))
            else:
                historical_labels.append(str(date_val))
            historical_counts.append(item['count'])

    # Matrix 1: Total Attendance Distribution (Pie Chart)
    total_present = AttendanceRecord.objects.filter(status='PRESENT').count()
    total_absent = AttendanceRecord.objects.filter(status='ABSENT').count()

    # Matrix 2: Performance metrics across distinct Course Units (Bar Chart)
    units = CourseUnit.objects.annotate(
        present_count=Count('timetableentry__attendancesession__records',
                            filter=Q(timetableentry__attendancesession__records__status='PRESENT')),
        total_count=Count('timetableentry__attendancesession__records')
    )

    unit_labels = [u.name for u in units]
    unit_rates = [
        round((u.present_count / u.total_count) * 100, 2) if u.total_count > 0 else 0
        for u in units
    ]

    # Combine all structural data matrices safely into the returning JSON stream
    payload = {
        'pie': {'present': total_present, 'absent': total_absent},
        'bar': {'labels': unit_labels, 'rates': unit_rates},
        'line': {'labels': historical_labels, 'counts': historical_counts}
    }
    return JsonResponse(payload)