#!/usr/bin/env python
"""
DEBUG NOTIFICATION SYSTEM - Step by Step
Helps identify why notifications aren't appearing
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User
from notifications_app.models import Notification, NotificationType, NotificationPreference
from leads_app.models import Lead, FollowUp

def debug_step_1_server():
    """Check if Django server is running and accessible"""
    print("🔍 DEBUG STEP 1: Server Check")
    print("="*50)

    try:
        # Check if we can access Django models
        user_count = User.objects.count()
        lead_count = Lead.objects.count()
        followup_count = FollowUp.objects.count()

        print(f"✅ Database connection OK")
        print(f"   Users: {user_count}")
        print(f"   Leads: {lead_count}")
        print(f"   Follow-ups: {followup_count}")

        # Check notification types
        notif_types = NotificationType.objects.count()
        print(f"   Notification Types: {notif_types}")

        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def debug_step_2_notifications():
    """Check notification system setup"""
    print("\n🔍 DEBUG STEP 2: Notification System")
    print("="*50)

    # Check notification types exist
    try:
        followup_reminder = NotificationType.objects.filter(name='FOLLOWUP_REMINDER').first()
        if followup_reminder:
            print(f"✅ FOLLOWUP_REMINDER type exists: {followup_reminder.category}")
        else:
            print("❌ FOLLOWUP_REMINDER type missing!")
            return False

        # Check total notifications
        total_notifs = Notification.objects.count()
        print(f"   Total notifications in DB: {total_notifs}")

        # Check recent notifications
        recent = Notification.objects.all().order_by('-created_at')[:3]
        if recent:
            print("   Recent notifications:")
            for n in recent:
                print(f"     - {n.title} ({n.created_at.strftime('%H:%M:%S')})")
        else:
            print("   No notifications found in database")

        return True
    except Exception as e:
        print(f"❌ Notification system error: {e}")
        return False

def debug_step_3_create_test():
    """Create a test notification manually"""
    print("\n🔍 DEBUG STEP 3: Manual Test Creation")
    print("="*50)

    try:
        # Get or create test user
        user, created = User.objects.get_or_create(
            username='debug_user',
            defaults={'email': 'debug@test.com'}
        )
        print(f"✅ Using user: {user.username}")

        # Create test notification directly
        test_notification = Notification.create_notification(
            notification_type_name='FOLLOWUP_REMINDER',
            recipient=user,
            title='DEBUG: Test Notification',
            message='This is a manual test notification to verify the system works.',
            data={'debug': True, 'manual': True}
        )

        if test_notification:
            print(f"✅ Test notification created: ID {test_notification.id}")
            print(f"   Title: {test_notification.title}")
            print(f"   Status: {test_notification.status}")
            print(f"   Email Error: {test_notification.email_error or 'None'}")

            # Try to send it
            if test_notification.send():
                print("✅ Notification sent successfully")
            else:
                print("❌ Failed to send notification")

            return test_notification
        else:
            print("❌ Failed to create test notification")
            return None

    except Exception as e:
        print(f"❌ Manual test creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_step_4_web_interface():
    """Check web interface URLs"""
    print("\n🔍 DEBUG STEP 4: Web Interface Check")
    print("="*50)

    print("📋 Check these URLs in your browser:")
    print("   1. Main site: http://127.0.0.1:8000/")
    print("   2. Notifications: http://127.0.0.1:8000/notifications/")
    print("   3. Leads page: http://127.0.0.1:8000/leads/")
    print("   4. Preferences: http://127.0.0.1:8000/notifications/preferences/")

    print("\n🔍 Check these things:")
    print("   - Can you access all URLs?")
    print("   - Do you see the notification bell (🔔) in the top right?")
    print("   - When you click the bell, does it show 'Loading notifications...'?")

def debug_step_5_fix_common_issues():
    """Provide fixes for common issues"""
    print("\n🔧 DEBUG STEP 5: Common Fixes")
    print("="*50)

    print("If notifications still don't appear, try these fixes:")

    print("\n1. 🚀 Restart the Django server:")
    print("   python manage.py runserver 127.0.0.1:8000")

    print("\n2. 🔄 Initialize notification types:")
    print("   python manage.py setup_notifications")

    print("\n3. 📧 Check email settings (for email notifications):")
    print("   - Open settings.py")
    print("   - Look for EMAIL_BACKEND setting")
    print("   - For testing, use: EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'")

    print("\n4. 🔐 Check user permissions:")
    print("   - Make sure you're logged in as a user who should receive notifications")
    print("   - Check if the user has an email address set")

    print("\n5. 🔔 Check notification bell JavaScript:")
    print("   - Open browser Developer Tools (F12)")
    print("   - Go to Console tab")
    print("   - Click the notification bell")
    print("   - Look for any JavaScript errors")

def run_debug():
    """Run all debug steps"""
    print("🔍 NOTIFICATION DEBUG SESSION")
    print("="*60)
    print("Let's identify why notifications aren't appearing...")

    # Step 1: Server check
    if not debug_step_1_server():
        print("\n❌ Fix database connection first!")
        return

    # Step 2: Notification system
    if not debug_step_2_notifications():
        print("\n❌ Fix notification system setup first!")
        return

    # Step 3: Manual test
    test_notif = debug_step_3_create_test()

    # Step 4: Web interface
    debug_step_4_web_interface()

    # Step 5: Common fixes
    debug_step_5_fix_common_issues()

    print("\n" + "="*60)
    print("🔍 DEBUG SESSION COMPLETE")
    print("="*60)

    if test_notif:
        print("✅ Manual test notification was created successfully!")
        print("   Check: http://127.0.0.1:8000/notifications/")
        print("   You should see 'DEBUG: Test Notification' in the list")
    else:
        print("❌ Manual test failed - check error messages above")

    print("\n🚀 Next steps:")
    print("1. Check the URLs mentioned in Step 4")
    print("2. Look for the manual test notification")
    print("3. If you see the manual notification, the system works!")
    print("4. If not, check browser console for JavaScript errors")

if __name__ == '__main__':
    run_debug()
