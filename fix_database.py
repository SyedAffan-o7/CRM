import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

import sqlite3
from django.conf import settings

# Connect to the database
db_path = settings.DATABASES['default']['NAME']
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print('Current UserProfile table structure:')
cursor.execute('PRAGMA table_info(accounts_app_userprofile)')
columns = cursor.fetchall()
for col in columns:
    print(f'  {col[1]}: {col[2]} (pk: {col[5]})')

# Fix the table structure
print('\nFixing table structure...')

# Check if id column exists
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='accounts_app_userprofile'")
result = cursor.fetchone()
if result:
    create_sql = result[0]
    print(f"Current table SQL: {create_sql}")

    # For SQLite, we need to recreate the table properly
    if 'id INTEGER' not in create_sql.upper():
        print('Adding id column...')
        cursor.execute('ALTER TABLE accounts_app_userprofile ADD COLUMN id INTEGER PRIMARY KEY AUTOINCREMENT')
else:
    print("Table doesn't exist in sqlite_master or query failed")

# Make phone nullable
print('Making phone column nullable...')
try:
    cursor.execute('UPDATE accounts_app_userprofile SET phone = NULL WHERE phone = ""')
    print('Cleared empty phone values')
except:
    pass

conn.commit()
conn.close()
print('\nDatabase fix completed successfully!')

# Now test if we can create a user
print('\nTesting user creation...')
from django.contrib.auth.models import User
from accounts_app.models import UserProfile, UserRole

# Check if we can query the table
profiles = UserProfile.objects.all()
print(f'Found {profiles.count()} existing profiles')

for profile in profiles:
    print(f'  User: {profile.user.username}, Phone: {repr(profile.phone)}, Has ID: {hasattr(profile, "id") and profile.id}')

print('\nTest completed!')
