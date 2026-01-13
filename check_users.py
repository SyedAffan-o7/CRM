#!/usr/bin/env python
"""
Check current users and their status
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User

print("🔍 Current Users in Database:")
print("=" * 50)

users = User.objects.all()
print(f"Total users: {users.count()}")
print()

for user in users:
    print(f"👤 Username: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Superuser: {'✅ YES' if user.is_superuser else '❌ No'}")
    print(f"   Active: {'✅ YES' if user.is_active else '❌ No'}")
    print(f"   Staff: {'✅ YES' if user.is_staff else '❌ No'}")
    print(f"   Last Login: {user.last_login or 'Never'}")
    print("-" * 30)

print()
print("🔍 To login as superuser, use one of these:")
superusers = users.filter(is_superuser=True, is_active=True)
for su in superusers:
    print(f"   Username: {su.username}")
