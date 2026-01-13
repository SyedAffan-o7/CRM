#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def debug_user_auth():
    print("=== User Authentication Debug ===")
    
    # Check if user 'unni' exists
    try:
        user = User.objects.get(username='unni')
        print(f"✓ User 'unni' found")
        print(f"  - Active: {user.is_active}")
        print(f"  - Staff: {user.is_staff}")
        print(f"  - Superuser: {user.is_superuser}")
        print(f"  - Password hash: {user.password[:50]}...")
        print(f"  - Date joined: {user.date_joined}")
        print(f"  - Last login: {user.last_login}")
        
        # Test authentication with common passwords
        test_passwords = ['password', 'unni', 'admin', '123456', 'test123', 'unni123']
        
        print(f"\n=== Testing Authentication ===")
        for pwd in test_passwords:
            auth_user = authenticate(username='unni', password=pwd)
            if auth_user:
                print(f"✓ Authentication SUCCESS with password: '{pwd}'")
                break
            else:
                print(f"✗ Authentication FAILED with password: '{pwd}'")
        
        # Check if password is properly hashed
        if user.password.startswith('pbkdf2_sha256$') or user.password.startswith('argon2$'):
            print(f"✓ Password is properly hashed")
        else:
            print(f"✗ Password may not be properly hashed: {user.password}")
            
    except User.DoesNotExist:
        print("✗ User 'unni' not found")
        
    # List all users
    print(f"\n=== All Users ===")
    for u in User.objects.all():
        print(f"- {u.username} (Active: {u.is_active}, Hash: {u.password[:20]}...)")

if __name__ == '__main__':
    debug_user_auth()
