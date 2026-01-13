from leads_app.models import FollowUp
from accounts_app.models import UserProfile
from django.utils import timezone
from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError

def followup_notifications(request):
    if request.user.is_authenticated:
        try:
            if request.user.is_superuser:
                followups = FollowUp.objects.filter(status='pending')
            else:
                followups = FollowUp.objects.filter(
                    Q(assigned_to=request.user) | Q(created_by=request.user),
                    status='pending'
                ).distinct()

            overdue = sum(1 for f in followups if f.is_overdue)
            today = sum(1 for f in followups if f.is_due_today)

            return {
                'overdue_followups_count': overdue,
                'today_followups_count': today
            }
        except (OperationalError, ProgrammingError):
            # Database schema might be out of sync during migrations; fail gracefully
            return {
                'overdue_followups_count': 0,
                'today_followups_count': 0
            }
    return {}

def user_role_context(request):
    """Add user role information to template context"""
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            return {
                'user_role': profile.role.name if profile.role else None,
                'user_role_display': profile.role.display_name if profile.role else None,
                'user_role_level': profile.role.role_level if profile.role else 0,
            }
        except (UserProfile.DoesNotExist, AttributeError, OperationalError, ProgrammingError):
            return {
                'user_role': None,
                'user_role_display': None,
                'user_role_level': 0,
            }
    return {
        'user_role': None,
        'user_role_display': None,
        'user_role_level': 0,
    }
