from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications_app.models import Notification
from notifications_app.signals import send_followup_reminders, send_daily_digest
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send pending notifications and reminders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['reminders', 'digest', 'pending', 'all'],
            default='all',
            help='Type of notifications to send'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending'
        )

    def handle(self, *args, **options):
        notification_type = options['type']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No notifications will be sent'))
        
        try:
            if notification_type in ['reminders', 'all']:
                self.send_followup_reminders(dry_run)
            
            if notification_type in ['digest', 'all']:
                self.send_daily_digest(dry_run)
            
            if notification_type in ['pending', 'all']:
                self.send_pending_notifications(dry_run)
                
        except Exception as e:
            logger.error(f"Error in send_notifications command: {e}")
            self.stdout.write(
                self.style.ERROR(f'Error sending notifications: {e}')
            )

    def send_followup_reminders(self, dry_run=False):
        """Send follow-up reminder notifications"""
        self.stdout.write('Sending follow-up reminders...')
        
        if not dry_run:
            send_followup_reminders()
        else:
            from django.utils import timezone
            from datetime import timedelta
            from leads_app.models import FollowUp
            
            now = timezone.now()
            tomorrow = now + timedelta(days=1)
            
            upcoming = FollowUp.objects.filter(
                scheduled_date__date=tomorrow.date(),
                status='pending'
            ).count()
            
            overdue = FollowUp.objects.filter(
                scheduled_date__lt=now,
                status='pending'
            ).count()
            
            self.stdout.write(f'Would send {upcoming} reminder and {overdue} overdue notifications')

    def send_daily_digest(self, dry_run=False):
        """Send daily digest notifications"""
        self.stdout.write('Sending daily digest...')
        
        if not dry_run:
            send_daily_digest()
        else:
            from django.contrib.auth.models import User
            
            users_count = User.objects.filter(
                notification_preferences__daily_digest=True,
                is_active=True,
                email__isnull=False
            ).exclude(email='').count()
            
            self.stdout.write(f'Would send daily digest to {users_count} users')

    def send_pending_notifications(self, dry_run=False):
        """Send all pending notifications"""
        self.stdout.write('Sending pending notifications...')
        
        # Get notifications that are scheduled and not yet sent
        pending_notifications = Notification.objects.filter(
            status='PENDING',
            scheduled_for__lte=timezone.now()
        ).select_related('notification_type', 'recipient')
        
        sent_count = 0
        failed_count = 0
        
        for notification in pending_notifications:
            if dry_run:
                self.stdout.write(f'Would send: {notification.title} to {notification.recipient.username}')
                continue
            
            try:
                success = notification.send()
                if success:
                    sent_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Sent: {notification.title} to {notification.recipient.username}')
                    )
                else:
                    failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'Failed: {notification.title} to {notification.recipient.username}')
                    )
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending notification {notification.id}: {e}")
                self.stdout.write(
                    self.style.ERROR(f'Error sending {notification.title}: {e}')
                )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Sent {sent_count} notifications, {failed_count} failed')
            )
        else:
            self.stdout.write(f'Would send {pending_notifications.count()} pending notifications')
