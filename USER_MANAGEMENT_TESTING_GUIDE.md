# 🧪 User Management Testing Guide

## Overview
This guide provides step-by-step instructions for testing all new user management functionalities added to the Django CRM system.

---

## 🚀 Prerequisites

1. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

2. **Login as Superuser:**
   - Username: `Affan`
   - Password: `[your password]`
   - URL: http://127.0.0.1:8000/login/

3. **Navigate to User Management:**
   - Go to: http://127.0.0.1:8000/settings/users/
   - Or click: **Settings** → **User Management** → **Manage Users**

---

## ✅ Feature 1: View User Credentials/Details

### What It Does
Displays comprehensive information about a user including:
- Basic info (username, email, name)
- Profile details (role, employee ID, department)
- Activity statistics (leads created, activities logged)
- Last login information

### How to Test

1. **Navigate to User Management Dashboard:**
   - URL: http://127.0.0.1:8000/settings/users/

2. **Click the Eye Icon (👁️) for any user**
   - Look for the gray "View Details" button in the Actions column

3. **Verify the following information is displayed:**
   - ✅ User Information Card shows:
     - Username
     - Full name
     - Email address
     - Account status (Active/Inactive badges)
     - Superuser/Staff badges (if applicable)
     - Date joined
     - Last login time
   
   - ✅ Profile Information Card shows:
     - Role with level badge
     - Employee ID
     - Department
     - Phone number
     - Profile status
     - Profile creation date
   
   - ✅ Activity Statistics Card shows:
     - Number of leads created
     - Number of leads assigned
     - Number of activities logged

4. **Test Navigation:**
   - Click "Back to Users" → Should return to user list
   - Click "Edit User" → Should go to edit form
   - Click "Reset Password" → Should go to password reset

### Expected Results
- All user information displays correctly
- No errors in console
- Statistics are accurate
- Navigation buttons work properly

### URL Format
```
http://127.0.0.1:8000/settings/users/<user_id>/credentials/
```

---

## ✅ Feature 2: Reset User Password

### What It Does
Allows superuser to reset any user's password with:
- Password strength indicator
- Real-time password matching validation
- Show/hide password toggle
- Minimum 8 character requirement

### How to Test

1. **Navigate to User Management Dashboard:**
   - URL: http://127.0.0.1:8000/settings/users/

2. **Click the Key Icon (🔑) for any user**
   - Look for the yellow "Reset Password" button

3. **Test Password Validation:**

   **Test Case 1: Weak Password**
   - Enter password: `test123`
   - Expected: Red "Weak" strength indicator
   - Click Reset → Should show error "Password must be at least 8 characters long"

   **Test Case 2: Mismatched Passwords**
   - New Password: `MyPassword123`
   - Confirm Password: `MyPassword456`
   - Expected: Red message "✗ Passwords do not match"
   - Click Reset → Should show alert

   **Test Case 3: Strong Password**
   - New Password: `SecurePass123!`
   - Confirm Password: `SecurePass123!`
   - Expected: 
     - Green "Strong" strength indicator
     - Green message "✓ Passwords match"
   - Click Reset → Should prompt confirmation
   - Confirm → Should show success message

4. **Test Password Visibility Toggle:**
   - Click eye icon button next to password field
   - Password should become visible/hidden

5. **Test the Reset:**
   - After resetting, logout
   - Try logging in as that user with the NEW password
   - Should successfully login

### Expected Results
- Password strength indicator changes color (Red→Yellow→Blue→Green)
- Validation prevents weak/mismatched passwords
- Toggle buttons show/hide passwords
- Success message appears after reset
- User can login with new password

### URL Format
```
http://127.0.0.1:8000/settings/users/<user_id>/reset-password/
```

---

## ✅ Feature 3: Delete User

### What It Does
Permanently deletes a user with:
- Multiple safety confirmations
- Username typing verification
- Prevents deleting yourself
- Prevents deleting other superusers
- Option to deactivate instead

### How to Test

1. **Create a Test User First:**
   - Go to: http://127.0.0.1:8000/settings/users/create/
   - Username: `testuser`
   - Email: `test@example.com`
   - Password: `TestPass123`
   - Role: Salesperson
   - Click "Create User"

