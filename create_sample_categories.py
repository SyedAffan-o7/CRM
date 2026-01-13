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
from django.contrib.auth.models import User

def create_sample_categories():
    print("=== Creating Sample Categories and Subcategories ===")
    
    # Get or create a user for created_by field
    try:
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
        if not user:
            print("⚠️  No users found! Please create a user first.")
            return
    except Exception as e:
        print(f"Error getting user: {e}")
        return
    
    # Sample categories and their subcategories
    categories_data = {
        "Electronics": [
            "Mobile Phones",
            "Laptops",
            "Tablets",
            "Cameras",
            "Audio Equipment"
        ],
        "Home & Garden": [
            "Furniture",
            "Kitchen Appliances",
            "Garden Tools",
            "Home Decor",
            "Lighting"
        ],
        "Automotive": [
            "Car Parts",
            "Motorcycles",
            "Car Accessories",
            "Tires",
            "Car Care"
        ],
        "Fashion": [
            "Men's Clothing",
            "Women's Clothing",
            "Shoes",
            "Accessories",
            "Jewelry"
        ]
    }
    
    created_categories = 0
    created_subcategories = 0
    
    for category_name, subcategory_names in categories_data.items():
        # Create or get category
        category, created = Category.objects.get_or_create(
            name=category_name,
            defaults={
                'description': f'{category_name} products and services',
                'created_by': user,
                'is_active': True
            }
        )
        
        if created:
            created_categories += 1
            print(f"✅ Created category: {category_name}")
        else:
            print(f"📁 Category already exists: {category_name}")
        
        # Create subcategories
        for subcategory_name in subcategory_names:
            subcategory, created = Subcategory.objects.get_or_create(
                name=subcategory_name,
                category=category,
                defaults={
                    'description': f'{subcategory_name} in {category_name}',
                    'created_by': user,
                    'is_active': True
                }
            )
            
            if created:
                created_subcategories += 1
                print(f"  ✅ Created subcategory: {subcategory_name}")
            else:
                print(f"  📄 Subcategory already exists: {subcategory_name}")
    
    print(f"\n=== Summary ===")
    print(f"Categories created: {created_categories}")
    print(f"Subcategories created: {created_subcategories}")
    
    # Final count
    total_categories = Category.objects.filter(is_active=True).count()
    total_subcategories = Subcategory.objects.filter(is_active=True).count()
    print(f"Total active categories: {total_categories}")
    print(f"Total active subcategories: {total_subcategories}")

def check_existing_data():
    print("=== Checking Existing Data ===")
    
    categories = Category.objects.filter(is_active=True)
    print(f"Active Categories: {categories.count()}")
    
    for category in categories:
        subcategories = Subcategory.objects.filter(category=category, is_active=True)
        print(f"  {category.name}: {subcategories.count()} subcategories")
    
    return categories.count()

if __name__ == '__main__':
    existing_count = check_existing_data()
    
    if existing_count == 0:
        print("\nNo categories found. Creating sample data...")
        create_sample_categories()
    else:
        print(f"\n{existing_count} categories already exist.")
        create_anyway = input("Create additional sample categories? (y/n): ")
        if create_anyway.lower() == 'y':
            create_sample_categories()
    
    print("\n=== Final Check ===")
    check_existing_data()
