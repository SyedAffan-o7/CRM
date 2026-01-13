from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Notification, NotificationPreference, NotificationType


@login_required
def notification_list(request):
    """List user's notifications"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('notification_type').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        notifications = notifications.filter(status=status_filter)
    
    # Filter by type
    type_filter = request.GET.get('type')
    if type_filter:
        notifications = notifications.filter(notification_type__category=type_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        notifications = notifications.filter(
            Q(title__icontains=search) | Q(message__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get counts for badges
    unread_count = Notification.objects.filter(
        recipient=request.user, 
        status__in=['PENDING', 'SENT']
    ).count()
    
    context = {
        'page_obj': page_obj,
        'unread_count': unread_count,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'search': search,
        'notification_categories': NotificationType.CATEGORY_CHOICES,
    }
    
    return render(request, 'notifications_app/notification_list.html', context)


@login_required
@require_http_methods(["POST"])
def mark_as_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id, 
            recipient=request.user
        )
        notification.mark_as_read()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, 'Notification marked as read.')
        return redirect('notifications_app:notification_list')
        
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error marking notification as read: {e}')
        return redirect('notifications_app:notification_list')


@login_required
@require_http_methods(["POST"])
def mark_all_as_read(request):
    """Mark all notifications as read for the current user"""
    try:
        count = Notification.objects.filter(
            recipient=request.user,
            status__in=['PENDING', 'SENT']
        ).update(
            status='READ',
            read_at=timezone.now()
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'count': count})
        
        messages.success(request, f'Marked {count} notifications as read.')
        return redirect('notifications_app:notification_list')
        
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error marking notifications as read: {e}')
        return redirect('notifications_app:notification_list')


@login_required
def notification_preferences(request):
    """Manage notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )
    
    if request.method == 'POST':
        try:
            # Update email preferences
            preferences.email_follow_ups = request.POST.get('email_follow_ups') == 'on'
            preferences.email_lead_changes = request.POST.get('email_lead_changes') == 'on'
            preferences.email_assignments = request.POST.get('email_assignments') == 'on'
            preferences.email_user_changes = request.POST.get('email_user_changes') == 'on'
            preferences.email_system_alerts = request.POST.get('email_system_alerts') == 'on'
            
            # Update in-app preferences
            preferences.app_follow_ups = request.POST.get('app_follow_ups') == 'on'
            preferences.app_lead_changes = request.POST.get('app_lead_changes') == 'on'
            preferences.app_assignments = request.POST.get('app_assignments') == 'on'
            preferences.app_user_changes = request.POST.get('app_user_changes') == 'on'
            preferences.app_system_alerts = request.POST.get('app_system_alerts') == 'on'
            
            # Update digest preferences
            preferences.daily_digest = request.POST.get('daily_digest') == 'on'
            preferences.weekly_digest = request.POST.get('weekly_digest') == 'on'
            
            preferences.save()
            
            messages.success(request, 'Notification preferences updated successfully.')
            return redirect('notifications_app:notification_preferences')
            
        except Exception as e:
            messages.error(request, f'Error updating preferences: {e}')
    
    context = {
        'preferences': preferences,
    }
    
    return render(request, 'notifications_app/notification_preferences.html', context)


@login_required
def get_unread_notifications(request):
    """Get unread notifications for AJAX requests"""
    notifications = Notification.objects.filter(
        recipient=request.user,
        status__in=['PENDING', 'SENT']
    ).select_related('notification_type').order_by('-created_at')[:10]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
            'priority': notification.notification_type.priority,
            'category': notification.notification_type.category,
        })
    
    return JsonResponse({
        'notifications': notifications_data,
        'count': len(notifications_data),
        'total_unread': Notification.objects.filter(
            recipient=request.user,
            status__in=['PENDING', 'SENT']
        ).count()
    })


@login_required
def notification_detail(request, notification_id):
    """View notification details"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )
    
    # Mark as read when viewed
    if notification.status != 'READ':
        notification.mark_as_read()
    
    context = {
        'notification': notification,
    }
    
    return render(request, 'notifications_app/notification_detail.html', context)


@login_required
@require_http_methods(["DELETE"])
@csrf_exempt
def delete_notification(request, notification_id):
    """Delete a notification"""
    try:
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=request.user
        )
        notification.delete()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, 'Notification deleted.')
        return redirect('notifications_app:notification_list')
        
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error deleting notification: {e}')
        return redirect('notifications_app:notification_list')


# Admin views (for superusers)
@login_required
def admin_notification_dashboard(request):
    """Admin dashboard for notifications"""
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('crm_app:dashboard')
    
    # Get statistics
    total_notifications = Notification.objects.count()
    pending_notifications = Notification.objects.filter(status='PENDING').count()
    failed_notifications = Notification.objects.filter(status='FAILED').count()
    
    # Recent notifications
    recent_notifications = Notification.objects.select_related(
        'notification_type', 'recipient'
    ).order_by('-created_at')[:20]
    
    # Notification types
    notification_types = NotificationType.objects.all()
    
    context = {
        'total_notifications': total_notifications,
        'pending_notifications': pending_notifications,
        'failed_notifications': failed_notifications,
        'recent_notifications': recent_notifications,
        'notification_types': notification_types,
    }
    
    return render(request, 'notifications_app/admin_dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def send_test_notification(request):
    """Send a test notification (admin only)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        notification = Notification.create_notification(
            notification_type_name='SYSTEM_ALERT',
            recipient=request.user,
            title='Test Notification',
            message='This is a test notification to verify the system is working correctly.',
            data={'test': True}
        )
        
        if notification:
            success = notification.send()
            return JsonResponse({
                'success': success,
                'message': 'Test notification sent successfully' if success else 'Failed to send test notification'
            })
        else:
            return JsonResponse({'success': False, 'error': 'Failed to create notification'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
