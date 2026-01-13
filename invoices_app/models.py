from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    contact = models.ForeignKey('customers_app.Contact', on_delete=models.PROTECT, related_name='invoices')
    lead = models.ForeignKey('leads_app.Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    invoice_number = models.CharField(max_length=20, unique=True, blank=True)
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(blank=True, null=True)
    currency = models.CharField(max_length=10, default='AED')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.invoice_number or f'Invoice {self.pk}'

    def save(self, *args, **kwargs):
        # Invoice number must be provided manually via form; no auto-generation.
        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self) -> str:
        return self.description

    def save(self, *args, **kwargs):
        subtotal = self.quantity * self.unit_price
        discount_amount = subtotal * (self.discount_percent / Decimal('100'))
        self.line_total = subtotal - discount_amount
        super().save(*args, **kwargs)
