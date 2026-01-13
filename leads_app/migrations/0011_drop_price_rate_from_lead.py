"""Backend-aware cleanup migration for price_rate column on Lead.

Only execute DROP COLUMN on PostgreSQL. NO-OP on SQLite to avoid syntax
errors with IF EXISTS.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        try:
            cursor.execute('ALTER TABLE leads_app_lead DROP COLUMN IF EXISTS price_rate;')
        except Exception:
            pass


def backwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        try:
            cursor.execute('ALTER TABLE leads_app_lead ADD COLUMN price_rate DECIMAL(10,2) NULL;')
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('leads_app', '0010_auto_20251007_2007'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
