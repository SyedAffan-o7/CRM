# Generated for phone number primary key conversion

from django.db import migrations
import random

def clean_and_generate_phone_numbers(apps, schema_editor):
    """
    Clean phone number data and generate unique phone numbers for records without them.
    """
    Lead = apps.get_model('leads_app', 'Lead')
    
    # Convert empty strings and None to unique phone numbers
    Lead.objects.filter(phone_number='').update(phone_number=None)
    leads_without_phone = Lead.objects.filter(phone_number__isnull=True)
    used_numbers = set(Lead.objects.exclude(phone_number__isnull=True).values_list('phone_number', flat=True))
    
    for lead in leads_without_phone:
        while True:
            phone_number = f"+91{random.randint(6000000000, 9999999999)}"
            if phone_number not in used_numbers:
                lead.phone_number = phone_number
                lead.save()
                used_numbers.add(phone_number)
                break

class Migration(migrations.Migration):

    dependencies = [
        ('leads_app', '0003_alter_lead_phone_number'),
    ]

    operations = [
        migrations.RunPython(clean_and_generate_phone_numbers, reverse_code=migrations.RunPython.noop),
    ]
