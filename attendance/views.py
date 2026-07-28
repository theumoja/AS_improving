from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from attendance.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm

def custom_login_view(request):
    # If user is already authenticated, send them to their dashboard right away
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect_user_by_role(user)
    else:
        form = AuthenticationForm()
        
    return render(request, 'attendance/login.html', {'form': form})

def redirect_user_by_role(user):
    return redirect('attendance:home')

@login_required
def change_password_view(request):
    """Allows both authenticated teachers and students to safely change their passwords."""
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Crucial: Keeps the session valid so the user isn't forced to re-login
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect_user_by_role(user)
    else:
        form = PasswordChangeForm(user=request.user)
        
    return render(request, 'attendance/change_password.html', {'form': form})