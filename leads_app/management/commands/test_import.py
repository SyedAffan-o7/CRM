from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from leads_app.models import Lead, Product, Reason
from products.models import Category
import pandas as pd

class Command(BaseCommand):
    help = 'Test import functionality'

    def handle(self, *args, **options):
        self.stdout.write("=== TESTING IMPORT FUNCTIONALITY ===")
        
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='test_import_user',
            defaults={'email': 'test@example.com', 'first_name': 'Test', 'last_name': 'User'}
        )
        self.stdout.write(f"Test user: {user} (created: {created})")
        
        # Test Category creation (should work - has created_by field)
        try:
            category, created = Category.objects.get_or_create(
                name='Test Category Import',
                defaults={'created_by': user}
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Category creation: {category} (created: {created})"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Category creation failed: {e}"))
        
        # Test Product creation (should work now - no created_by field)
        try:
            product, created = Product.objects.get_or_create(
                name='Test Product Import',
                defaults={}
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Product creation: {product} (created: {created})"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Product creation failed: {e}"))
        
        # Test Reason creation (should work now - no created_by field)
        try:
            reason, created = Reason.objects.get_or_create(
                name='Test Reason Import',
                defaults={}
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Reason creation: {reason} (created: {created})"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Reason creation failed: {e}"))
        
        # Test Lead creation
        try:
            lead = Lead.objects.create(
                contact_name='Test Contact Import',
                phone_number='9876543210',
                company_name='Test Company Import',
                image_url='https://example.com/image.jpg',
                category=category,
                lead_status='not_fulfilled',
                enquiry_stage='enquiry_received',
                reason=reason,
                notes='Test import via command',
                created_by=user,
                assigned_sales_person=user,
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Lead creation: {lead}"))
            
            # Add product to lead
            lead.products_enquired.add(product)
            self.stdout.write(self.style.SUCCESS(f"✅ Product added to lead"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Lead creation failed: {e}"))
            import traceback
            self.stdout.write(self.style.ERROR(f"Traceback: {traceback.format_exc()}"))
        
        self.stdout.write("=== TEST COMPLETE ===")
