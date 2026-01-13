#!/usr/bin/env python
"""
Script to create sample reasons for Not Fulfilled enquiries
Run this script: python create_sample_reasons.py
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from crm_app.models import Reason

def create_sample_reasons():
    """Create sample reasons for Not Fulfilled enquiries"""
    
    reasons_data = [
        {
            'name': 'Price too high',
            'description': 'Customer found our pricing too expensive compared to competitors'
        },
        {
            'name': 'Not interested in product',
            'description': 'Customer decided they do not need this product/service'
        },
        {
            'name': 'Budget constraints',
            'description': 'Customer does not have sufficient budget at this time'
        },
        {
            'name': 'Timing not right',
            'description': 'Customer wants to purchase later, not now'
        },
        {
            'name': 'Went with competitor',
            'description': 'Customer chose a competitor\'s product/service'
        },
        {
            'name': 'Technical requirements not met',
            'description': 'Our product does not meet customer\'s technical specifications'
        },
        {
            'name': 'No decision maker contact',
            'description': 'Unable to reach the person who makes purchasing decisions'
        },
        {
            'name': 'Company policy restrictions',
            'description': 'Customer\'s company policy prevents them from purchasing'
        },
        {
            'name': 'Already have similar solution',
            'description': 'Customer already has a similar product/service in place'
        },
        {
            'name': 'Lost contact',
            'description': 'Customer stopped responding to our communications'
        }
    ]
    
    created_count = 0
    
    for reason_data in reasons_data:
        reason, created = Reason.objects.get_or_create(
            name=reason_data['name'],
            defaults={
                'description': reason_data['description'],
                'is_active': True
            }
        )
        
        if created:
            created_count += 1
            print(f"✓ Created reason: {reason.name}")
        else:
            print(f"- Reason already exists: {reason.name}")
    
    print(f"\n✅ Sample reasons setup complete!")
    print(f"📊 Created {created_count} new reasons")
    print(f"📋 Total active reasons: {Reason.objects.filter(is_active=True).count()}")

if __name__ == '__main__':
    create_sample_reasons()
