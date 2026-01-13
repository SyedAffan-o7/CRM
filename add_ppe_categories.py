import os
import sys
import django

# Resolve project root (where manage.py lives)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User
from products.models import Category

CATEGORIES = [
    "Eye And Face protection",
    "Ear Protection",
    "Head Protection",
    "Safety Gloves",
    "Safety Shoes",
]


def main():
    # Pick a user for created_by FK
    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        print("No users found. Please create a user (e.g., createsuperuser) and rerun.")
        return

    created_count = 0
    for name in CATEGORIES:
        obj, created = Category.objects.get_or_create(
            name=name,
            defaults={
                "description": f"{name} category",
                "created_by": user,
                "is_active": True,
            },
        )
        if created:
            created_count += 1
            print(f"✅ Created: {obj.name}")
        else:
            # Ensure any missing required fields are set (e.g., created_by) if previously created without it
            updated = False
            if obj.created_by_id is None:
                obj.created_by = user
                updated = True
            if obj.description in (None, ""):
                obj.description = f"{name} category"
                updated = True
            if updated:
                obj.save()
                print(f"♻️  Updated: {obj.name}")
            else:
                print(f"📁 Exists: {obj.name}")

    print("\nSummary:")
    print(f"Created: {created_count}")
    print(f"Total active categories: {Category.objects.filter(is_active=True).count()}")


if __name__ == "__main__":
    main()
