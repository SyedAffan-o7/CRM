#!/usr/bin/env python
"""
Debug script to check if URLs are properly registered
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.urls import reverse
from django.contrib.auth.models import User

print("🔍 Checking URL Registration...")
print("=" * 50)

try:
    # Test if URLs exist
    test_user_id = 1
    
    urls_to_test = [
        ('accounts_app:user_management', 'User Management Dashboard'),
        ('accounts_app:view_user_credentials', 'View User Credentials', test_user_id),
        ('accounts_app:reset_user_password', 'Reset User Password', test_user_id),
        ('accounts_app:delete_user', 'Delete User', test_user_id),
    ]
    
    for url_test in urls_to_test:
        try:
            if len(url_test) == 3:  # URL with parameter
                url_name, description, user_id = url_test
                url = reverse(url_name, kwargs={'user_id': user_id})
            else:  # URL without parameter
                url_name, description = url_test
                url = reverse(url_name)
            
            print(f"✅ {description}: {url}")
        except Exception as e:
            print(f"❌ {description}: ERROR - {e}")
    
    print("\n🔍 Checking Users...")
    print("=" * 50)
    
    users = User.objects.all()
    print(f"Total users in database: {users.count()}")
    
    for user in users[:3]:  # Show first 3 users
        print(f"- User ID: {user.id}, Username: {user.username}, Superuser: {user.is_superuser}")
    
    print("\n🔍 Checking Views...")
    print("=" * 50)
    
    from accounts_app import views
    
    view_functions = [
        'view_user_credentials',
        'reset_user_password', 
        'delete_user'
    ]
    
    for view_name in view_functions:
        if hasattr(views, view_name):
            print(f"✅ View function '{view_name}' exists")
        else:
            print(f"❌ View function '{view_name}' NOT FOUND")

except Exception as e:
    print(f"❌ Error during URL check: {e}")
    import traceback
    traceback.print_exc()
