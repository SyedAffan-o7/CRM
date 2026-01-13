#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from crm_app.models import Reason

def create_default_reason():
    """Create default 'Enquiry Just Received' reason"""
    
    reason, created = Reason.objects.get_or_create(
        name='Enquiry Just Received',
        defaults={
            'description': 'Default reason for new enquiries that have just been received',
            'is_active': True
        }
    )
    
    if created:
        print(f"✓ Created default reason: {reason.name}")
    else:
        print(f"✓ Default reason already exists: {reason.name}")

if __name__ == '__main__':
    create_default_reason()