2. **Navigate to User Management Dashboard:**
   - URL: http://127.0.0.1:8000/settings/users/

3. **Test Security Restrictions:**

   **Test Case 1: Try to Delete Yourself**
   - Find YOUR username (Affan) in the list
   - Notice: No delete button appears for your own account
   - Expected: ✅ Delete button is hidden for your account

   **Test Case 2: Try to Delete Another Superuser**
   - If another superuser exists, find them in the list
   - Notice: No delete button appears for superuser accounts
   - Expected: ✅ Delete button is hidden for superusers

4. **Test Normal User Deletion:**

   **Step 1: Click Delete Button**
   - Find `testuser` in the list
   - Click the red trash icon (🗑️)
   - Should navigate to confirmation page

   **Step 2: Review Deletion Page**
   - Verify user details are displayed correctly
   - Check "What will be deleted" section
   - Notice the "Deactivate User Instead" suggestion

   **Step 3: Try Submitting Without Confirmation**
   - Leave username field empty
   - Click "Yes, Permanently Delete This User"
   - Expected: Button should be disabled (gray)

   **Step 4: Test Username Verification**
   - Type wrong username: `wronguser`
   - Expected: Delete button stays disabled
   - Type correct username: `testuser`
   - Expected: Delete button becomes enabled (red)

   **Step 5: Complete Deletion**
   - With correct username typed, click "Yes, Permanently Delete This User"
   - Click "OK" on confirmation dialog
   - Expected:
     - Redirects to user management
     - Success message: "User 'testuser' has been permanently deleted"
     - User no longer appears in list

5. **Test Alternative: Deactivate Instead**
   - Create another test user
   - Go to delete confirmation page
   - Click "Deactivate User Instead" button
   - User should be deactivated (not deleted)
   - User still appears in list with "Inactive" badge

### Expected Results
- Cannot delete yourself
- Cannot delete superusers
- Username typing required for confirmation
- Delete button only enables when username matches
- Double confirmation (typing + dialog)
- User is permanently removed
- Success message appears
- Deactivate option works as alternative

### URL Format
```
http://127.0.0.1:8000/settings/users/<user_id>/delete/
```

---

## 🎨 Feature 4: Enhanced User Management Table

### What Changed
The user management table now has 6 action buttons per user:

1. **👁️ View Details** (Gray) - View comprehensive user information
2. **✏️ Edit** (Blue) - Edit user information
3. **🔑 Reset Password** (Yellow) - Reset user password
4. **🛡️ Permissions** (Cyan) - View permission matrix
5. **✓/✗ Toggle Status** (Green/Red) - Activate/deactivate user
6. **🗑️ Delete** (Red) - Delete user (hidden for self/superusers)

### How to Test

1. **Navigate to User Management Dashboard:**
   - URL: http://127.0.0.1:8000/settings/users/

2. **Verify Button Visibility:**
   - For regular users: All 6 buttons visible
   - For yourself: Only 5 buttons (no delete)
   - For other superusers: Only 5 buttons (no delete)

3. **Test Each Button:**
   - **View Details** → Opens credentials page
   - **Edit** → Opens edit form
   - **Reset Password** → Opens password reset
   - **Permissions** → Opens permission matrix
   - **Toggle Status** → Shows confirmation, changes status
   - **Delete** → Opens delete confirmation

4. **Test Tooltips:**
   - Hover over each button
   - Should see descriptive tooltip text

### Expected Results
- All buttons display with correct icons and colors
- Buttons navigate to correct pages
- Delete button hidden for self and superusers
- Tooltips display on hover
- Responsive layout on mobile

---

## 📊 Complete Testing Checklist

### Before Testing
- [ ] Server is running
- [ ] Logged in as superuser
- [ ] Navigate to User Management
- [ ] At least 2-3 test users exist

### View User Credentials
- [ ] Click eye icon opens credentials page
- [ ] User information displays correctly
- [ ] Profile information displays correctly
- [ ] Activity statistics are accurate
- [ ] Navigation buttons work
- [ ] No console errors

### Reset Password
- [ ] Password strength indicator works
- [ ] Password matching validation works
- [ ] Show/hide password toggle works
- [ ] Weak passwords are rejected
- [ ] Strong passwords are accepted
- [ ] User can login with new password
- [ ] Success message appears

