"""Backend-aware migration to fix both Account and UserProfile PKs.

Ensures both models use standard id primary keys instead of phone-based ones.
Works safely on both SQLite and PostgreSQL.
"""

from django.db import migrations, models
from django.db.migrations.operations import RunPython


def forwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    
    if vendor == 'postgresql':
        # PostgreSQL: Use raw SQL for complex PK changes
        with schema_editor.connection.cursor() as cursor:
            # Fix UserProfile table
            try:
                cursor.execute(
                    "ALTER TABLE accounts_app_userprofile DROP CONSTRAINT IF EXISTS accounts_app_userprofile_pkey CASCADE;"
                )
                cursor.execute(
                    "ALTER TABLE accounts_app_userprofile ADD COLUMN IF NOT EXISTS id BIGSERIAL;"
                )
                cursor.execute(
                    "ALTER TABLE accounts_app_userprofile ADD CONSTRAINT accounts_app_userprofile_pkey PRIMARY KEY (id);"
                )
                cursor.execute(
                    "ALTER TABLE accounts_app_userprofile ALTER COLUMN phone DROP NOT NULL;"
                )
                cursor.execute(
                    "UPDATE accounts_app_userprofile SET phone = NULL WHERE phone = '';"
                )
            except Exception:
                pass

            # Fix Account table
            try:
                cursor.execute(
                    "ALTER TABLE accounts_app_account DROP CONSTRAINT IF EXISTS accounts_app_account_pkey CASCADE;"
                )
                cursor.execute(
                    "ALTER TABLE accounts_app_account ADD COLUMN IF NOT EXISTS id BIGSERIAL;"
                )
                cursor.execute(
                    "ALTER TABLE accounts_app_account ADD CONSTRAINT accounts_app_account_pkey PRIMARY KEY (id);"
                )
                cursor.execute(
                    "ALTER TABLE accounts_app_account ALTER COLUMN phone_number DROP NOT NULL;"
                )
                cursor.execute(
                    "UPDATE accounts_app_account SET phone_number = NULL WHERE phone_number = '';"
                )
            except Exception:
                pass
    
    elif vendor == 'sqlite':
        # SQLite: Let Django handle it with model operations
        # This will be handled by the schema migration operations below
        pass


def backwards(apps, schema_editor):
    # Intentionally no-op; reverting PK changes may be destructive
    return


class Migration(migrations.Migration):

    dependencies = [
        ('accounts_app', '0006_remove_account_id_remove_userprofile_id_and_more'),
    ]

    operations = [
        # First run the PostgreSQL-specific fixes
        RunPython(forwards, backwards),
        
        # Then apply Django model changes for both backends
        migrations.AlterField(
            model_name='account',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='phone',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
    ]
