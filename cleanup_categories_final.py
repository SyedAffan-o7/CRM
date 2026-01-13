#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from products.models import Category

def cleanup_categories():
    print("=== Category Cleanup ===")

    # Categories to keep
    categories_to_keep = [
        'Eye And Face protection',
        'Ear Protection Ear plugs And Muffs',
        'Head Protection',
        'Safety Gloves',
        'Safety Shoes'
    ]

    print("Categories to keep:")
    for cat in categories_to_keep:
        print(f"  - {cat}")

    # Get categories to delete
    categories_to_delete = Category.objects.exclude(name__in=categories_to_keep)

    print(f"\nFound {categories_to_delete.count()} categories to delete:")
    for category in categories_to_delete:
        print(f"  - {category.name} (ID: {category.id})")

    if categories_to_delete:
        print(f"\nDeleting {categories_to_delete.count()} categories...")
        deleted_count, _ = categories_to_delete.delete()
        print(f"✅ Successfully deleted {deleted_count} categories")
    else:
        print("ℹ️  No categories to delete")

    # Show remaining categories
    remaining_categories = Category.objects.all()
    print(f"\nRemaining categories ({remaining_categories.count()}):")
    for category in remaining_categories:
        print(f"  - {category.name} (ID: {category.id})")

if __name__ == '__main__':
    cleanup_categories()
