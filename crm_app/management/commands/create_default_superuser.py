from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = 'Create a default superuser for production deployment'

    def handle(self, *args, **options):
        # Get credentials from environment variables
        username = os.getenv('DEFAULT_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DEFAULT_SUPERUSER_EMAIL', 'admin@yourapp.com')
        password = os.getenv('DEFAULT_SUPERUSER_PASSWORD')

        if not password:
            self.stdout.write(
                self.style.ERROR(
                    'DEFAULT_SUPERUSER_PASSWORD environment variable is required'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    'Please set DEFAULT_SUPERUSER_PASSWORD in your Render environment variables'
                )
            )
            return

        # Check if superuser already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" already exists')
            )
            return

        # Create superuser
        try:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created superuser: {username}'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to create superuser: {str(e)}')
            )
