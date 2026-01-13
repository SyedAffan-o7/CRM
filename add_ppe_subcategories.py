import os
import sys
import django

# Resolve project root (where manage.py lives)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User
from products.models import Category, Subcategory

DATA = {
    "Eye And Face protection": [
        "Safety Goggle",
        "Face Shield",
        "Mask",
        "Mask Filter",
        "Welding Goggles",
    ],
    "Ear Protection": [
        "Ear plugs And Muffs",
    ],
    "Head Protection": [
        "Safety Helmet",
        "Head Protection Accessories",
        "Bump Cap",
        "Welding Helmet",
        "Head Lamps",
    ],
    "Safety Gloves": [
        "Chemical Gloves",
        "Disposable Gloves",
        "Dotted Gloves",
        "Lattex Gloves",
        "PU Cotted Gloves",
        "Leather Gloves",
        "Welding Gloves",
    ],
    "Safety Shoes": [
        "Gumboots",
        "Foot Accessories",
    ],
}


def main():
    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        print("No users found. Please create a user (e.g., createsuperuser) and rerun.")
        return

    created_subcats = 0
    for cat_name, subcats in DATA.items():
        cat, _ = Category.objects.get_or_create(
            name=cat_name,
            defaults={
                "description": f"{cat_name} category",
                "created_by": user,
                "is_active": True,
            },
        )
        for sc_name in subcats:
            sc, created = Subcategory.objects.get_or_create(
                category=cat,
                name=sc_name,
                defaults={
                    "description": f"{sc_name}",
                    "created_by": user,
                    "is_active": True,
                },
            )
            if created:
                created_subcats += 1
                print(f"✅ Created: {cat.name} -> {sc.name}")
            else:
                updated = False
                if sc.created_by_id is None:
                    sc.created_by = user
                    updated = True
                if sc.is_active is False:
                    sc.is_active = True
                    updated = True
                if updated:
                    sc.save()
                    print(f"♻️  Updated: {cat.name} -> {sc.name}")
                else:
                    print(f"📁 Exists: {cat.name} -> {sc.name}")

    print("\nSummary:")
    print(f"Subcategories created: {created_subcats}")
    total = Subcategory.objects.filter(is_active=True).count()
    print(f"Total active subcategories: {total}")


if __name__ == "__main__":
    main()
