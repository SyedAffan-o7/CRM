#!/usr/bin/env python
import os
import django
from django.test import Client

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

# Test the user management page
client = Client()

# Try to access the settings/users page
try:
    response = client.get('/settings/users/')
    print(f"Status Code: {response.status_code}")
    print(f"Redirect Chain: {len(response.redirect_chain)} redirects")

    if len(response.redirect_chain) > 0:
        for i, (url, status) in enumerate(response.redirect_chain):
            print(f"  Redirect {i+1}: {url} (Status: {status})")

    if response.status_code == 200:
        print("✅ SUCCESS: User management page loads correctly!")
        print("Page title found in content:", b'User Management' in response.content)
    elif response.status_code in [301, 302]:
        print("⚠️  REDIRECT: Final redirect to:", response.get('Location', 'Unknown'))
    else:
        print(f"❌ ERROR: Status {response.status_code}")
        print("Response content length:", len(response.content))
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
