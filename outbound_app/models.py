from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta


class MessageTemplate(models.Model):
    """Pre-defined message templates for WhatsApp/Email"""
    TEMPLATE_TYPE_CHOICES = [
        ('WHATSAPP', 'WhatsApp'),
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES)
    subject = models.CharField(max_length=200, blank=True)  # For emails
    message = models.TextField(help_text="Use {customer_name}, {company_name} for personalization")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_templates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    class Meta:
        ordering = ['template_type', 'name']


class Campaign(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"


class OutboundActivity(models.Model):
    METHOD_CHOICES = [
        ('PHONE', 'Phone Call'),
        ('WHATSAPP', 'WhatsApp'),
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('MEETING', 'In-Person Meeting'),
        ('VIDEO_CALL', 'Video Call'),
        ('LINKEDIN', 'LinkedIn Message'),
        ('OTHER', 'Other'),
    ]

    NEXT_STEP_CHOICES = [
        ('NONE', 'None'),
        ('FOLLOW_UP', 'Schedule Follow-up'),
        ('SEND_CATALOGUE', 'Send Product Catalogue'),
        ('SEND_QUOTE', 'Send Quotation'),
        ('SEND_PROPOSAL', 'Send Proposal'),
        ('SCHEDULE_DEMO', 'Schedule Product Demo'),
        ('SCHEDULE_MEETING', 'Schedule Meeting'),
        ('CREATE_ENQUIRY', 'Create Enquiry'),
        ('CONVERT_LEAD', 'Convert to Lead'),
        ('CLOSE_WON', 'Mark as Won'),
        ('CLOSE_LOST', 'Mark as Lost'),
    ]

    OUTCOME_CHOICES = [
        ('POSITIVE', 'Positive Response'),
        ('NEUTRAL', 'Neutral Response'),
        ('NEGATIVE', 'Negative Response'),
        ('NO_RESPONSE', 'No Response'),
        ('CALLBACK_REQUESTED', 'Callback Requested'),
        ('NOT_INTERESTED', 'Not Interested'),
        ('INTERESTED', 'Showed Interest'),
        ('MEETING_SCHEDULED', 'Meeting Scheduled'),
    ]

    id = models.BigAutoField(primary_key=True)
    campaign = models.ForeignKey(
        'outbound_app.Campaign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outbound_activities"
    )
    contact = models.ForeignKey(
        'customers_app.Contact',
        to_field='phone_number',
        on_delete=models.CASCADE,
        related_name='outbound_activities'
    )
    lead = models.ForeignKey(
        'leads_app.Lead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='outbound_from'
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, blank=True)
    summary = models.TextField(blank=True, max_length=2000, help_text="Brief summary of the conversation")
    detailed_notes = models.TextField(blank=True, help_text="Detailed notes and observations")
    next_step = models.CharField(max_length=30, choices=NEXT_STEP_CHOICES, default='NONE')
    next_step_date = models.DateTimeField(null=True, blank=True)
    follow_up_reminder = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Call/meeting duration in minutes")
    template_used = models.ForeignKey(
        MessageTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outbound_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        contact_name = getattr(self.contact, 'full_name', 'Unknown')
        return f"{contact_name} — {self.get_method_display()} @ {self.created_at:%Y-%m-%d %H:%M}"
    
    @property
    def is_follow_up_due(self):
        """Check if follow-up reminder is due"""
        if not self.follow_up_reminder:
            return False
        return timezone.now() >= self.follow_up_reminder
    
    @property
    def days_since_contact(self):
        """Calculate days since this activity"""
        return (timezone.now().date() - self.created_at.date()).days
    
    def get_personalized_message(self, template):
        """Get personalized message using template"""
        if not template or not self.contact:
            return template.message if template else ""
        
        context = {
            'customer_name': self.contact.full_name,
            'company_name': getattr(getattr(self.contact, 'company', None), 'company_name', 'your company'),
        }
        
        try:
            return template.message.format(**context)
        except KeyError:
            return template.message

    class Meta:
        indexes = [
            models.Index(fields=['contact', 'created_at']),
        ]
        ordering = ['-created_at']
        verbose_name = "Outbound Activity"
        verbose_name_plural = "Outbound Activities"
