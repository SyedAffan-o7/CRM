#!/usr/bin/env python
"""
STEP-BY-STEP NOTIFICATION TESTING SCRIPT
Run this script to test each notification type one at a time
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User
from notifications_app.models import Notification, NotificationPreference, NotificationType
from leads_app.models import Lead, FollowUp
from django.utils import timezone

def print_header(title):
    """Print a nice header"""
    print(f"\n{'='*60}")
    print(f"🔔 {title}")
    print(f"{'='*60}")

def print_step(step_num, description):
    """Print a step description"""
    print(f"\n📋 Step {step_num}: {description}")
    input("Press Enter when ready...")

def test_followup_reminder():
    """Test FOLLOWUP_REMINDER notification"""
    print_header("TESTING: FOLLOWUP_REMINDER")

    print("📝 This notification reminds users about follow-ups due tomorrow")

    print_step(1, "Create a test follow-up for tomorrow")

    # Get or create test user
    user, created = User.objects.get_or_create(
        username='test_reminder',
        defaults={'email': 'reminder@test.com'}
    )
    if created:
        print(f"   ✅ Created test user: {user.username}")

    # Create test lead
    lead = Lead.objects.create(
        contact_name='Reminder Test Contact',
        phone_number='+1234567890',
        company_name='Test Company',
        assigned_sales_person=user,
        created_by=user
    )

    # Create follow-up for tomorrow
    followup = FollowUp.objects.create(
        lead=lead,
        scheduled_date=timezone.now() + timedelta(days=1),
        followup_type='call',
        notes='Test follow-up reminder for tomorrow',
        created_by=user,
        assigned_to=user
    )

    print(f"   ✅ Created follow-up for tomorrow: {followup.scheduled_date.strftime('%Y-%m-%d %H:%M')}")

    print_step(2, "Trigger the reminder notification")

    # Import and run the signal function
    from notifications_app.signals import send_followup_reminders
    send_followup_reminders()

    print("   ✅ Sent follow-up reminders")

    print_step(3, "Check the results")

    # Check if notification was created
    notifications = Notification.objects.filter(
        recipient=user,
        notification_type__name='FOLLOWUP_REMINDER'
    )

    if notifications.exists():
        notif = notifications.first()
        print(f"   ✅ Notification created: {notif.title}")
        print(f"   📧 Email would be sent to: {user.email}")
    else:
        print("   ❌ No notification created")

    print(f"\n🔗 Check: http://127.0.0.1:8000/notifications/")
    print("   Should see 'Follow-up Reminder' notification")

    return user, lead, followup

def test_followup_overdue():
    """Test FOLLOWUP_OVERDUE notification"""
    print_header("TESTING: FOLLOWUP_OVERDUE")

    print("🚨 This notification alerts users about overdue follow-ups")

    user, lead, followup = test_followup_reminder()

    print_step(1, "Create an overdue follow-up")

    # Create overdue follow-up
    overdue_followup = FollowUp.objects.create(
        lead=lead,
        scheduled_date=timezone.now() - timedelta(days=2),  # 2 days overdue
        followup_type='email',
        notes='Test overdue follow-up alert',
        created_by=user,
        assigned_to=user,
        status='pending'
    )

    print(f"   ✅ Created overdue follow-up: {overdue_followup.scheduled_date.strftime('%Y-%m-%d %H:%M')}")

    print_step(2, "Trigger the overdue notification")

    from notifications_app.signals import send_followup_reminders
    send_followup_reminders()

    print("   ✅ Sent follow-up reminders")

    print_step(3, "Check the results")

    # Check for overdue notification
    overdue_notifications = Notification.objects.filter(
        recipient=user,
        notification_type__name='FOLLOWUP_OVERDUE'
    )

    if overdue_notifications.exists():
        notif = overdue_notifications.first()
        print(f"   ✅ URGENT notification created: {notif.title}")
        print(f"   🚨 Priority: {notif.notification_type.priority}")
    else:
        print("   ❌ No overdue notification created")

    print(f"\n🔗 Check: http://127.0.0.1:8000/notifications/")
    print("   Should see URGENT 'Overdue Follow-up' notification in RED")

def test_new_lead():
    """Test NEW_LEAD notification"""
    print_header("TESTING: NEW_LEAD")

    print("🎯 This notification alerts about new enquiry creation")

    print_step(1, "Create a new lead manually")

    user = User.objects.first()
    if not user:
        user = User.objects.create_user('test_lead', 'lead@test.com', 'pass123')

    # Create new lead
    lead = Lead.objects.create(
        contact_name='New Lead Test',
        phone_number='+1987654321',
        company_name='New Company',
        assigned_sales_person=user,
        created_by=user,
        notes='Test new lead notification'
    )

    print(f"   ✅ Created new lead: {lead.contact_name}")

    print_step(2, "Check if notification was triggered automatically")

    # Check for new lead notification
    new_lead_notifications = Notification.objects.filter(
        recipient=user,
        notification_type__name='NEW_LEAD',
        content_type__model='lead',
        object_id=lead.id
    )

    if new_lead_notifications.exists():
        notif = new_lead_notifications.first()
        print(f"   ✅ Notification created: {notif.title}")
        print(f"   📧 Email would be sent to: {user.email}")
    else:
        print("   ❌ No new lead notification found")
        print("   💡 This might need manual trigger or signal setup")

    print_step(3, "Verify in web interface")

    print(f"\n🔗 Check: http://127.0.0.1:8000/notifications/")
    print("   Should see 'New Lead' notification")

def test_lead_stage_change():
    """Test LEAD_STAGE_CHANGE notification"""
    print_header("TESTING: LEAD_STAGE_CHANGE")

    print("📈 This notification alerts about lead stage changes")

    print_step(1, "Update a lead's stage")

    user = User.objects.first()
    lead = Lead.objects.filter(assigned_sales_person=user).first()

    if not lead:
        lead = Lead.objects.create(
            contact_name='Stage Test Contact',
            phone_number='+1111111111',
            assigned_sales_person=user,
            created_by=user
        )

    print(f"   📋 Current stage: {lead.get_enquiry_stage_display()}")

    # Update stage
    original_stage = lead.enquiry_stage
    lead.enquiry_stage = 'quotation_sent'
    lead.save()

    print(f"   ✅ Updated stage from '{original_stage}' to '{lead.enquiry_stage}'")

    print_step(2, "Check if notification was triggered")

    # Check for stage change notification
    stage_notifications = Notification.objects.filter(
        recipient=user,
        notification_type__name='LEAD_STAGE_CHANGE',
        content_type__model='lead',
        object_id=lead.id
    )

    if stage_notifications.exists():
        notif = stage_notifications.first()
        print(f"   ✅ Notification created: {notif.title}")
        print(f"   📊 Shows stage change from {original_stage} to {lead.enquiry_stage}")
    else:
        print("   ❌ No stage change notification found")

    print(f"\n🔗 Check: http://127.0.0.1:8000/notifications/")
    print("   Should see 'Lead Stage Updated' notification")

def test_daily_digest():
    """Test DAILY_DIGEST notification"""
    print_header("TESTING: DAILY_DIGEST")

    print("📊 This notification sends daily activity summaries")

    print_step(1, "Enable daily digest for user")

    user = User.objects.first()
    prefs, created = NotificationPreference.objects.get_or_create(user=user)
    prefs.daily_digest = True
    prefs.save()

    print("   ✅ Enabled daily digest preference")

    print_step(2, "Trigger daily digest")

    from notifications_app.signals import send_daily_digest
    send_daily_digest()

    print("   ✅ Sent daily digest")

    print_step(3, "Check if notification was created")

    # Check for daily digest notification
    digest_notifications = Notification.objects.filter(
        recipient=user,
        notification_type__name='DAILY_DIGEST'
    ).order_by('-created_at')

    if digest_notifications.exists():
        notif = digest_notifications.first()
        print(f"   ✅ Daily digest created: {notif.title}")
        print(f"   📧 Email would be sent to: {user.email}")
    else:
        print("   ❌ No daily digest notification found")

    print(f"\n🔗 Check: http://127.0.0.1:8000/notifications/")
    print("   Should see 'Daily CRM Summary' notification")

def run_all_tests():
    """Run all notification tests in sequence"""
    print("🚀 NOTIFICATION TESTING - Step by Step")
    print("="*60)
    print("This will test each notification type one at a time")
    print("Make sure your server is running: python manage.py runserver")

    tests = [
        ("Follow-up Reminder", test_followup_reminder),
        ("Follow-up Overdue", test_followup_overdue),
        ("New Lead", test_new_lead),
        ("Lead Stage Change", test_lead_stage_change),
        ("Daily Digest", test_daily_digest),
    ]

    for test_name, test_func in tests:
        try:
            print(f"\n🎯 Starting: {test_name}")
            input("Press Enter to continue...")
            test_func()
            print(f"\n✅ {test_name} test completed")
            input("Press Enter to continue to next test...")
        except KeyboardInterrupt:
            print(f"\n⏹️  Stopped at {test_name}")
            break
        except Exception as e:
            print(f"\n❌ Error in {test_name}: {e}")
            input("Press Enter to continue...")

    print(f"\n{'='*60}")
    print("🏁 TESTING SESSION COMPLETED!")
    print("="*60)

if __name__ == '__main__':
    run_all_tests()
