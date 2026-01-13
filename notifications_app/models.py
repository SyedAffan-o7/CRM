from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class NotificationType(models.Model):
    """Defines different types of notifications"""
    CATEGORY_CHOICES = [
        ('FOLLOW_UP', 'Follow-up Reminders'),
        ('LEAD_MANAGEMENT', 'Lead Management'),
        ('USER_MANAGEMENT', 'User Management'),
        ('SYSTEM', 'System Notifications'),
        ('WORKFLOW', 'Workflow Updates'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    description = models.TextField(blank=True)
    email_template = models.CharField(max_length=200, blank=True, help_text="Email template file name")
    is_active = models.BooleanField(default=True)
    send_email = models.BooleanField(default=True)
    send_in_app = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    class Meta:
        ordering = ['category', 'name']


class NotificationPreference(models.Model):
    """User preferences for notifications"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_follow_ups = models.BooleanField(default=True, verbose_name="Follow-up Reminders")
    email_lead_changes = models.BooleanField(default=True, verbose_name="Lead Updates")
    email_assignments = models.BooleanField(default=True, verbose_name="New Assignments")
    email_user_changes = models.BooleanField(default=True, verbose_name="Account Changes")
    email_system_alerts = models.BooleanField(default=False, verbose_name="System Alerts")
    
    # In-app preferences
    app_follow_ups = models.BooleanField(default=True)
    app_lead_changes = models.BooleanField(default=True)
    app_assignments = models.BooleanField(default=True)
    app_user_changes = models.BooleanField(default=True)
    app_system_alerts = models.BooleanField(default=True)
    
    # Digest preferences
    daily_digest = models.BooleanField(default=True, verbose_name="Daily Summary Email")
    weekly_digest = models.BooleanField(default=False, verbose_name="Weekly Summary Email")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


class Notification(models.Model):
    """Individual notification instances"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('READ', 'Read'),
        ('FAILED', 'Failed'),
    ]
    
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    # Generic foreign key to link to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Email specific fields
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True)
    
    # In-app notification fields
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Scheduling
    scheduled_for = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    data = models.JSONField(default=dict, blank=True, help_text="Additional context data")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} -> {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if self.status != 'READ':
            self.status = 'READ'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])
    
    def send_email_notification(self):
        """Send email notification"""
        try:
            # Check user preferences
            prefs = getattr(self.recipient, 'notification_preferences', None)
            if not prefs:
                # Create default preferences
                prefs = NotificationPreference.objects.create(user=self.recipient)
            
            # Check if user wants email for this type
            category = self.notification_type.category
            should_send = True
            
            if category == 'FOLLOW_UP' and not prefs.email_follow_ups:
                should_send = False
            elif category == 'LEAD_MANAGEMENT' and not prefs.email_lead_changes:
                should_send = False
            elif category == 'USER_MANAGEMENT' and not prefs.email_user_changes:
                should_send = False
            elif category == 'SYSTEM' and not prefs.email_system_alerts:
                should_send = False
            
            if not should_send:
                logger.info(f"Email notification skipped for {self.recipient.username} - user preference")
                return False
            
            # Prepare email content
            subject = self.title
            
            # Use template if specified
            if self.notification_type.email_template:
                try:
                    html_message = render_to_string(
                        f'notifications_app/emails/{self.notification_type.email_template}',
                        {
                            'notification': self,
                            'recipient': self.recipient,
                            'content_object': self.content_object,
                            'data': self.data,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Template rendering failed: {e}, using plain message")
                    html_message = None
            else:
                html_message = None
            
            # Send email
            send_mail(
                subject=subject,
                message=self.message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@crm.com'),
                recipient_list=[self.recipient.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            self.email_sent = True
            self.email_sent_at = timezone.now()
            self.save(update_fields=['email_sent', 'email_sent_at'])
            
            logger.info(f"Email notification sent to {self.recipient.email}")
            return True
            
        except Exception as e:
            self.email_error = str(e)
            self.save(update_fields=['email_error'])
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def send(self):
        """Send the notification (email and/or in-app)"""
        success = True
        
        # Send email if enabled
        if self.notification_type.send_email and self.recipient.email:
            email_success = self.send_email_notification()
            if not email_success:
                success = False
        
        # Mark as sent for in-app
        if self.notification_type.send_in_app:
            self.status = 'SENT'
        else:
            self.status = 'READ'  # Skip in-app display
        
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
        
        return success
    
    @classmethod
    def create_notification(cls, notification_type_name, recipient, title, message, 
                          content_object=None, data=None, scheduled_for=None):
        """Helper method to create notifications"""
        try:
            notification_type = NotificationType.objects.get(name=notification_type_name)
        except NotificationType.DoesNotExist:
            logger.error(f"Notification type '{notification_type_name}' not found")
            return None
        
        notification = cls.objects.create(
            notification_type=notification_type,
            recipient=recipient,
            title=title,
            message=message,
            content_object=content_object,
            data=data or {},
            scheduled_for=scheduled_for or timezone.now(),
        )
        
        return notification
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['scheduled_for']),
            models.Index(fields=['notification_type', 'status']),
        ]


class NotificationLog(models.Model):
    """Log of all notification activities for auditing"""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50)  # 'created', 'sent', 'read', 'failed'
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.notification.title} - {self.action}"
    
    class Meta:
        ordering = ['-timestamp']
