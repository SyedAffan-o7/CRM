#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User
from notifications_app.models import Notification, NotificationPreference
from leads_app.models import Lead, FollowUp
from datetime import datetime, timedelta
from django.utils import timezone

def create_test_notifications():
    """Create test notifications for demonstration"""
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        print(f"Created test user: {user.username}")
    
    # Ensure user has notification preferences
    prefs, created = NotificationPreference.objects.get_or_create(user=user)
    if created:
        print(f"Created notification preferences for {user.username}")
    
    # Create test notifications
    notifications_data = [
        {
            'type': 'FOLLOWUP_REMINDER',
            'title': 'Follow-up Reminder: John Doe',
            'message': 'You have a follow-up scheduled for tomorrow with John Doe from ABC Company.',
            'priority': 'HIGH'
        },
        {
            'type': 'NEW_LEAD',
            'title': 'New Lead: Jane Smith',
            'message': 'A new enquiry has been received from Jane Smith at XYZ Corp.',
            'priority': 'MEDIUM'
        },
        {
            'type': 'FOLLOWUP_OVERDUE',
            'title': 'Overdue Follow-up: Mike Johnson',
            'message': 'Your follow-up with Mike Johnson is 2 days overdue. Please update the status.',
            'priority': 'URGENT'
        },
        {
            'type': 'LEAD_STAGE_CHANGE',
            'title': 'Lead Stage Updated: Sarah Wilson',
            'message': 'Lead for Sarah Wilson has moved to "Quotation Sent" stage.',
            'priority': 'MEDIUM'
        },
        {
            'type': 'DAILY_DIGEST',
            'title': f'Daily CRM Summary - {timezone.now().strftime("%B %d, %Y")}',
            'message': 'Here\'s your daily summary: 3 new enquiries, 2 follow-ups due today, 1 overdue follow-up.',
            'priority': 'LOW'
        }
    ]
    
    created_count = 0
    for notif_data in notifications_data:
        notification = Notification.create_notification(
            notification_type_name=notif_data['type'],
            recipient=user,
            title=notif_data['title'],
            message=notif_data['message'],
            data={'test': True, 'priority': notif_data['priority']}
        )
        
        if notification:
            created_count += 1
            print(f"Created notification: {notification.title}")
        else:
            print(f"Failed to create notification: {notif_data['title']}")
    
    print(f"\nCreated {created_count} test notifications for user: {user.username}")
    
    # Show notification counts
    total_notifications = Notification.objects.filter(recipient=user).count()
    unread_notifications = Notification.objects.filter(
        recipient=user, 
        status__in=['PENDING', 'SENT']
    ).count()
    
    print(f"Total notifications: {total_notifications}")
    print(f"Unread notifications: {unread_notifications}")
    
    return user, created_count

def test_notification_sending():
    """Test sending notifications"""
    print("\n" + "="*50)
    print("TESTING NOTIFICATION SENDING")
    print("="*50)
    
    user, count = create_test_notifications()
    
    if count > 0:
        # Get a test notification and try to send it
        test_notification = Notification.objects.filter(
            recipient=user,
            status='PENDING'
        ).first()
        
        if test_notification:
            print(f"\nTesting email send for: {test_notification.title}")
            success = test_notification.send()
            print(f"Email send result: {'Success' if success else 'Failed'}")
            
            if test_notification.email_error:
                print(f"Email error: {test_notification.email_error}")
    
    return user

def test_follow_up_reminders():
    """Test follow-up reminder system"""
    print("\n" + "="*50)
    print("TESTING FOLLOW-UP REMINDERS")
    print("="*50)
    
    from notifications_app.signals import send_followup_reminders
    
    # This would normally be called by a cron job
    print("Running follow-up reminder check...")
    send_followup_reminders()
    print("Follow-up reminder check completed")

if __name__ == '__main__':
    print("AAA CRM Notification System Test")
    print("="*50)
    
    try:
        # Test basic notification creation
        user = test_notification_sending()
        
        # Test follow-up reminders
        test_follow_up_reminders()
        
        print("\n" + "="*50)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("="*50)
        print(f"\nTo view notifications in the web interface:")
        print(f"1. Login as user: {user.username}")
        print(f"2. Visit: http://localhost:8000/notifications/")
        print(f"3. Check the notification bell in the top navigation")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
