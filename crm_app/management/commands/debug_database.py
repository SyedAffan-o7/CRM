from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = 'Check database connection and user status'

    def handle(self, *args, **options):
        self.stdout.write('=== DATABASE DEBUG INFO ===')

        # Check environment
        self.stdout.write(f'USE_REMOTE_DB: {os.getenv("USE_REMOTE_DB", "Not set")}')
        self.stdout.write(f'DATABASE_URL set: {bool(os.getenv("DATABASE_URL"))}')
        self.stdout.write(f'DEBUG: {os.getenv("DEBUG", "Not set")}')

        # Check database connection
        try:
            from django.db import connection
            self.stdout.write(f'Database backend: {connection.vendor}')

            # Check users
            users = User.objects.all()
            self.stdout.write(f'Total users: {len(users)}')

            superusers = users.filter(is_superuser=True)
            self.stdout.write(f'Superusers: {len(superusers)}')

            for user in users:
                self.stdout.write(f'  - {user.username} (superuser: {user.is_superuser})')

            if not superusers:
                self.stdout.write(self.style.ERROR('No superusers found!'))
                self.stdout.write('You need to create one using the management command.')
            else:
                self.stdout.write(self.style.SUCCESS('Superusers exist - login should work'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Database error: {str(e)}'))
