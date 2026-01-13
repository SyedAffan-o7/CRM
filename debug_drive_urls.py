import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from leads_app.models import Lead
from media_app.views import google_drive_url

# Check a few Google Drive images
leads = Lead.objects.exclude(image_url__isnull=True).exclude(image_url='')[:5]
print("Checking Google Drive URLs:")
print("=" * 50)

for lead in leads:
    original = lead.image_url
    converted = google_drive_url(original)
    print(f'Lead: {lead.contact_name}')
    print(f'Original: {original}')
    print(f'Converted: {converted}')
    print('---')
