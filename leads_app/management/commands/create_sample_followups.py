from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from leads_app.models import Lead, FollowUp
from datetime import timedelta
import random


class Command(BaseCommand):
    help = 'Create sample follow-ups for testing dashboard functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of sample follow-ups to create (default: 5)'
        )

    def handle(self, *args, **options):
        count = options['count']

        # Get a random user or create one if none exists
        try:
            user = User.objects.filter(is_active=True).first()
            if not user:
                user = User.objects.create_user(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123',
                    first_name='Test',
                    last_name='User'
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created test user: {user.username}')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating/getting user: {e}')
            )
            return

        # Get some leads or create sample ones if none exist
        leads = Lead.objects.all()[:10]  # Get up to 10 leads

        if not leads:
            self.stdout.write(
                self.style.WARNING('No leads found. Please create some leads first.')
            )
            return

        created_count = 0

        # Create overdue follow-ups (yesterday and before)
        for i in range(min(count // 3, len(leads))):
            lead = leads[i]
            try:
                follow_up = FollowUp.objects.create(
                    lead=lead,
                    scheduled_date=timezone.now() - timedelta(days=random.randint(1, 7)),
                    followup_type=random.choice(['call', 'email', 'meeting']),
                    notes=f"Sample overdue follow-up for {lead.contact_name}",
                    status='pending',  # Will be set to 'overdue' by the save method
                    created_by=user,
                    assigned_to=user
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created overdue follow-up: {follow_up}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating overdue follow-up: {e}')
                )

        # Create today's follow-ups
        remaining_count = count - created_count
        for i in range(min(remaining_count // 2, len(leads) - created_count)):
            lead = leads[created_count + i]
            try:
                follow_up = FollowUp.objects.create(
                    lead=lead,
                    scheduled_date=timezone.now() + timedelta(hours=random.randint(1, 8)),
                    followup_type=random.choice(['call', 'email', 'meeting']),
                    notes=f"Sample today's follow-up for {lead.contact_name}",
                    status='pending',
                    created_by=user,
                    assigned_to=user
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created today\'s follow-up: {follow_up}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating today\'s follow-up: {e}')
                )

        # Create upcoming follow-ups (tomorrow and later)
        remaining_count = count - created_count
        for i in range(min(remaining_count, len(leads) - created_count)):
            lead = leads[created_count + i]
            try:
                follow_up = FollowUp.objects.create(
                    lead=lead,
                    scheduled_date=timezone.now() + timedelta(days=random.randint(1, 7)),
                    followup_type=random.choice(['call', 'email', 'meeting']),
                    notes=f"Sample upcoming follow-up for {lead.contact_name}",
                    status='pending',
                    created_by=user,
                    assigned_to=user
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created upcoming follow-up: {follow_up}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating upcoming follow-up: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} sample follow-ups')
        )

        if created_count == 0:
            self.stdout.write(
                self.style.WARNING('No follow-ups were created. Please check that you have leads in the system.')
            )
