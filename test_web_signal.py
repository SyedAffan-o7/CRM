#!/usr/bin/env python
"""
TEST NOTIFICATION SIGNAL IN DJANGO SHELL
This simulates exactly what happens when creating a follow-up through the web interface
"""
import os
import sys
import django

# Setup Django exactly like the web server does
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

print("🔔 TESTING NOTIFICATION SIGNAL IN DJANGO ENVIRONMENT")
print("="*60)

try:
    from django.contrib.auth.models import User
    from notifications_app.models import Notification, NotificationType
    from leads_app.models import Lead, FollowUp
    from datetime import datetime, timedelta

    # Get the current user (simulate logged-in user)
    user = User.objects.filter(is_active=True).first()
    if not user:
        user = User.objects.create_user('web_test', 'web@test.com', 'pass123')
        print(f"✅ Created test user: {user.username}")

    print(f"👤 Testing as user: {user.username}")

    # Count notifications before
    before_count = Notification.objects.filter(recipient=user).count()
    print(f"📊 Notifications before: {before_count}")

    # Create a lead (exactly like the web form does)
    lead = Lead.objects.create(
        contact_name='Web Interface Test',
        phone_number='+1987654321',
        company_name='Web Test Company',
        assigned_sales_person=user,
        created_by=user
    )
    print(f"✅ Created lead: {lead.contact_name}")

    # Create follow-up for tomorrow (exactly like the web form does)
    tomorrow = datetime.now() + timedelta(days=1)
    followup = FollowUp.objects.create(
        lead=lead,
        scheduled_date=tomorrow,
        followup_type='call',
        notes='Testing follow-up creation through web interface',
        created_by=user,
        assigned_to=user
    )
    print(f"✅ Created follow-up for tomorrow: {tomorrow.strftime('%Y-%m-%d %H:%M')}")

    # Wait a moment for signals to process
    import time
    time.sleep(1)

    # Count notifications after
    after_count = Notification.objects.filter(recipient=user).count()
    print(f"📊 Notifications after: {after_count}")

    # Check for follow-up reminder specifically
    reminder_notifications = Notification.objects.filter(
        recipient=user,
        notification_type__name='FOLLOWUP_REMINDER',
        content_type__model='followup',
        object_id=followup.id
    )

    if reminder_notifications.exists():
        notif = reminder_notifications.first()
        print("✅ SUCCESS! Follow-up reminder notification created!")
        print(f"   📧 Title: {notif.title}")
        print(f"   📅 Created: {notif.created_at.strftime('%H:%M:%S')}")
        print(f"   🔄 Status: {notif.status}")
        print(f"   📝 Message: {notif.message[:100]}...")

        print("\n🚀 NOTIFICATION SIGNAL IS WORKING!")
        print("   The notification should appear in the web interface now!")
        print(f"   Check: http://127.0.0.1:8000/notifications/")

    else:
        print("❌ No follow-up reminder notification found")
        print("   Checking all recent notifications for this user:")

        # Show recent notifications for debugging
        recent_notifs = Notification.objects.filter(recipient=user).order_by('-created_at')[:5]
        for n in recent_notifs:
            print(f"     - {n.title} ({n.notification_type.name}) - {n.created_at.strftime('%H:%M:%S')}")

    # Cleanup
    followup.delete()
    lead.delete()
    print("🗑️  Cleaned up test data")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("If no notification appeared, check:")
print("1. Is the Django server running?")
print("2. Are you logged in as the correct user?")
print("3. Check browser console for JavaScript errors")
print("4. Try refreshing the page")
print("="*60)
