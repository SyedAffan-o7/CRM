#!/usr/bin/env python
"""
Setup script for CRM Django application
"""
import os
import sys
import django
from django.core.management import execute_from_command_line
from django.contrib.auth import get_user_model

def setup_database():
    """Set up the database with initial migrations"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
    django.setup()
    
    print("Creating database migrations...")
    execute_from_command_line(['manage.py', 'makemigrations'])
    
    print("Applying migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    
    print("Database setup complete!")

def create_superuser():
    """Create a superuser for admin access"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
    django.setup()
    
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Superuser 'admin' created with password 'admin123'")
    else:
        print("Superuser already exists")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'db':
            setup_database()
        elif sys.argv[1] == 'superuser':
            create_superuser()
        elif sys.argv[1] == 'all':
            setup_database()
            create_superuser()
    else:
        print("Usage: python setup.py [db|superuser|all]")
        print("  db        - Set up database and run migrations")
        print("  superuser - Create admin superuser")
        print("  all       - Do both database setup and create superuser")
