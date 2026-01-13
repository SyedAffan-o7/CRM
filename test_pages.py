#!/usr/bin/env python
import os
import django
from django.test import Client

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

# Test key pages that were having issues
client = Client(HTTP_HOST='127.0.0.1')

test_urls = [
    '/settings/users/',
    '/enquiry-stages/',
    '/enquiries/',
]

for url in test_urls:
    try:
        response = client.get(url)
        print(f"URL: {url}")
        print(f"  Status Code: {response.status_code}")

        if hasattr(response, 'redirect_chain') and response.redirect_chain:
            print(f"  Redirect Chain: {len(response.redirect_chain)} redirects")
            for i, (redirect_url, status) in enumerate(response.redirect_chain):
                print(f"    Redirect {i+1}: {redirect_url} (Status: {status})")
        else:
            print("  Redirect Chain: No redirects")
        if response.status_code == 200:
            print("  ✅ SUCCESS")
        elif response.status_code in [301, 302]:
            if len(getattr(response, 'redirect_chain', [])) > 5:  # Too many redirects
                print("  ❌ REDIRECT LOOP DETECTED")
            else:
                print("  ⚠️  REDIRECT")
        else:
            print(f"  ❌ ERROR: {response.status_code}")
    except Exception as e:
        print(f"URL: {url}")
        print(f"  ❌ EXCEPTION: {e}")
        print()

print("Test completed!")
