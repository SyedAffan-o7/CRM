#!/usr/bin/env python
"""
TEST FOLLOW-UP NOTIFICATION SIGNAL
Creates a follow-up and checks if notification appears immediately
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User
from notifications_app.models import Notification, NotificationType
from leads_app.models import Lead, FollowUp
from datetime import datetime, timedelta

def test_followup_signal():
    """Test that follow-up creation triggers notification signal"""
    print("🔔 TESTING FOLLOW-UP NOTIFICATION SIGNAL")
    print("="*60)

    # Get or create test user
    user, created = User.objects.get_or_create(
        username='signal_test',
        defaults={'email': 'signal@test.com'}
    )
    print(f"✅ Using user: {user.username}")

    # Count notifications before
    before_count = Notification.objects.filter(recipient=user).count()
    print(f"📊 Notifications before: {before_count}")

    # Create test lead
    lead = Lead.objects.create(
        contact_name='Signal Test Contact',
        phone_number='+1234567890',
        company_name='Signal Test Company',
        assigned_sales_person=user,
        created_by=user
    )
    print(f"✅ Created lead: {lead.contact_name}")

    # Create follow-up for tomorrow
    tomorrow = datetime.now() + timedelta(days=1)
    followup = FollowUp.objects.create(
        lead=lead,
        scheduled_date=tomorrow,
        followup_type='call',
        notes='Testing signal notification',
        created_by=user,
        assigned_to=user
    )

    print(f"✅ Created follow-up for: {tomorrow.strftime('%Y-%m-%d %H:%M')}")

    # Check notifications after
    after_count = Notification.objects.filter(recipient=user).count()
    print(f"📊 Notifications after: {after_count}")

    # Check for our specific notification
    reminder_notifications = Notification.objects.filter(
        recipient=user,
        notification_type__name='FOLLOWUP_REMINDER',
        content_type__model='followup',
        object_id=followup.id
    )

    if reminder_notifications.exists():
        notif = reminder_notifications.first()
        print("✅ SUCCESS! Follow-up notification created:")
        print(f"   📧 Title: {notif.title}")
        print(f"   📅 Created: {notif.created_at.strftime('%H:%M:%S')}")
        print(f"   🔄 Status: {notif.status}")

        print("\n🚀 NOTIFICATION SIGNAL IS WORKING!")
        print("   Go to: http://127.0.0.1:8000/notifications/")
        print("   You should see the notification in the list")

    else:
        print("❌ No follow-up reminder notification found")
        print("   Checking all notifications for this user:")

        # Show all notifications for debugging
        all_user_notifs = Notification.objects.filter(recipient=user).order_by('-created_at')[:5]
        if all_user_notifs:
            for n in all_user_notifs:
                print(f"     - {n.title} ({n.notification_type.name})")
        else:
            print("     - No notifications found for this user")

    # Cleanup
    followup.delete()
    lead.delete()
    print("🗑️  Cleaned up test data")

if __name__ == '__main__':
    test_followup_signal()
