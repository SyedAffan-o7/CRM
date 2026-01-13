import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

import sqlite3
from django.conf import settings

db_path = settings.DATABASES['default']['NAME']
print(f'Database path: {db_path}')
print(f'Database exists: {os.path.exists(db_path)}')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'\nTables in database: {len(tables)}')
    for table in tables:
        print(f'  {table[0]}')

    # Check UserProfile specifically
    if any('userprofile' in table[0].lower() for table in tables):
        print('\nUserProfile table exists, checking structure...')
        cursor.execute('PRAGMA table_info(accounts_app_userprofile)')
        columns = cursor.fetchall()
        for col in columns:
            print(f'  {col[1]}: {col[2]} (pk: {col[5]})')
    else:
        print('\nUserProfile table does not exist!')

    conn.close()
else:
    print('Database file does not exist!')
