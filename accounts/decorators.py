from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist

def get_user_role(user):
    if not user or not user.is_authenticated:
        return None
    try:
        if hasattr(user, 'profile'):
            return user.profile.role
        if hasattr(user, 'userprofile'):
            return user.userprofile.role
    except ObjectDoesNotExist:
        pass
    return None

def is_admin_user(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return get_user_role(user) == 'admin'

def is_tutor_user(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return get_user_role(user) == 'tutor'

def is_student_user(user):
    if not user or not user.is_authenticated:
        return False
    return get_user_role(user) == 'student'

def is_guardian_user(user):
    if not user or not user.is_authenticated:
        return False
    return get_user_role(user) == 'guardian'

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if user.is_staff or user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            role = get_user_role(user)
            if role in allowed_roles:
                return view_func(request, *args, **kwargs)
                
            messages.error(request, "You do not have permission to access this page.")
            if role == 'student':
                return redirect('student_dashboard')
            elif role == 'tutor':
                return redirect('tutor_dashboard')
            elif role == 'guardian':
                return redirect('guardian_dashboard')
            return redirect('homepage')
        return _wrapped_view
    return decorator
