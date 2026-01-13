from django.core.management.base import BaseCommand
from django.db import connection, connections
from customers_app.models import Contact
from outbound_app.models import Campaign, OutboundActivity


class Command(BaseCommand):
    help = 'Fix database connection issues and create sample data if needed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-sample',
            action='store_true',
            help='Create sample contacts and campaigns if none exist',
        )

    def handle(self, *args, **options):
        self.stdout.write('Fixing database connections...')
        
        # Close all connections
        for conn in connections.all():
            conn.close()
        
        # Test connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.stdout.write(
                    self.style.SUCCESS('Database connection is working!')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Database connection failed: {e}')
            )
            return

        # Check if we have contacts
        contact_count = Contact.objects.count()
        campaign_count = Campaign.objects.count()
        
        self.stdout.write(f'Found {contact_count} contacts and {campaign_count} campaigns')
        
        if options['create_sample'] and contact_count == 0:
            self.stdout.write('Creating sample contacts...')
            self.create_sample_contacts()
            
        if options['create_sample'] and campaign_count == 0:
            self.stdout.write('Creating sample campaigns...')
            self.create_sample_campaigns()

    def create_sample_contacts(self):
        """Create sample contacts for testing"""
        sample_contacts = [
            {
                'full_name': 'John Smith',
                'phone_number': '+1234567890',
                'email': 'john@example.com',
                'outbound_status': 'NOT_CONTACTED'
            },
            {
                'full_name': 'Sarah Johnson',
                'phone_number': '+1234567891',
                'email': 'sarah@techcorp.com',
                'outbound_status': 'NOT_CONTACTED'
            },
            {
                'full_name': 'Mike Wilson',
                'phone_number': '+1234567892',
                'email': 'mike@business.com',
                'outbound_status': 'CONTACTED'
            }
        ]
        
        for contact_data in sample_contacts:
            contact, created = Contact.objects.get_or_create(
                phone_number=contact_data['phone_number'],
                defaults=contact_data
            )
            if created:
                self.stdout.write(f'Created contact: {contact.full_name}')

    def create_sample_campaigns(self):
        """Create sample campaigns for testing"""
        sample_campaigns = [
            {
                'name': 'Q4 Sales Push',
                'description': 'End of year sales campaign',
                'is_active': True
            },
            {
                'name': 'New Product Launch',
                'description': 'Promoting our latest product',
                'is_active': True
            }
        ]
        
        for campaign_data in sample_campaigns:
            campaign, created = Campaign.objects.get_or_create(
                name=campaign_data['name'],
                defaults=campaign_data
            )
            if created:
                self.stdout.write(f'Created campaign: {campaign.name}')
