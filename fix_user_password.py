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

def fix_user_password():
    """Fix user password by setting it properly"""
    try:
        user = User.objects.get(username='Unni')
        print(f"Found user: {user.username}")
        print(f"Current password hash: {user.password[:50]}...")
        
        # Set a proper password
        user.set_password('unni123')
        user.save()
        
        print(f"✓ Password updated for user '{user.username}'")
        print(f"New password hash: {user.password[:50]}...")
        print(f"You can now login with username: 'Unni' and password: 'unni123'")
        
    except User.DoesNotExist:
        print("✗ User 'unni' not found")

if __name__ == '__main__':
    fix_user_password()
