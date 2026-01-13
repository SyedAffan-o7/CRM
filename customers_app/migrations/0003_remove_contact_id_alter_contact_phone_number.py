"""Make this migration a NO-OP to preserve id as primary key on Contact.

The original migration attempted to drop the implicit id PK and make
phone_number the primary key. That causes FK mismatches on SQLite with
existing migrations (e.g., deals_app.Deal.contact).

We intentionally do nothing here so the schema stays aligned with 0001_initial
(id as PK, phone_number unique).
"""

from django.db import migrations


def forwards(apps, schema_editor):
    # No-op intentionally
    return


def backwards(apps, schema_editor):
    # No-op intentionally
    return


class Migration(migrations.Migration):

    dependencies = [
        ('customers_app', '0002_clean_phone_data'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
