#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from products.models import Category, Subcategory

def check_categories():
    print("=== Categories and Subcategories Check ===")
    
    categories = Category.objects.filter(is_active=True)
    print(f"\nActive Categories: {categories.count()}")
    
    for category in categories:
        print(f"\nCategory: {category.name} (ID: {category.id})")
        subcategories = Subcategory.objects.filter(category=category, is_active=True)
        print(f"  Subcategories: {subcategories.count()}")
        
        for subcategory in subcategories:
            print(f"    - {subcategory.name} (ID: {subcategory.id})")
    
    if categories.count() == 0:
        print("\n⚠️  No active categories found!")
        print("You need to create categories first.")
    
    total_subcategories = Subcategory.objects.filter(is_active=True).count()
    print(f"\nTotal active subcategories: {total_subcategories}")
    
    if total_subcategories == 0:
        print("⚠️  No active subcategories found!")
        print("You need to create subcategories for your categories.")

if __name__ == '__main__':
    check_categories()
