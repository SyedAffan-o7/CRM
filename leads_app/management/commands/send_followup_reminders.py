from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from leads_app.models import FollowUp

class Command(BaseCommand):
    help = 'Sends email reminders for due and overdue follow-ups'

    def handle(self, *args, **options):
        # Get all pending follow-ups
        followups = FollowUp.objects.filter(status='pending')
        
        now = timezone.now()
        today = now.date()
        
        for followup in followups:
            # Check if follow-up is due today or overdue
            if followup.scheduled_date.date() <= today:
                # Send email to assigned user
                subject = f'Follow-up Reminder: {followup.lead.contact_name}'
                context = {
                    'followup': followup,
                    'now': now
                }
                message = render_to_string('emails/followup_reminder.txt', context)
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [followup.assigned_to.email],
                    fail_silently=False
                )
                self.stdout.write(f'Sent reminder for follow-up #{followup.id} to {followup.assigned_to.email}')
        self.stdout.write('Successfully sent follow-up reminders')
