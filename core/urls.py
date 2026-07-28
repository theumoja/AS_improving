from django.contrib import admin
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from attendance import views_admin, views_users, views_analytics

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('attendance.urls')),
    
]

# LINK CUSTOM ERROR HANDLERS TO CORE VIEWS
handler404 = 'attendance.views_users.custom_page_not_found'
handler403 = 'attendance.views_users.custom_permission_denied'
handler500 = 'attendance.views_users.custom_server_error'
handler400 = 'attendance.views_users.custom_bad_request'