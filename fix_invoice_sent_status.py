#!/usr/bin/env python
"""
Script to fix existing enquiries in invoice_sent stage:
- Set status to 'fulfilled'
- Lock the enquiries
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from leads_app.models import Lead
from activities_app.models import ActivityLog

def fix_invoice_sent_enquiries():
    """Fix existing enquiries in invoice_sent stage"""

    # Get all enquiries in invoice_sent stage
    invoice_sent_leads = Lead.objects.filter(enquiry_stage='invoice_sent')

    updated_count = 0
    already_fulfilled_count = 0

    for lead in invoice_sent_leads:
        if lead.lead_status != 'fulfilled':
            # Update to fulfilled and lock
            lead.lead_status = 'fulfilled'
            lead.is_locked = True
            lead.save(update_fields=['lead_status', 'is_locked', 'updated_date'])

            # Create activity log
            ActivityLog.objects.create(
                user=None,  # System action
                activity_type='stage_change',
                content_object=lead,
                details='Automatically set to fulfilled and locked (invoice sent)'
            )

            updated_count += 1
            print(f"✓ Updated lead {lead.id}: {lead.contact_name}")
        else:
            # Already fulfilled, just ensure it's locked
            if not lead.is_locked:
                lead.is_locked = True
                lead.save(update_fields=['is_locked', 'updated_date'])
                print(f"✓ Locked already fulfilled lead {lead.id}: {lead.contact_name}")
            already_fulfilled_count += 1

    print(f"\n📊 Summary:")
    print(f"   Updated to fulfilled: {updated_count}")
    print(f"   Already fulfilled: {already_fulfilled_count}")
    print(f"   Total processed: {invoice_sent_leads.count()}")

if __name__ == '__main__':
    print("🔄 Fixing existing invoice_sent enquiries...")
    fix_invoice_sent_enquiries()
    print("✅ Done!")
