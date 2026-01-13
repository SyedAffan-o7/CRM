from django.core.management.base import BaseCommand
from django.db import transaction
from leads_app.models import Lead
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update existing leads in "won" stage to "fulfilled" status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output of changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']

        # Find all leads that are in "won" stage but have "not_fulfilled" status
        leads_to_update = Lead.objects.filter(
            enquiry_stage='won',
            lead_status='not_fulfilled'
        )

        total_count = leads_to_update.count()

        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ No leads found that need status updates. All "won" stage leads are already "fulfilled".')
            )
            return

        self.stdout.write(
            f'Found {total_count} lead(s) in "won" stage with "not_fulfilled" status that need to be updated.'
        )

        if verbose:
            self.stdout.write('\nLeads to be updated:')
            for lead in leads_to_update:
                self.stdout.write(f'  - Lead ID {lead.id}: {lead.contact_name} ({lead.phone_number})')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made.')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Would update {total_count} lead(s) to "fulfilled" status.')
            )
            return

        # Perform the actual update
        with transaction.atomic():
            updated_count = leads_to_update.update(lead_status='fulfilled')

        self.stdout.write(
            self.style.SUCCESS(f'✅ Successfully updated {updated_count} lead(s) to "fulfilled" status.')
        )

        if verbose:
            self.stdout.write('\nUpdated leads:')
            for lead in Lead.objects.filter(enquiry_stage='won', lead_status='fulfilled')[:total_count]:
                self.stdout.write(f'  - Lead ID {lead.id}: {lead.contact_name} ({lead.phone_number}) -> Fulfilled')
