from django.core.management.base import BaseCommand
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Debug S3 media storage configuration'

    def handle(self, *args, **options):
        self.stdout.write('=== S3 Media Storage Debug ===\n')

        # Check environment variables
        self.stdout.write('Environment Variables:')
        env_vars = ['USE_S3_MEDIA', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                   'AWS_STORAGE_BUCKET_NAME', 'AWS_S3_REGION_NAME', 'AWS_S3_CUSTOM_DOMAIN']
        for var in env_vars:
            value = os.getenv(var, 'NOT SET')
            # Mask sensitive values
            if 'SECRET' in var or 'KEY' in var:
                value = value[:10] + '...' if value != 'NOT SET' else value
            self.stdout.write(f'  {var}: {value}')

        self.stdout.write('\nDjango Settings:')
        self.stdout.write(f'  USE_S3: {getattr(settings, "USE_S3", "Not found")}')
        self.stdout.write(f'  DEFAULT_FILE_STORAGE: {getattr(settings, "DEFAULT_FILE_STORAGE", "Not found")}')
        self.stdout.write(f'  MEDIA_URL: {getattr(settings, "MEDIA_URL", "Not found")}')
        self.stdout.write(f'  MEDIA_ROOT: {getattr(settings, "MEDIA_ROOT", "Not found")}')

        # Test S3 connection if enabled
        if getattr(settings, 'USE_S3', False):
            self.stdout.write('\nTesting S3 Connection...')
            try:
                from django.core.files.storage import default_storage
                # Try to list files in bucket
                dirs, files = default_storage.listdir('')
                self.stdout.write(f'  ✅ S3 Connection successful')
                self.stdout.write(f'  📁 Files in bucket: {len(files)}')
                if files:
                    self.stdout.write(f'  📄 Sample files: {files[:3]}')
            except Exception as e:
                self.stdout.write(f'  ❌ S3 Connection failed: {e}')
        else:
            self.stdout.write('\nS3 is disabled - using local storage')
