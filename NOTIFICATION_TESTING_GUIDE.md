# 🔔 NOTIFICATION TESTING GUIDE - Step by Step

## 📋 Complete Testing Plan for Each Notification Type

This guide will help you test **EVERY** notification type systematically. Each test includes:
- **How to trigger** the notification
- **Expected behavior** 
- **How to verify** it worked
- **Troubleshooting** if needed

---

## 🚨 **FOLLOW-UP NOTIFICATIONS**

### 1. **FOLLOWUP_REMINDER** - Tomorrow's Follow-up
**Purpose**: Remind users about follow-ups due tomorrow

**🧪 TEST STEPS:**
1. **Create a follow-up for tomorrow:**
   ```bash
   # Access Django shell
   python manage.py shell
   ```

   ```python
   from leads_app.models import Lead, FollowUp
   from django.contrib.auth.models import User
   from datetime import datetime, timedelta

   # Get a user (or create test user)
   user = User.objects.first()

   # Create a test lead
   lead = Lead.objects.create(
       contact_name='Test Contact',
       phone_number='+1234567890',
       company_name='Test Company',
       assigned_sales_person=user,
       created_by=user
   )

   # Create follow-up for tomorrow
   followup = FollowUp.objects.create(
       lead=lead,
       scheduled_date=datetime.now() + timedelta(days=1),
       followup_type='call',
       notes='Test follow-up reminder',
       created_by=user,
       assigned_to=user
   )
   ```

2. **Trigger the notification:**
   ```bash
   python manage.py send_notifications --type=reminders
   ```

3. **Verify:**
   - Check notification bell shows new notification
   - Check `/notifications/` - should see "Follow-up Reminder"
   - Check email (if user has email configured)

### 2. **FOLLOWUP_OVERDUE** - Overdue Follow-up Alert
**Purpose**: Alert users about overdue follow-ups

**🧪 TEST STEPS:**
1. **Create an overdue follow-up:**
   ```python
   # In Django shell
   overdue_followup = FollowUp.objects.create(
       lead=lead,
       scheduled_date=datetime.now() - timedelta(days=2),  # 2 days ago
       followup_type='email',
       notes='Test overdue follow-up',
       created_by=user,
       assigned_to=user,
       status='pending'
   )
   ```

2. **Trigger the notification:**
   ```bash
   python manage.py send_notifications --type=reminders
   ```

3. **Verify:**
   - Should get URGENT notification with red styling
   - Email should be sent (if enabled)

### 3. **FOLLOWUP_ASSIGNED** - Follow-up Assignment
**Purpose**: Notify when follow-up is assigned

**🧪 TEST STEPS:**
1. **Create and assign follow-up:**
   ```python
   # Create follow-up assigned to different user
   user2 = User.objects.create_user('testuser2', 'test2@test.com', 'pass123')

   assigned_followup = FollowUp.objects.create(
       lead=lead,
       scheduled_date=datetime.now() + timedelta(days=1),
       followup_type='meeting',
       notes='Test assignment notification',
       created_by=user,
       assigned_to=user2  # Different user
   )
   ```

2. **Trigger the notification:**
   ```bash
   python manage.py send_notifications --type=reminders
   ```

3. **Verify:**
   - User2 should get notification about new assignment
   - Original user might also get notification

### 4. **FOLLOWUP_COMPLETED** - Follow-up Completion
**Purpose**: Notify when follow-up is marked complete

**🧪 TEST STEPS:**
1. **Complete a follow-up:**
   ```python
   # Complete the follow-up
   followup.mark_completed()
   ```

2. **Check if notification triggers automatically**

3. **Verify:**
   - Should get notification about completion
   - Status should show as completed

---

## 🎯 **LEAD MANAGEMENT NOTIFICATIONS**

### 5. **NEW_LEAD** - New Lead Creation
**Purpose**: Alert about new enquiry creation

**🧪 TEST STEPS:**
1. **Create a new lead:**
   - Go to `/` (main dashboard)
   - Click "New Enquiry" or use the form
   - Fill in contact details
   - Submit the form

