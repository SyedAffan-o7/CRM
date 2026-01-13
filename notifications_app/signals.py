from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from leads_app.models import Lead, FollowUp
from customers_app.models import Contact
from accounts_app.models import UserProfile
from activities_app.models import ActivityLog
from .models import Notification, NotificationPreference
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """Create default notification preferences for new users"""
    if created:
        NotificationPreference.objects.get_or_create(user=instance)


@receiver(post_save, sender=Lead)
def handle_lead_notifications(sender, instance, created, **kwargs):
    """Handle lead-related notifications"""
    try:
        if created:
            # New lead created - notify assigned salesperson and managers
            recipients = []
            
            # Add assigned salesperson
            if instance.assigned_sales_person:
                recipients.append(instance.assigned_sales_person)
            
            # Add managers and admins
            managers = User.objects.filter(
                profile__role__name__in=['MANAGER', 'ADMIN', 'SUPERUSER'],
                is_active=True
            ).exclude(id__in=[r.id for r in recipients])
            recipients.extend(managers)
            
            # Create notifications
            for recipient in recipients:
                Notification.create_notification(
                    notification_type_name='NEW_LEAD',
                    recipient=recipient,
                    title=f'New Enquiry: {instance.contact_name}',
                    message=f'A new enquiry has been received from {instance.contact_name} ({instance.company_name or "No company"}). '
                           f'Products: {", ".join([p.name for p in instance.products_enquired.all()[:3]])}',
                    content_object=instance,
                    data={
                        'lead_id': instance.id,
                        'contact_name': instance.contact_name,
                        'phone_number': instance.phone_number,
                        'company_name': instance.company_name,
                        'created_by': instance.created_by.username if instance.created_by else None,
                    }
                )
        
        else:
            # Lead updated - check for important changes
            if hasattr(instance, '_original_enquiry_stage'):
                old_stage = instance._original_enquiry_stage
                new_stage = instance.enquiry_stage
                
                if old_stage != new_stage:
                    # Stage changed - notify relevant users
                    recipients = []
                    
                    if instance.assigned_sales_person:
                        recipients.append(instance.assigned_sales_person)
                    if instance.created_by and instance.created_by != instance.assigned_sales_person:
                        recipients.append(instance.created_by)
                    
                    # Add managers for important stages
                    if new_stage in ['won', 'lost', 'proforma_invoice_sent', 'invoice_sent']:
                        managers = User.objects.filter(
                            profile__role__name__in=['MANAGER', 'ADMIN', 'SUPERUSER'],
                            is_active=True
                        ).exclude(id__in=[r.id for r in recipients])
                        recipients.extend(managers)
                    
                    stage_display = dict(Lead.ENQUIRY_STAGE_CHOICES).get(new_stage, new_stage)
                    
                    for recipient in recipients:
                        Notification.create_notification(
                            notification_type_name='LEAD_STAGE_CHANGE',
                            recipient=recipient,
                            title=f'Enquiry Stage Updated: {instance.contact_name}',
                            message=f'Enquiry for {instance.contact_name} has moved to "{stage_display}" stage.',
                            content_object=instance,
                            data={
                                'lead_id': instance.id,
                                'old_stage': old_stage,
                                'new_stage': new_stage,
                                'stage_display': stage_display,
                            }
                        )
    
    except Exception as e:
        logger.error(f"Error in lead notification signal: {e}")


