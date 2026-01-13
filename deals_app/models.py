from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Deal(models.Model):
    DEAL_STAGE_CHOICES = [
        ('prospecting', 'Prospecting'),
        ('qualification', 'Qualification'),
        ('proposal', 'Proposal'),
        ('negotiation', 'Negotiation'),
        ('closed_won', 'Closed Won'),
        ('closed_lost', 'Closed Lost'),
    ]

    deal_name = models.CharField(max_length=200)
    contact = models.ForeignKey('customers_app.Contact', on_delete=models.CASCADE, related_name='deals')
    account = models.ForeignKey('accounts_app.Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='deals')
    products_services = models.TextField(blank=True)
    deal_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deal_stage = models.CharField(max_length=20, choices=DEAL_STAGE_CHOICES, default='prospecting')
    expected_close_date = models.DateField(null=True, blank=True)
    probability_percent = models.IntegerField(default=50, help_text="Probability of closing (0-100)")
    sales_person_assigned = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_deals')
    reason_win_loss = models.TextField(blank=True, help_text="Reason for winning or losing the deal")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_deals')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.deal_name} - {self.contact.full_name if self.contact else 'No Contact'}"

    class Meta:
        ordering = ['-created_date']
