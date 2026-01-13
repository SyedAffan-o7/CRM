#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User
from accounts_app.models import UserProfile, UserRole, UserPermissions

def test_permissions_display():
    """Test if permissions are being displayed correctly"""
    print("=== Testing Permissions Display ===")

    # Get the first user
    user = User.objects.first()
    if not user:
        print("No users found!")
        return

    print(f"Testing user: {user.username}")

    # Check if user has profile
    if not hasattr(user, 'profile'):
        print("User has no profile!")
        return

    profile = user.profile
    print(f"User role: {profile.role.display_name if profile.role else 'No role'}")

    # Check permissions
    if profile.role:
        permissions = profile.role.permissions.all()
        print(f"Total permissions: {permissions.count()}")

        for perm in permissions[:3]:  # Show first 3 permissions
            print(f"  - {perm.get_module_display()}: view={perm.can_view}, create={perm.can_create}, edit={perm.can_edit}")

        # Test the view logic
        permissions_list = []
        for permission in permissions:
            permissions_list.append({
                'module': permission.get_module_display(),
                'can_view': permission.can_view,
                'can_create': permission.can_create,
                'can_edit': permission.can_edit,
                'can_delete': permission.can_delete,
                'can_import': permission.can_import,
                'can_export': permission.can_export,
            })

        print(f"Permissions list length: {len(permissions_list)}")
        print(f"First permission: {permissions_list[0] if permissions_list else 'No permissions'}")

        # Check if permissions would be empty
        if not permissions_list:
            print("❌ Permissions list is empty!")
        else:
            print("✅ Permissions list has data!")

    else:
        print("❌ User has no role assigned!")

if __name__ == '__main__':
    test_permissions_display()
