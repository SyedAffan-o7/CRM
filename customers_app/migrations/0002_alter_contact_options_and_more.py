"""No-op migration.

This migration intentionally left blank because the new 0001_initial defines the
final Contact schema. Keeping this file preserves numbering for environments
that had an earlier 0002, while avoiding conflicting operations.
"""

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts_app', '0006_remove_account_id_remove_userprofile_id_and_more'),
        ('customers_app', '0001_initial'),
    ]

    operations = []
