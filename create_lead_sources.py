#!/usr/bin/env python
"""
Create sample lead sources for the CRM system
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from crm_app.models import LeadSource

def create_lead_sources():
    """Create sample lead sources"""
    lead_sources = [
        {'name': 'Website', 'description': 'Leads from company website'},
        {'name': 'Referral', 'description': 'Customer referrals'},
        {'name': 'Social Media', 'description': 'Facebook, LinkedIn, Instagram'},
        {'name': 'Cold Call', 'description': 'Outbound cold calling'},
        {'name': 'Email Campaign', 'description': 'Email marketing campaigns'},
        {'name': 'Trade Show', 'description': 'Industry trade shows and events'},
        {'name': 'Other', 'description': 'Other sources not listed above'},
    ]
    
    created_count = 0
    for source_data in lead_sources:
        source, created = LeadSource.objects.get_or_create(
            name=source_data['name'],
            defaults={'description': source_data['description']}
        )
        if created:
            created_count += 1
            print(f"Created lead source: {source.name}")
        else:
            print(f"Lead source already exists: {source.name}")
    
    print(f"\nTotal lead sources created: {created_count}")
    print(f"Total lead sources in system: {LeadSource.objects.count()}")

if __name__ == '__main__':
    create_lead_sources()
