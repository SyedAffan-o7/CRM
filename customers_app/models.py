from django.db import models
from django.contrib.auth.models import User


class Contact(models.Model):
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, unique=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    company = models.ForeignKey('accounts_app.Account', to_field='phone_number', on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts')
    role_position = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_contacts')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    # Outbound-related fields (appended)
    last_contacted = models.DateTimeField(null=True, blank=True)

    OUTBOUND_STATUS_CHOICES = [
        ('NOT_CONTACTED', 'Not Contacted'),
        ('CONTACTED', 'Contacted'),
        ('CONVERTED', 'Converted'),
    ]
    outbound_status = models.CharField(max_length=20, choices=OUTBOUND_STATUS_CHOICES, default='NOT_CONTACTED')
    manual_status_override = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.phone_number}"

    class Meta:
        ordering = ['full_name']
