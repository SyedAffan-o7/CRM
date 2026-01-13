from django.core.management.base import BaseCommand
from django.db.models import Q
from leads_app.models import Lead
from media_app.views import check_google_drive_accessibility, google_drive_url
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check and fix Google Drive image accessibility issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix inaccessible images by updating URLs',
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Remove invalid entries like "No Photo" from the database',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        self.stdout.write('Checking Google Drive image accessibility...\n')

        # Get all leads with Google Drive URLs
        google_drive_leads = Lead.objects.exclude(image_url__isnull=True).exclude(image_url='')

        total = google_drive_leads.count()
        self.stdout.write(f'Found {total} leads with image URLs\n')

        accessible = 0
        inaccessible = 0
        invalid = 0
        fixed = 0
        cleaned = 0

        for lead in google_drive_leads:
            original_url = lead.image_url

            # Check for invalid entries first
            if original_url.strip().lower() in ['no photo', 'n/a', 'none', '']:
                invalid += 1
                if options['clean']:
                    if options['dry_run']:
                        self.stdout.write(
                            self.style.WARNING(f'WOULD CLEAN: {lead.contact_name} - invalid entry "{original_url}"')
                        )
                    else:
                        lead.image_url = None
                        lead.save()
                        cleaned += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ CLEANED: {lead.contact_name} - removed invalid entry "{original_url}"')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'❌ INVALID: {lead.contact_name} - "{original_url}" (use --clean to remove)')
                    )
                continue

            # Process valid-looking URLs
            converted_url = google_drive_url(original_url)
            if converted_url is None:
                # This shouldn't happen now with our improved validation, but just in case
                invalid += 1
                continue

            # Check accessibility
            status = check_google_drive_accessibility(converted_url)

            if status['accessible']:
                accessible += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Accessible: {lead.contact_name} - {converted_url}')
                )
            else:
                inaccessible += 1
                reason = status.get('reason', status.get('error', 'Unknown'))
                self.stdout.write(
                    self.style.ERROR(f'✗ Inaccessible: {lead.contact_name} - {converted_url} ({reason})')
                )

                if options['fix'] and not options['dry_run']:
                    # Try alternative URL formats
                    file_id = None
                    if 'drive.google.com/file/d/' in original_url:
                        start = original_url.find('/file/d/') + 8
                        end = original_url.find('/view?usp=sharing')
                        if start != -1 and end != -1:
                            file_id = original_url[start:end]

                    if file_id:
                        # Try thumbnail URL as alternative (now this is the primary format)
                        thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
                        thumb_status = check_google_drive_accessibility(thumbnail_url)

                        if thumb_status['accessible']:
                            lead.image_url = thumbnail_url
                            lead.save()
                            fixed += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  → Fixed with thumbnail URL: {thumbnail_url}')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'  → Could not fix: thumbnail also inaccessible')
                            )

        # Summary
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'Total entries checked: {total}')
        self.stdout.write(self.style.SUCCESS(f'Accessible: {accessible}'))
        self.stdout.write(self.style.ERROR(f'Inaccessible: {inaccessible}'))
        self.stdout.write(self.style.WARNING(f'Invalid entries: {invalid}'))

        if options['fix']:
            self.stdout.write(self.style.SUCCESS(f'Fixed: {fixed}'))

        if options['clean']:
            self.stdout.write(self.style.SUCCESS(f'Cleaned: {cleaned}'))

        if inaccessible > 0 or invalid > 0:
            self.stdout.write(f'\nTroubleshooting tips:')
            if invalid > 0:
                self.stdout.write('• Use --clean to remove invalid entries like "No Photo"')
            if inaccessible > 0:
                self.stdout.write('• Ensure Google Drive files are shared publicly')
                self.stdout.write('• Check that sharing links have the correct format')
                self.stdout.write('• Verify files haven\'t been deleted or moved')
                self.stdout.write('• Try regenerating sharing links from Google Drive')
