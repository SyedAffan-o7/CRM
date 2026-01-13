"""NO-OP migration to preserve id as PK on Lead.

Original 0005 attempted to drop id and make phone_number the PK, which
conflicts with existing FKs (e.g., LeadProduct.lead) on SQLite and causes
foreign key mismatch errors.

We intentionally do nothing here so the schema stays aligned with 0001_initial
(id as PK; phone_number non-PK).
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
        ('leads_app', '0004_clean_phone_data'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
