#!/usr/bin/env python
import os
import django
import sys

# Setup Django
sys.path.insert(0, r'd:\Aafiya Proj\crm\aaa-2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from accounts_app.models import UserProfile
from django.contrib.auth.models import User

# Test saving a profile with phone=None
try:
    user = User.objects.filter(is_active=True).first()
    if user:
        profile = user.profile
        print(f"Current phone value: {repr(profile.phone)}")
        profile.phone = None
        profile.save()
        print("Successfully saved phone=None")
    else:
        print("No active user found")
except Exception as e:
    print(f"Error: {e}")