2. **Verify:**
   - Assigned salesperson should get notification
   - Check notification bell immediately
   - Check `/notifications/` list

### 6. **LEAD_STAGE_CHANGE** - Lead Stage Updates
**Purpose**: Notify about enquiry stage changes

**🧪 TEST STEPS:**
1. **Update lead stage:**
   - Go to an existing lead (or create one)
   - Change the "Enquiry Stage" field
   - Save the changes

2. **Verify:**
   - Should get notification about stage change
   - Check notification details for old/new stage info

### 7. **LEAD_ASSIGNMENT** - Lead Assignment Changes
**Purpose**: Notify when lead ownership changes

**🧪 TEST STEPS:**
1. **Change lead assignment:**
   - Edit an existing lead
   - Change "Assigned Sales Person"
   - Save changes

2. **Verify:**
   - Both old and new assignee should get notifications
   - Notification should show assignment change

### 8. **LEAD_STATUS_CHANGE** - Lead Status Updates
**Purpose**: Notify about lead status changes (fulfilled/not fulfilled)

**🧪 TEST STEPS:**
1. **Change lead status:**
   - Edit a lead that reached "won" stage
   - Update status to "fulfilled"
   - Save changes

2. **Verify:**
   - Should get notification about status change

---

## 👥 **USER MANAGEMENT NOTIFICATIONS**

### 9. **USER_WELCOME** - New User Welcome
**Purpose**: Welcome new users to the system

**🧪 TEST STEPS:**
1. **Create a new user:**
   - Go to `/settings/users/create/`
   - Create a new user account
   - Submit the form

2. **Verify:**
   - New user should get welcome notification
   - Check their notification list

### 10. **USER_ROLE_CHANGE** - Role Changes
**Purpose**: Notify about user role/permission changes

**🧪 TEST STEPS:**
1. **Change user role:**
   - Edit an existing user
   - Change their role
   - Save changes

2. **Verify:**
   - User should get notification about role change

### 11. **USER_ACCOUNT_ACTIVATED** - Account Activation
**Purpose**: Notify when account is activated

**🧪 TEST STEPS:**
1. **Activate user account:**
   - Edit a user with inactive status
   - Set "Is Active" to True
   - Save changes

2. **Verify:**
   - User should get activation notification

### 12. **USER_ACCOUNT_DEACTIVATED** - Account Deactivation
**Purpose**: Notify when account is deactivated

**🧪 TEST STEPS:**
1. **Deactivate user account:**
   - Edit an active user
   - Set "Is Active" to False
   - Save changes

2. **Verify:**
   - User should get deactivation notification

---

## 📊 **SYSTEM & WORKFLOW NOTIFICATIONS**

### 13. **DAILY_DIGEST** - Daily Summary
**Purpose**: Send daily activity summary

**🧪 TEST STEPS:**
1. **Enable daily digest:**
   - Go to `/notifications/preferences/`
   - Check "Daily Summary Email"
   - Save preferences

2. **Trigger daily digest:**
   ```bash
   python manage.py send_notifications --type=digest
   ```

3. **Verify:**
   - Should receive daily digest email
   - Should show activity summary

### 14. **WEEKLY_DIGEST** - Weekly Summary
**Purpose**: Send weekly performance insights

**🧪 TEST STEPS:**
1. **Enable weekly digest:**
   - Go to `/notifications/preferences/`
   - Check "Weekly Summary Email"
   - Save preferences

2. **Trigger weekly digest:**
   ```bash
   python manage.py send_notifications --type=digest
   ```

3. **Verify:**
   - Should receive weekly digest email
   - Should show performance insights

### 15. **SYSTEM_ALERT** - System Notifications
**Purpose**: Important system alerts and errors

**🧪 TEST STEPS:**
1. **Trigger system alert:**
   ```python
   # In Django shell
   from notifications_app.models import Notification

   user = User.objects.first()
   alert = Notification.create_notification(
       notification_type_name='SYSTEM_ALERT',
       recipient=user,
       title='Test System Alert',
       message='This is a test system alert notification.',
       data={'test': True}
   )
   ```

