import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.db import connection
from accounts_app.models import UserProfile

print('Checking PostgreSQL connection...')
print(f'Database backend: {connection.vendor}')
print(f'Database name: {connection.settings_dict["NAME"]}')

# Check if UserProfile table exists in PostgreSQL
with connection.cursor() as cursor:
    try:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name = %s", ['accounts_app_userprofile'])
        result = cursor.fetchone()
        if result:
            print('UserProfile table exists in PostgreSQL')

            # Get table structure
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
            """, ['accounts_app_userprofile'])

            columns = cursor.fetchall()
            print('\nTable structure:')
            for col in columns:
                print(f'  {col[0]}: {col[1]} (nullable: {col[2]})')
        else:
            print('UserProfile table does not exist in PostgreSQL')
    except Exception as e:
        print(f'Error checking table: {e}')
