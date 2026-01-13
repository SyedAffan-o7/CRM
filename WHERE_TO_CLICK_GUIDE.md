# 🎯 WHERE TO ADD DATA - Practical Testing Guide

## 📍 **EXACT LOCATIONS** to trigger each notification

This guide shows you **exactly where to click and what to enter** in the CRM interface to see each notification type in action.

---

## 🚨 **FOLLOW-UP NOTIFICATIONS**

### **1. FOLLOWUP_REMINDER** - Tomorrow's Follow-up
**📍 WHERE:** `/leads/` (Enquiries page)

**🖱️ STEPS:**
1. Go to: `http://127.0.0.1:8000/leads/`
2. Find any existing lead OR click "New Enquiry"
3. Fill in:
   - Contact Name: "Test Reminder"
   - Phone: "+1234567890"
   - Company: "Test Company"
4. **Click "Add Follow-up"** button
5. Set follow-up for **TOMORROW**
6. Select type: "Call"
7. Add notes: "Test reminder"
8. **Save**

**👀 WHAT TO SEE:**
- Notification bell should show badge
- Dropdown shows "Follow-up Reminder"
- `/notifications/` shows the notification

---

### **2. FOLLOWUP_OVERDUE** - Overdue Alert
**📍 WHERE:** Same as above, but set date in the PAST

**🖱️ STEPS:**
1. Go to: `http://127.0.0.1:8000/leads/`
2. Create/edit a lead
3. **Click "Add Follow-up"**
4. Set follow-up for **YESTERDAY** (past date)
5. Select type: "Email"
6. Add notes: "Test overdue"
7. **Save**

**👀 WHAT TO SEE:**
- URGENT notification (red styling)
- "Overdue Follow-up" in bell dropdown
- RED notification in list

---

## 🎯 **LEAD MANAGEMENT NOTIFICATIONS**

### **3. NEW_LEAD** - New Enquiry Alert
**📍 WHERE:** Main Dashboard `/`

**🖱️ STEPS:**
1. Go to: `http://127.0.0.1:8000/`
2. **Click "New Enquiry"** button (top right)
3. Fill the form:
   - Contact Name: "New Lead Test"
   - Phone Number: "+1987654321"
   - Company: "New Test Company"
   - **Leave other fields default**
4. **Click "Save"**

**👀 WHAT TO SEE:**
- **IMMEDIATE** notification in bell
- "New Lead Received" notification
- Assigned user gets email notification

### **4. LEAD_STAGE_CHANGE** - Stage Updates
**📍 WHERE:** `/leads/` (click on any lead)

**🖱️ STEPS:**
1. Go to: `http://127.0.0.1:8000/leads/`
2. **Click on any lead** in the list
3. In the lead detail page:
   - Find "Enquiry Stage" dropdown
   - **Change it** from current stage to another
   - **Click "Save"**

**👀 WHAT TO SEE:**
- Notification about stage change
- Shows old and new stage in notification
- "Lead Stage Updated" in bell

### **5. LEAD_ASSIGNMENT** - Assignment Changes
**📍 WHERE:** Lead detail page

**🖱️ STEPS:**
1. Go to any lead detail page
2. Find "Assigned Sales Person" field
3. **Change it to a different user**
4. **Click "Save"**

**👀 WHAT TO SEE:**
- Both old AND new assignee get notifications
- "Lead Assignment" notification appears

---

## 👥 **USER MANAGEMENT NOTIFICATIONS**

### **6. USER_WELCOME** - New User Welcome
**📍 WHERE:** `/settings/users/create/`

**🖱️ STEPS:**
1. Go to: `http://127.0.0.1:8000/settings/users/create/`
2. Fill in new user details:
   - Username: "newuser"
   - Email: "newuser@test.com"
   - Password: "password123"
   - **Select a role**
3. **Click "Create User"**

**👀 WHAT TO SEE:**
- New user gets "Welcome" notification
- Check their notification list