2. **Send the notification:**
   ```python
   alert.send()
   ```

3. **Verify:**
   - Should get system alert notification
   - Should appear in notification list

### 16. **ENQUIRY_ACCEPTED** - Enquiry Acceptance
**Purpose**: Notify when enquiry is accepted

**🧪 TEST STEPS:**
1. **Accept a pending enquiry:**
   - Find a lead with "is_pending_review = True"
   - Set it to False (accept it)

2. **Verify:**
   - Should get acceptance notification

### 17. **ENQUIRY_REJECTED** - Enquiry Rejection
**Purpose**: Notify when enquiry is rejected

**🧪 TEST STEPS:**
1. **Reject a pending enquiry:**
   - Find a lead with "is_pending_review = True"
   - Delete it or mark as rejected

2. **Verify:**
   - Should get rejection notification

### 18. **CONTACT_AUTO_CREATED** - Contact Auto-Creation
**Purpose**: Notify when contact is auto-created

**🧪 TEST STEPS:**
1. **Trigger auto-contact creation:**
   - Create a lead without an existing contact
   - System should auto-create contact

2. **Verify:**
   - Should get auto-creation notification

---

## 🔧 **TESTING COMMANDS**

### **Quick Test All Notifications:**
```bash
# Test notification creation
python test_notifications.py

# Verify system functionality
python verify_notifications.py

# Check all notification types exist
python manage.py shell
>>> from notifications_app.models import NotificationType
>>> for nt in NotificationType.objects.all():
...     print(f"{nt.name}: {nt.category}")
```

### **Send Specific Notification Types:**
```bash
# Send only follow-up reminders
python manage.py send_notifications --type=reminders

# Send only digests
python manage.py send_notifications --type=digest

# Send only pending notifications
python manage.py send_notifications --type=pending

# Dry run (test without sending)
python manage.py send_notifications --dry-run
```

---

## 📋 **TESTING CHECKLIST**

**Mark each as you test:**

### Follow-up Notifications
- [ ] FOLLOWUP_REMINDER - Tomorrow reminder
- [ ] FOLLOWUP_OVERDUE - Overdue alert
- [ ] FOLLOWUP_ASSIGNED - Assignment notification
- [ ] FOLLOWUP_COMPLETED - Completion notification

### Lead Management Notifications
- [ ] NEW_LEAD - New enquiry alert
- [ ] LEAD_STAGE_CHANGE - Stage update
- [ ] LEAD_ASSIGNMENT - Assignment change
- [ ] LEAD_STATUS_CHANGE - Status update

### User Management Notifications
- [ ] USER_WELCOME - New user welcome
- [ ] USER_ROLE_CHANGE - Role change
- [ ] USER_ACCOUNT_ACTIVATED - Account activation
- [ ] USER_ACCOUNT_DEACTIVATED - Account deactivation

### System Notifications
- [ ] DAILY_DIGEST - Daily summary
- [ ] WEEKLY_DIGEST - Weekly summary
- [ ] SYSTEM_ALERT - System alert
- [ ] ENQUIRY_ACCEPTED - Enquiry accepted
- [ ] ENQUIRY_REJECTED - Enquiry rejected
- [ ] CONTACT_AUTO_CREATED - Contact auto-created

---

## 🎯 **WHAT TO DO RIGHT NOW**

1. **Start with Follow-up Reminders** (most important):
   ```bash
   python manage.py shell
   # Create test follow-up for tomorrow
   # Run: python manage.py send_notifications --type=reminders
   # Check notification bell
   ```

2. **Test Lead Creation** (next most important):
   - Go to main page `/`
   - Create a new enquiry
   - Check if notification appears

3. **Test Stage Changes**:
   - Edit an existing lead
   - Change the stage
   - Verify notification

4. **Continue with each type** using the steps above

**Each test should result in:**
- ✅ Notification appears in bell dropdown
- ✅ Notification shows in `/notifications/` list
- ✅ Email sent (if preferences enabled)
- ✅ Correct styling (URGENT = red, HIGH = yellow, etc.)

Need help with any specific notification type? Let me know which one to focus on next!
