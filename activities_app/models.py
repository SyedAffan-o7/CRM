from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

class ActivityLog(models.Model):
    ACTIVITY_TYPE_CHOICES = [
        ('call', 'Phone Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('note', 'Note'),
        ('task', 'Task'),
        ('stage_change', 'Stage Change'),
        ('status_change', 'Status Change'),
        ('reason_update', 'Reason Update'),
    ]

    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    subject = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    details = models.TextField(blank=True, null=True, help_text='Additional details about the activity')
    
    # Legacy foreign keys (kept for backward compatibility)
    contact = models.ForeignKey('customers_app.Contact', on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    lead = models.ForeignKey('leads_app.Lead', on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    deal = models.ForeignKey('deals_app.Deal', on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    
    # Generic foreign key for any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_date = models.DateTimeField(default=timezone.now)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.subject:
            return f"{self.get_activity_type_display()} - {self.subject}"
        return f"{self.get_activity_type_display()} on {self.activity_date.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def log_activity(cls, user, activity_type, content_object=None, **kwargs):
        """Helper method to create an activity log entry"""
        return cls.objects.create(
            user=user,
            activity_type=activity_type,
            content_object=content_object,
            **kwargs
        )

    class Meta:
        ordering = ['-activity_date']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
