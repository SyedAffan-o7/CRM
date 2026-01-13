from django.utils.deprecation import MiddlewareMixin

class RoleSuperuserMiddleware(MiddlewareMixin):
    """
    Promote users with role SUPERUSER to behave like Django superusers for the request lifecycle.
    This does NOT persist changes to the database; it only alters request-time behavior to
    make existing `user.is_superuser` checks pass for role-based superadmins.
    """
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return
        try:
            profile = getattr(user, 'profile', None)
            role = getattr(profile, 'role', None)
            role_name = getattr(role, 'name', None)
            if role_name == 'SUPERUSER':
                # Mark a flag for debugging/conditional use if needed
                setattr(user, 'role_is_superuser', True)
                # Shadow is_superuser so existing checks pass
                if not getattr(user, 'is_superuser', False):
                    setattr(user, 'is_superuser', True)
                # Optionally grant is_staff for admin UI visibility without persisting
                if not getattr(user, 'is_staff', False):
                    setattr(user, 'is_staff', True)
        except Exception:
            # Fail open: do nothing if profile is missing or any error occurs
            return
