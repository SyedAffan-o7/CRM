from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings
import os
from leads_app.models import LeadProduct

class Command(BaseCommand):
    help = 'Migrate existing media files to Supabase storage'

    def handle(self, *args, **options):
        if not getattr(settings, 'USE_S3', False):
            self.stdout.write(self.style.WARNING('USE_S3_MEDIA is disabled. Enable it first to migrate files.'))
            return

        # Get all LeadProduct images
        lead_products = LeadProduct.objects.exclude(image='').exclude(image__isnull=True)

        migrated = 0
        skipped = 0

        for lp in lead_products:
            if lp.image and lp.image.name:
                # Check if file exists in current storage
                if default_storage.exists(lp.image.name):
                    self.stdout.write(f'✓ Already migrated: {lp.image.name}')
                    skipped += 1
                else:
                    self.stdout.write(f'⚠️  File not found locally: {lp.image.name}')
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(f'Migration check complete. {migrated} migrated, {skipped} skipped.'))