### Delete User
- [ ] Cannot see delete button for own account
- [ ] Cannot see delete button for superusers
- [ ] Delete button visible for regular users
- [ ] Confirmation page shows user details
- [ ] Username typing required
- [ ] Button disabled until correct username
- [ ] Double confirmation dialog works
- [ ] User is deleted successfully
- [ ] Success message appears
- [ ] User removed from list
- [ ] "Deactivate instead" option works

### Enhanced UI
- [ ] 6 action buttons display correctly
- [ ] Button colors are appropriate
- [ ] Icons are clear and meaningful
- [ ] Tooltips display on hover
- [ ] Buttons work on mobile
- [ ] Layout is responsive

---

## 🐛 Common Issues & Solutions

### Issue 1: 404 Error on Any Page
**Problem:** URL not found
**Solution:** 
```bash
# Check URLs are registered
python manage.py show_urls | grep accounts_app
```

### Issue 2: Template Not Found
**Problem:** Template does not exist
**Solution:**
```bash
# Verify template files exist
ls accounts_app/templates/accounts_app/
# Should see:
# - user_credentials.html
# - user_password_reset.html
# - user_confirm_delete.html
```

### Issue 3: Permission Denied
**Problem:** Not logged in as superuser
**Solution:** Login with superuser account (Affan)

### Issue 4: Button Not Appearing
**Problem:** Delete button not visible
**Solution:** This is correct behavior for your own account and superusers

### Issue 5: Password Reset Not Working
**Problem:** Password change doesn't work
**Solution:** Check if using set_password() method (not direct assignment)

---

## 🔍 Manual Testing Script

Copy and paste this into a testing document:

```
DATE: ___________
TESTER: ___________

FEATURE 1: VIEW USER CREDENTIALS
URL: /settings/users/<id>/credentials/
[ ] User info displays correctly
[ ] Profile info displays correctly
[ ] Statistics are accurate
[ ] Navigation works
Result: PASS / FAIL
Notes: ___________

FEATURE 2: RESET PASSWORD
URL: /settings/users/<id>/reset-password/
[ ] Strength indicator works
[ ] Validation prevents weak passwords
[ ] Toggle shows/hides password
[ ] Reset successful
[ ] User can login with new password
Result: PASS / FAIL
Notes: ___________

FEATURE 3: DELETE USER
URL: /settings/users/<id>/delete/
[ ] Cannot delete self
[ ] Cannot delete superusers
[ ] Username verification required
[ ] Deletion successful
[ ] Success message displayed
Result: PASS / FAIL
Notes: ___________

FEATURE 4: ENHANCED UI
URL: /settings/users/
[ ] All buttons display correctly
[ ] Buttons navigate properly
[ ] Tooltips work
[ ] Responsive on mobile
Result: PASS / FAIL
Notes: ___________
```

---

## 📸 Screenshots to Capture

For documentation, capture these screenshots:

1. **User Management Dashboard** with new button layout
2. **User Credentials Page** showing all information
3. **Password Reset Page** with strength indicator
4. **Delete Confirmation Page** with warnings
5. **Success Messages** for each operation

---

## 🎓 Testing Tips

1. **Use Multiple Browsers:** Test in Chrome, Firefox, Edge
2. **Test Mobile View:** Use browser dev tools (F12) → Toggle device toolbar
3. **Check Console:** Always check for JavaScript errors (F12 → Console)
4. **Test Edge Cases:** Try empty fields, special characters, very long inputs
5. **Test Permissions:** Test with different user roles (create test accounts)
6. **Document Issues:** Note any bugs or unexpected behavior

---

## 📞 Support

If you encounter any issues during testing:
1. Check the error messages in browser console (F12)
2. Check Django debug output in terminal
3. Review the implementation in `accounts_app/views.py`
4. Check URL configurations in `accounts_app/urls.py`

---

## ✅ Test Summary

After completing all tests, fill this out:

**Overall Result:** PASS / FAIL / PARTIAL

**Working Features:**
- [ ] View User Credentials
- [ ] Reset Password
- [ ] Delete User
- [ ] Enhanced UI

**Issues Found:**
1. ___________
2. ___________
3. ___________

**Recommended Actions:**
___________

---

**Testing Complete!** 🎉
