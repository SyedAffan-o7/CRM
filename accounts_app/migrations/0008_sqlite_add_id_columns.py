"""
SQLite compatibility migration: ensure 'id' columns exist on Account and UserProfile.

Context: Earlier schema had phone-based PKs and lacked an 'id' column on SQLite.
This migration adds an 'id' INTEGER column and populates it, so Django ORM can
work with models that expect an 'id' primary key. SQLite cannot alter primary keys
in-place; we add the column and create unique indexes as a pragmatic workaround.
"""
from django.db import migrations, models
from django.db.migrations.operations import RunPython

def forwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor != 'sqlite':
        return

    with schema_editor.connection.cursor() as cursor:
        # Add id to accounts_app_userprofile if missing
        try:
            cursor.execute("PRAGMA table_info(accounts_app_userprofile);")
            cols = [row[1] for row in cursor.fetchall()]  # name at index 1
            if 'id' not in cols:
                cursor.execute("ALTER TABLE accounts_app_userprofile ADD COLUMN id INTEGER;")
                # Populate with rowid for uniqueness
                cursor.execute("UPDATE accounts_app_userprofile SET id = rowid WHERE id IS NULL;")
                # Create a unique index to mimic PK behavior
                cursor.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS accounts_app_userprofile_id_unique ON accounts_app_userprofile(id);"
                )
        except Exception:
            pass

        # Add id to accounts_app_account if missing
        try:
            cursor.execute("PRAGMA table_info(accounts_app_account);")
            cols = [row[1] for row in cursor.fetchall()]
            if 'id' not in cols:
                cursor.execute("ALTER TABLE accounts_app_account ADD COLUMN id INTEGER;")
                cursor.execute("UPDATE accounts_app_account SET id = rowid WHERE id IS NULL;")
                cursor.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS accounts_app_account_id_unique ON accounts_app_account(id);"
                )
        except Exception:
            pass


def backwards(apps, schema_editor):
    # No-op; removing columns or indexes on SQLite is unnecessary and risky
    return


class Migration(migrations.Migration):
    dependencies = [
        ('accounts_app', '0007_fix_userprofile_phone_primary_key_postgres'),
    ]

    operations = [
        RunPython(forwards, backwards),
    ]