@receiver(post_save, sender=FollowUp)
def handle_followup_notifications(sender, instance, created, **kwargs):
    """Handle follow-up related notifications"""
    try:
        if created:
            # New follow-up created - notify assigned user if different from creator
            if instance.assigned_to and instance.assigned_to != instance.created_by:
                Notification.create_notification(
                    notification_type_name='FOLLOWUP_ASSIGNED',
                    recipient=instance.assigned_to,
                    title=f'New Follow-up Assigned: {instance.lead.contact_name}',
                    message=f'You have been assigned a follow-up for {instance.lead.contact_name} '
                           f'scheduled for {instance.scheduled_date.strftime("%B %d, %Y at %I:%M %p")}.',
                    content_object=instance,
                    data={
                        'followup_id': instance.id,
                        'lead_id': instance.lead.id,
                        'scheduled_date': instance.scheduled_date.isoformat(),
                        'assigned_by': instance.created_by.username if instance.created_by else None,
                    }
                )

            # NEW: Also create immediate reminder notification for the assigned user
            # This ensures users see notifications immediately when creating follow-ups
            if instance.assigned_to:
                # Check if it's due tomorrow or today
                now = timezone.now()
                tomorrow = now + timedelta(days=1)

                # Make sure we're comparing dates properly
                instance_date = timezone.make_aware(instance.scheduled_date) if timezone.is_naive(instance.scheduled_date) else instance.scheduled_date
                is_due_tomorrow = instance_date.date() == tomorrow.date()

                if is_due_tomorrow:
                    # Create immediate reminder notification
                    Notification.create_notification(
                        notification_type_name='FOLLOWUP_REMINDER',
                        recipient=instance.assigned_to,
                        title=f'Follow-up Reminder: {instance.lead.contact_name}',
                        message=f'You have a follow-up scheduled for tomorrow ({instance.scheduled_date.strftime("%B %d, %Y at %I:%M %p")}) '
                               f'with {instance.lead.contact_name}. Notes: {instance.notes or "No notes"}',
                        content_object=instance,
                        data={
                            'followup_id': instance.id,
                            'lead_id': instance.lead.id,
                            'scheduled_date': instance.scheduled_date.isoformat(),
                            'is_reminder': True,
                            'immediate': True,  # Mark as immediate notification
                        }
                    )
        
        # Check for status changes
        if hasattr(instance, '_original_status'):
            old_status = instance._original_status
            new_status = instance.status
            
            if old_status != new_status and new_status == 'completed':
                # Follow-up completed - notify creator and managers
                recipients = []
                
                if instance.created_by and instance.created_by != instance.assigned_to:
                    recipients.append(instance.created_by)
                
                # Notify managers for completed follow-ups
                managers = User.objects.filter(
                    profile__role__name__in=['MANAGER', 'ADMIN'],
                    is_active=True
                ).exclude(id__in=[r.id for r in recipients if r])
                recipients.extend(managers)
                
                for recipient in recipients:
                    Notification.create_notification(
                        notification_type_name='FOLLOWUP_COMPLETED',
                        recipient=recipient,
                        title=f'Follow-up Completed: {instance.lead.contact_name}',
                        message=f'Follow-up for {instance.lead.contact_name} has been marked as completed '
                               f'by {instance.assigned_to.get_full_name() or instance.assigned_to.username}.',
                        content_object=instance,
                        data={
                            'followup_id': instance.id,
                            'lead_id': instance.lead.id,
                            'completed_by': instance.assigned_to.username if instance.assigned_to else None,
                        }
                    )
    
    except Exception as e:
        logger.error(f"Error in followup notification signal: {e}")


@receiver(post_save, sender=UserProfile)
def handle_user_profile_notifications(sender, instance, created, **kwargs):
    """Handle user profile related notifications"""
    try:
        if created:
            # New user profile created - send welcome notification
            Notification.create_notification(
                notification_type_name='USER_WELCOME',
                recipient=instance.user,
                title='Welcome to AAA CRM System',
                message=f'Welcome {instance.user.get_full_name() or instance.user.username}! '
                       f'Your account has been set up with {instance.role.display_name if instance.role else "default"} permissions. '
                       f'You can now access the CRM system and manage your tasks.',
                content_object=instance,
                data={
                    'user_id': instance.user.id,
                    'role': instance.role.name if instance.role else None,
                    'role_display': instance.role.display_name if instance.role else None,
                }
            )
        
        else:
            # Check for role changes
            if hasattr(instance, '_original_role_id'):
                old_role_id = instance._original_role_id
                new_role_id = instance.role.id if instance.role else None
                
                if old_role_id != new_role_id:
                    # Role changed - notify user
                    old_role_name = "No Role"
                    new_role_name = instance.role.display_name if instance.role else "No Role"
                    
                    if old_role_id:
                        try:
                            from accounts_app.models import UserRole
                            old_role = UserRole.objects.get(id=old_role_id)
                            old_role_name = old_role.display_name
                        except UserRole.DoesNotExist:
                            pass
                    
                    Notification.create_notification(
                        notification_type_name='USER_ROLE_CHANGE',
                        recipient=instance.user,
                        title='Your Role Has Been Updated',
                        message=f'Your role has been changed from "{old_role_name}" to "{new_role_name}". '
                               f'Your access permissions may have changed. Please contact your administrator if you have questions.',
                        content_object=instance,
                        data={
                            'user_id': instance.user.id,
                            'old_role': old_role_name,
                            'new_role': new_role_name,
                        }
                    )
    
    except Exception as e:
        logger.error(f"Error in user profile notification signal: {e}")


