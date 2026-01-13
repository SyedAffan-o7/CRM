from django.core.management.base import BaseCommand
from notifications_app.models import NotificationType


class Command(BaseCommand):
    help = 'Set up default notification types'

    def handle(self, *args, **options):
        notification_types = [
            # Follow-up notifications
            {
                'name': 'FOLLOWUP_REMINDER',
                'category': 'FOLLOW_UP',
                'priority': 'HIGH',
                'description': 'Reminder for upcoming follow-ups',
                'email_template': 'followup_reminder.html',
            },
            {
                'name': 'FOLLOWUP_OVERDUE',
                'category': 'FOLLOW_UP',
                'priority': 'URGENT',
                'description': 'Notification for overdue follow-ups',
                'email_template': 'followup_overdue.html',
            },
            {
                'name': 'FOLLOWUP_ASSIGNED',
                'category': 'FOLLOW_UP',
                'priority': 'MEDIUM',
                'description': 'Notification when a follow-up is assigned',
                'email_template': 'followup_assigned.html',
            },
            {
                'name': 'FOLLOWUP_COMPLETED',
                'category': 'FOLLOW_UP',
                'priority': 'LOW',
                'description': 'Notification when a follow-up is completed',
                'email_template': 'followup_completed.html',
            },
            
            # Lead management notifications
            {
                'name': 'NEW_LEAD',
                'category': 'LEAD_MANAGEMENT',
                'priority': 'HIGH',
                'description': 'Notification for new lead creation',
                'email_template': 'new_lead.html',
            },
            {
                'name': 'LEAD_STAGE_CHANGE',
                'category': 'LEAD_MANAGEMENT',
                'priority': 'MEDIUM',
                'description': 'Notification for lead stage changes',
                'email_template': 'lead_stage_change.html',
            },
            {
                'name': 'LEAD_ASSIGNMENT',
                'category': 'LEAD_MANAGEMENT',
                'priority': 'HIGH',
                'description': 'Notification for lead assignment changes',
                'email_template': 'lead_assignment.html',
            },
            {
                'name': 'LEAD_STATUS_CHANGE',
                'category': 'LEAD_MANAGEMENT',
                'priority': 'MEDIUM',
                'description': 'Notification for lead status changes',
                'email_template': 'lead_status_change.html',
            },
            
            # User management notifications
            {
                'name': 'USER_WELCOME',
                'category': 'USER_MANAGEMENT',
                'priority': 'MEDIUM',
                'description': 'Welcome notification for new users',
                'email_template': 'user_welcome.html',
            },
            {
                'name': 'USER_ROLE_CHANGE',
                'category': 'USER_MANAGEMENT',
                'priority': 'HIGH',
                'description': 'Notification for user role changes',
                'email_template': 'user_role_change.html',
            },
            {
                'name': 'USER_ACCOUNT_ACTIVATED',
                'category': 'USER_MANAGEMENT',
                'priority': 'MEDIUM',
                'description': 'Notification when user account is activated',
                'email_template': 'user_activated.html',
            },
            {
                'name': 'USER_ACCOUNT_DEACTIVATED',
                'category': 'USER_MANAGEMENT',
                'priority': 'HIGH',
                'description': 'Notification when user account is deactivated',
                'email_template': 'user_deactivated.html',
            },
            
            # System notifications
            {
                'name': 'DAILY_DIGEST',
                'category': 'SYSTEM',
                'priority': 'LOW',
                'description': 'Daily summary digest',
                'email_template': 'daily_digest.html',
            },
            {
                'name': 'WEEKLY_DIGEST',
                'category': 'SYSTEM',
                'priority': 'LOW',
                'description': 'Weekly summary digest',
                'email_template': 'weekly_digest.html',
            },
            {
                'name': 'SYSTEM_ALERT',
                'category': 'SYSTEM',
                'priority': 'URGENT',
                'description': 'System alerts and errors',
                'email_template': 'system_alert.html',
            },
            
            # Workflow notifications
            {
                'name': 'ENQUIRY_ACCEPTED',
                'category': 'WORKFLOW',
                'priority': 'MEDIUM',
                'description': 'Notification when enquiry is accepted',
                'email_template': 'enquiry_accepted.html',
            },
            {
                'name': 'ENQUIRY_REJECTED',
                'category': 'WORKFLOW',
                'priority': 'MEDIUM',
                'description': 'Notification when enquiry is rejected',
                'email_template': 'enquiry_rejected.html',
            },
            {
                'name': 'CONTACT_AUTO_CREATED',
                'category': 'WORKFLOW',
                'priority': 'LOW',
                'description': 'Notification when contact is auto-created',
                'email_template': 'contact_auto_created.html',
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for nt_data in notification_types:
            notification_type, created = NotificationType.objects.get_or_create(
                name=nt_data['name'],
                defaults=nt_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created notification type: {nt_data["name"]}')
                )
            else:
                # Update existing notification type
                for key, value in nt_data.items():
                    if key != 'name':
                        setattr(notification_type, key, value)
                notification_type.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated notification type: {nt_data["name"]}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up notification types: {created_count} created, {updated_count} updated'
            )
        )
