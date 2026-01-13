#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser if it doesn't exist (optional)
python manage.py shell -c "
from django.contrib.auth.models import User
from accounts_app.models import UserRole, UserProfile

# Create default roles if they don't exist
try:
    from accounts_app.management.commands.init_roles import Command
    command = Command()
    command.handle()
    print('Default roles created successfully')
except Exception as e:
    print(f'Roles setup: {e}')

# Create superuser if it doesn't exist
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"
