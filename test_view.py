#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from accounts_app.views import user_permissions_detail

def test_view_function():
    """Test the user_permissions_detail view function"""
    print("=== Testing View Function ===")

    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/accounts/users/1/permissions/')
    request.user = User.objects.first()  # Use the first user (should be superuser)

    try:
        # Call the view function
        response = user_permissions_detail(request, 1)

        print(f"Response status: {response.status_code}")
        print(f"Response type: {type(response)}")
        print(f"Response is render: {hasattr(response, 'context_data')}")
        print(f"Response content: {response.content[:200] if hasattr(response, 'content') else 'No content'}")

        if hasattr(response, 'context_data'):
            context = response.context_data
            print(f"Context keys: {list(context.keys())}")
            print(f"User in context: {context.get('user')}")
            print(f"Permissions in context: {context.get('permissions', [])}")
            print(f"Permissions count: {len(context.get('permissions', []))}")

            permissions = context.get('permissions', [])
            if permissions:
                print(f"First permission: {permissions[0]}")
            else:
                print("❌ No permissions in context!")

    except Exception as e:
        print(f"❌ Error calling view: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_view_function()
