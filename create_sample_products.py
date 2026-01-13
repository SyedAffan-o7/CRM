#!/usr/bin/env python
"""
Script to create sample products for testing the CRM system
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from crm_app.models import Product

def create_sample_products():
    """Create sample products for testing"""
    sample_products = [
        {'name': 'Safety Gloves', 'description': 'Customer Relationship Management Software', 'category': 'Software'},
        {'name': 'Safety Helmet', 'description': 'Enterprise Resource Planning System', 'category': 'Software'},
        {'name': 'Coverall', 'description': 'Custom Website Development Services', 'category': 'Services'},
        {'name': 'Safety Goggles', 'description': 'iOS and Android App Development', 'category': 'Services'},
        {'name': 'Safety Shoes', 'description': 'SEO, Social Media, and Online Marketing', 'category': 'Marketing'},
        {'name': 'Safety Vest', 'description': 'Reliable Cloud Hosting Solutions', 'category': 'Infrastructure'},
        {'name': 'Warning Tape', 'description': 'Technology Consulting and Strategy', 'category': 'Consulting'},
        {'name': 'Safety Harness', 'description': 'Business Intelligence and Data Analysis', 'category': 'Analytics'},
        {'name': 'Lanyard', 'description': 'Security Assessment and Protection', 'category': 'Security'},
        {'name': 'Safety Ladder', 'description': 'Technical Training and Support Services', 'category': 'Support'},
    ]
    
    created_count = 0
    for product_data in sample_products:
        product, created = Product.objects.get_or_create(
            name=product_data['name'],
            defaults={
                'description': product_data['description'],
                'category': product_data['category'],
                'is_active': True
            }
        )
        if created:
            created_count += 1
            print(f"Created product: {product.name}")
        else:
            print(f"Product already exists: {product.name}")
    
    print(f"\nSample products creation complete! Created {created_count} new products.")
    print(f"Total products in system: {Product.objects.count()}")

if __name__ == '__main__':
    create_sample_products()
