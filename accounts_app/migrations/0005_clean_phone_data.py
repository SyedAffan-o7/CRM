# Generated for phone number primary key conversion

from django.db import migrations, models
from django.db.migrations.operations import RunPython
import random

def clean_and_generate_phone_numbers(apps, schema_editor):
    """
    Clean phone number data and generate unique phone numbers for records without them.
    """
    Account = apps.get_model('accounts_app', 'Account')
    UserProfile = apps.get_model('accounts_app', 'UserProfile')
    
    # Clean Account phone numbers
    Account.objects.filter(phone_number='').update(phone_number=None)
    accounts_without_phone = Account.objects.filter(phone_number__isnull=True)
    used_numbers = set(Account.objects.exclude(phone_number__isnull=True).values_list('phone_number', flat=True))
    
    for account in accounts_without_phone:
        while True:
            phone_number = f"+91{random.randint(6000000000, 9999999999)}"
            if phone_number not in used_numbers:
                account.phone_number = phone_number
                account.save()
                used_numbers.add(phone_number)
                break
    
    # Clean UserProfile phone numbers
    UserProfile.objects.filter(phone='').update(phone=None)
    profiles_without_phone = UserProfile.objects.filter(phone__isnull=True)
    used_profile_numbers = set(UserProfile.objects.exclude(phone__isnull=True).values_list('phone', flat=True))
    
    for profile in profiles_without_phone:
        while True:
            phone_number = f"+91{random.randint(6000000000, 9999999999)}"
            if phone_number not in used_profile_numbers and phone_number not in used_numbers:
                profile.phone = phone_number
                profile.save()
                used_profile_numbers.add(phone_number)
                used_numbers.add(phone_number)
                break

class Migration(migrations.Migration):

    dependencies = [
        ('accounts_app', '0004_alter_account_phone_number_alter_userprofile_phone'),
    ]

    operations = [
        migrations.RunPython(clean_and_generate_phone_numbers, reverse_code=RunPython.noop),
    ]
