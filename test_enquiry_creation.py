#!/usr/bin/env python
import os
import django
from django.test import Client

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

# Test enquiry creation
client = Client(HTTP_HOST='127.0.0.1')

# Test data for enquiry creation
test_data = {
    'contact_name': 'Test User',
    'phone_number': '+919876543210',
    'company_name': 'Test Company',
    'lead_source': '',  # Empty for now
    'lead_status': 'not_fulfilled',
    'enquiry_stage': 'enquiry_received',
    'priority': 'medium',
    'notes': 'Test enquiry created for testing',
    'categories[]': ['1'],  # Assuming category ID 1 exists
    'quantities[]': ['2'],
    'prices[]': ['100.00'],
    'product_descriptions[]': ['Test product description'],
}

print("Testing enquiry creation...")
print("=" * 50)

try:
    # Try to access the enquiry creation form
    response = client.get('/enquiries/add/')
    print(f"Enquiry form access: Status {response.status_code}")

    if response.status_code == 200:
        print("✅ Enquiry form loads successfully")
    else:
        print(f"❌ Enquiry form error: {response.status_code}")

except Exception as e:
    print(f"❌ Error accessing enquiry form: {e}")

print("\nTest completed!")
