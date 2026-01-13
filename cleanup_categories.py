from django.core.management.base import BaseCommand
from products.models import Category

class Command(BaseCommand):
    help = 'Clean up categories and keep only safety-related ones'

    def handle(self, *args, **options):
        # Categories to keep
        categories_to_keep = [
            'Eye And Face protection',
            'Ear Protection Ear plugs And Muffs',
            'Head Protection',
            'Safety Gloves',
            'Safety Shoes'
        ]

        # Get categories to delete
        categories_to_delete = Category.objects.exclude(name__in=categories_to_keep)

        if categories_to_delete:
            deleted_count, _ = categories_to_delete.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted_count} categories')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No categories to delete')
            )

        # Show remaining categories
        remaining_categories = Category.objects.all()
        self.stdout.write(
            self.style.SUCCESS(f'Remaining categories ({remaining_categories.count()}):')
        )
        for category in remaining_categories:
            self.stdout.write(f'  - {category.name} (ID: {category.id})')
