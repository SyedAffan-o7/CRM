# Generated for phone number primary key conversion

from django.db import migrations
import random

def clean_and_generate_phone_numbers(apps, schema_editor):
    """
    Clean phone number data and generate unique phone numbers for records without them.
    """
    Contact = apps.get_model('customers_app', 'Contact')
    
    # Convert empty strings to None first
    Contact.objects.filter(phone_number='').update(phone_number=None)
    
    # Get all contacts without phone numbers
    contacts_without_phone = Contact.objects.filter(phone_number__isnull=True)
    
    # Generate unique phone numbers for contacts without them
    used_numbers = set(Contact.objects.exclude(phone_number__isnull=True).values_list('phone_number', flat=True))
    
    for contact in contacts_without_phone:
        # Generate a unique phone number
        while True:
            # Generate a random 10-digit phone number starting with +91
            phone_number = f"+91{random.randint(6000000000, 9999999999)}"
            if phone_number not in used_numbers:
                contact.phone_number = phone_number
                contact.save()
                used_numbers.add(phone_number)
                break

class Migration(migrations.Migration):

    dependencies = [
        ('customers_app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(clean_and_generate_phone_numbers, reverse_code=migrations.RunPython.noop),
    ]