# Helper function to send reminder notifications (called by management command)
def send_followup_reminders():
    """Send follow-up reminder notifications"""
    try:
        now = timezone.now()
        tomorrow = now + timedelta(days=1)
        
        # Get follow-ups due tomorrow
        upcoming_followups = FollowUp.objects.filter(
            scheduled_date__date=tomorrow.date(),
            status='pending'
        ).select_related('lead', 'assigned_to')
        
        # Get overdue follow-ups
        overdue_followups = FollowUp.objects.filter(
            scheduled_date__lt=now,
            status='pending'
        ).select_related('lead', 'assigned_to')
        
        # Send reminders for upcoming follow-ups
        for followup in upcoming_followups:
            if followup.assigned_to:
                Notification.create_notification(
                    notification_type_name='FOLLOWUP_REMINDER',
                    recipient=followup.assigned_to,
                    title=f'Follow-up Reminder: {followup.lead.contact_name}',
                    message=f'You have a follow-up scheduled for tomorrow ({followup.scheduled_date.strftime("%B %d, %Y at %I:%M %p")}) '
                           f'with {followup.lead.contact_name}. Notes: {followup.notes or "No notes"}',
                    content_object=followup,
                    data={
                        'followup_id': followup.id,
                        'lead_id': followup.lead.id,
                        'scheduled_date': followup.scheduled_date.isoformat(),
                        'is_reminder': True,
                    }
                )
        
        # Send overdue notifications
        for followup in overdue_followups:
            if followup.assigned_to:
                days_overdue = (now.date() - followup.scheduled_date.date()).days
                Notification.create_notification(
                    notification_type_name='FOLLOWUP_OVERDUE',
                    recipient=followup.assigned_to,
                    title=f'Overdue Follow-up: {followup.lead.contact_name}',
                    message=f'Your follow-up with {followup.lead.contact_name} is {days_overdue} day(s) overdue. '
                           f'Originally scheduled for {followup.scheduled_date.strftime("%B %d, %Y at %I:%M %p")}. '
                           f'Please update the status or reschedule.',
                    content_object=followup,
                    data={
                        'followup_id': followup.id,
                        'lead_id': followup.lead.id,
                        'scheduled_date': followup.scheduled_date.isoformat(),
                        'days_overdue': days_overdue,
                        'is_overdue': True,
                    }
                )
        
        logger.info(f"Sent {len(upcoming_followups)} reminder and {len(overdue_followups)} overdue notifications")
        
    except Exception as e:
        logger.error(f"Error sending follow-up reminders: {e}")


# Helper function to send daily digest
def send_daily_digest():
    """Send daily digest notifications"""
    try:
        from django.db.models import Count, Q
        
        # Get users who want daily digest
        users_with_digest = User.objects.filter(
            notification_preferences__daily_digest=True,
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        for user in users_with_digest:
            # Get user's data for the day
            today = timezone.now().date()
            
            # Get user's leads and follow-ups
            user_leads = Lead.objects.filter(
                Q(assigned_sales_person=user) | Q(created_by=user)
            )
            
            # Today's stats
            leads_created_today = user_leads.filter(created_date__date=today).count()
            followups_due_today = FollowUp.objects.filter(
                assigned_to=user,
                scheduled_date__date=today,
                status='pending'
            ).count()
            overdue_followups = FollowUp.objects.filter(
                assigned_to=user,
                scheduled_date__date__lt=today,
                status='pending'
            ).count()
            
            # Only send digest if there's something to report
            if leads_created_today > 0 or followups_due_today > 0 or overdue_followups > 0:
                message_parts = []
                
                if leads_created_today > 0:
                    message_parts.append(f"• {leads_created_today} new enquir{'y' if leads_created_today == 1 else 'ies'} created")
                
                if followups_due_today > 0:
                    message_parts.append(f"• {followups_due_today} follow-up{'s' if followups_due_today != 1 else ''} due today")
                
                if overdue_followups > 0:
                    message_parts.append(f"• {overdue_followups} overdue follow-up{'s' if overdue_followups != 1 else ''}")
                
                message = "Here's your daily CRM summary:\n\n" + "\n".join(message_parts)
                
                Notification.create_notification(
                    notification_type_name='DAILY_DIGEST',
                    recipient=user,
                    title=f'Daily CRM Summary - {today.strftime("%B %d, %Y")}',
                    message=message,
                    data={
                        'date': today.isoformat(),
                        'leads_created': leads_created_today,
                        'followups_due': followups_due_today,
                        'overdue_followups': overdue_followups,
                    }
                )
        
        logger.info(f"Sent daily digest to {len(users_with_digest)} users")
        
    except Exception as e:
        logger.error(f"Error sending daily digest: {e}")
