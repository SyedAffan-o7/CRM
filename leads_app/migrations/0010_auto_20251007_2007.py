"""Backend-aware cleanup migration.

Only execute DROP COLUMN on backends that support it (e.g., PostgreSQL).
SQLite either lacks IF EXISTS support for DROP COLUMN or requires table
rebuilds; on SQLite we NO-OP safely.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor != 'postgresql':
        # No-op on SQLite and others to avoid syntax errors
        return
    with schema_editor.connection.cursor() as cursor:
        try:
            cursor.execute('ALTER TABLE leads_app_lead DROP COLUMN IF EXISTS quantity;')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE leads_app_lead DROP COLUMN IF EXISTS price;')
        except Exception:
            pass


def backwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        try:
            cursor.execute('ALTER TABLE leads_app_lead ADD COLUMN quantity INTEGER DEFAULT 1;')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE leads_app_lead ADD COLUMN price DECIMAL(10,2) NULL;')
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('leads_app', '0009_alter_leadproduct_price'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
