#!/usr/bin/env python
import os
import django
import sys

# Setup Django
sys.path.append(r'd:\Aafiya Proj\crm\aaa-2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.db import connection

# Check table schema
with connection.cursor() as cursor:
    if connection.vendor == 'sqlite3':
        cursor.execute("PRAGMA table_info(accounts_app_userprofile);")
        columns = cursor.fetchall()
        print("SQLite table info:")
        for col in columns:
            print(f"  {col[1]}: {col[2]} {'NOT NULL' if col[3] else 'NULL'} {'PRIMARY KEY' if col[5] else ''}")
    else:
        # For PostgreSQL
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'accounts_app_userprofile'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        print("PostgreSQL table info:")
        for col in columns:
            print(f"  {col[0]}: {col[1]} {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
