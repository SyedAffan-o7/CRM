#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from crm_app.models import Product

def update_safety_products():
    """Update existing products to safety-related items"""
    
    safety_products = [
        {'name': 'Safety Helmet', 'description': 'Hard hat for head protection', 'category': 'Head Protection'},
        {'name': 'Safety Net', 'description': 'Fall protection safety net', 'category': 'Fall Protection'},
        {'name': 'Safety Gloves', 'description': 'Cut-resistant work gloves', 'category': 'Hand Protection'},
        {'name': 'Safety Ladder', 'description': 'Industrial safety ladder with railings', 'category': 'Access Equipment'},
        {'name': 'Safety Harness', 'description': 'Full body safety harness', 'category': 'Fall Protection'},
        {'name': 'Coverall', 'description': 'Protective work coverall', 'category': 'Body Protection'},
        {'name': 'Safety Goggles', 'description': 'Eye protection goggles', 'category': 'Eye Protection'},
        {'name': 'Warning Tapes', 'description': 'Reflective warning barrier tape', 'category': 'Signage'},
        {'name': 'Safety Boots', 'description': 'Steel toe safety boots', 'category': 'Foot Protection'},
        {'name': 'High Visibility Vest', 'description': 'Reflective safety vest', 'category': 'Visibility'},
        {'name': 'First Aid Kit', 'description': 'Complete workplace first aid kit', 'category': 'Emergency'},
        {'name': 'Fire Extinguisher', 'description': 'Portable fire extinguisher', 'category': 'Fire Safety'},
    ]
    
    # Clear existing products
    Product.objects.all().delete()
    print("Cleared existing products")
    
    # Add safety products
    for product_data in safety_products:
        product = Product.objects.create(**product_data)
        print(f"Created: {product.name}")
    
    print(f"\n✓ Successfully created {len(safety_products)} safety products")

if __name__ == '__main__':
    update_safety_products()
