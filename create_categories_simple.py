import os
import sys
import django

# Add the project directory to Python path
project_path = r"D:\Aafiya Proj\crm\aaa-2"
sys.path.append(project_path)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from products.models import Category
from django.contrib.auth.models import User

def create_categories():
    print("Creating sample categories...")

    # Get a user
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
    if not user:
        print("No users found! Please create a user first.")
        return

    # Create sample categories
    categories_data = [
        "Electronics",
        "Home & Garden",
        "Automotive",
        "Fashion",
        "Sports & Outdoors",
        "Books & Media",
        "Health & Beauty",
        "Industrial Equipment"
    ]

    created_count = 0
    for cat_name in categories_data:
        category, created = Category.objects.get_or_create(
            name=cat_name,
            defaults={
                'description': f'{cat_name} products and services',
                'created_by': user,
                'is_active': True
            }
        )

        if created:
            created_count += 1
            print(f"✅ Created category: {cat_name}")
        else:
            print(f"📁 Category already exists: {cat_name}")

    print(f"\n=== Summary ===")
    print(f"Categories created: {created_count}")

    # Final count
    total_categories = Category.objects.filter(is_active=True).count()
    print(f"Total active categories: {total_categories}")

    # List all categories
    print("\n=== All Categories ===")
    for cat in Category.objects.filter(is_active=True).order_by('name'):
        print(f"- {cat.name} (ID: {cat.id})")

if __name__ == '__main__':
    create_categories()
