from functools import wraps
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from accounts_app.models import UserProfile

def require_permission(module, permission_type='view'):
    """
    Decorator to check if user has permission for a specific module and action
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            try:
                profile = request.user.profile
                if profile.has_permission(module, permission_type):
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, f"You don't have permission to {permission_type} {module}.")
                    return redirect('crm_app:dashboard')
            except UserProfile.DoesNotExist:
                messages.error(request, "User profile not found. Please contact administrator.")
                return redirect('crm_app:dashboard')
            except Exception as e:
                messages.error(request, f"Permission check failed: {str(e)}")
                return redirect('crm_app:dashboard')
        return wrapper
    return decorator

def require_superuser(view_func):
    """
    Decorator to check if user is a superuser (either Django is_superuser or role SUPERUSER)
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            profile = getattr(request.user, 'profile', None)
            role = getattr(profile, 'role', None)
            role_name = getattr(role, 'name', None)
            if role_name == 'SUPERUSER':
                return view_func(request, *args, **kwargs)
        except Exception:
            pass
        messages.error(request, "Only superusers can access this page.")
        return redirect('crm_app:dashboard')
    return wrapper

def require_role(role_name):
    """
    Decorator to check if user has a specific role
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            try:
                profile = request.user.profile
                if profile.role and profile.role.name == role_name:
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, f"This page requires {role_name} role.")
                    return redirect('crm_app:dashboard')
            except UserProfile.DoesNotExist:
                messages.error(request, "User profile not found. Please contact administrator.")
                return redirect('crm_app:dashboard')
        return wrapper
    return decorator

def get_user_modules(user):
    """
    Get list of modules accessible to a user
    """
    try:
        return user.profile.accessible_modules
    except UserProfile.DoesNotExist:
        return []

def has_module_access(user, module):
    """
    Check if user has access to a specific module
    """
    accessible_modules = get_user_modules(user)
    return module in accessible_modules

def get_user_permissions(user, module):
    """
    Get detailed permissions for a user on a specific module
    """
    try:
        profile = user.profile
        if profile.has_permission(module, 'view'):
            permission = profile.role.permissions.get(module=module)
            return {
                'can_view': permission.can_view,
                'can_create': permission.can_create,
                'can_edit': permission.can_edit,
                'can_delete': permission.can_delete,
                'can_import': permission.can_import,
                'can_export': permission.can_export,
            }
        return None
    except (UserProfile.DoesNotExist, UserPermissions.DoesNotExist):
        return None