### **7. USER_ROLE_CHANGE** - Role Changes
**📍 WHERE:** `/settings/users/` (edit existing user)

**🖱️ STEPS:**
1. Go to: `http://127.0.0.1:8000/settings/users/`
2. **Click "Edit"** on any user
3. **Change their role** to different one
4. **Click "Save"**

**👀 WHAT TO SEE:**
- User gets "Role Change" notification

---

## 📊 **SYSTEM NOTIFICATIONS**

### **8. DAILY_DIGEST** - Daily Summary
**📍 WHERE:** User Preferences + Management Command

**🖱️ STEPS:**
1. **Enable in preferences:**
   - Go to: `http://127.0.0.1:8000/notifications/preferences/`
   - **Check "Daily Summary Email"**
   - **Click "Save Preferences"**

2. **Trigger the digest:**
   ```bash
   python manage.py send_notifications --type=digest
   ```

**👀 WHAT TO SEE:**
- "Daily CRM Summary" notification
- Summary of today's activities

---

## 🎯 **QUICK TEST SEQUENCE**

### **Test All Critical Notifications in 5 Minutes:**

1. **Test 1: New Lead (30 seconds)**
   ```
   http://127.0.0.1:8000/ → "New Enquiry" → Fill form → Save
   → Check bell immediately
   ```

2. **Test 2: Follow-up Reminder (30 seconds)**
   ```
   http://127.0.0.1:8000/leads/ → Any lead → "Add Follow-up"
   → Set for TOMORROW → Save → Check bell
   ```

3. **Test 3: Stage Change (20 seconds)**
   ```
   http://127.0.0.1:8000/leads/ → Click any lead → Change stage → Save
   → Check bell
   ```

4. **Test 4: Assignment Change (20 seconds)**
   ```
   Same lead → Change "Assigned Sales Person" → Save → Check bell
   ```

5. **Test 5: Overdue Follow-up (30 seconds)**
   ```
   Same lead → "Add Follow-up" → Set for YESTERDAY → Save → Check bell
   ```

### **WHAT TO WATCH FOR:**

✅ **Bell Badge**: Red number appears immediately
✅ **Dropdown Content**: Click bell, see notification preview
✅ **Notification List**: Visit `/notifications/` to see full list
✅ **Email Console**: Check terminal for email notifications

---

## 🔧 **TROUBLESHOOTING - If No Notifications Appear**

### **Check These Things:**

1. **Notification Bell Working?**
   - Visit any page, click the 🔔 bell
   - Should show "Loading notifications..." then content

2. **JavaScript Enabled?**
   - Check browser console for errors
   - Try refreshing the page

3. **User Has Email?**
   - Check if user has valid email address
   - Some notifications need email for delivery

4. **Permissions?**
   - Make sure you're logged in as the user who should get notifications
   - Check if user has notification preferences set

### **Debug Commands:**
```bash
# Check if notifications exist in database
python manage.py shell
>>> from notifications_app.models import Notification
>>> Notification.objects.all().count()
>>> Notification.objects.filter(recipient_id=1)  # Your user ID

# Force send notifications
python manage.py send_notifications --type=pending

# Check notification types
python manage.py shell
>>> from notifications_app.models import NotificationType
>>> for nt in NotificationType.objects.all():
...     print(f"{nt.name}: {nt.category}")
```

---

## 🎯 **START TESTING NOW**

**Begin with this sequence:**

1. **Open:** `http://127.0.0.1:8000/`
2. **Create New Enquiry** → Fill form → Save
3. **Watch notification bell** → Should show badge immediately
4. **Click bell** → See notification preview
5. **Go to:** `http://127.0.0.1:8000/notifications/` → See full list

**Each step should trigger a notification that you can see immediately!** 🚀

Let me know what happens when you try these steps, and I'll help troubleshoot if anything doesn't work as expected.
