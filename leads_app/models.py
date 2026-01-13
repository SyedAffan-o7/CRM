from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
# Use string-based FKs to avoid circular import issues


class Reason(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        


class Product(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        


class LeadSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        


class Lead(models.Model):
    STATUS_CHOICES = [
        ('fulfilled', 'Fulfilled'),
        ('not_fulfilled', 'Not Fulfilled'),
    ]

    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    ENQUIRY_STAGE_CHOICES = [
        ('enquiry_received', 'Enquiry Received'),
        ('quotation_sent', 'Quotation Sent'),
        ('negotiation', 'Negotiation'),
        ('proforma_invoice_sent', 'Proforma Invoice Sent (PI Sent)'),
        ('invoice_sent', 'Invoice Sent'),
        ('lost', 'Lost'),
    ]

    ASSIGNMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    contact_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    country = models.CharField(max_length=100, blank=True, help_text="Auto-detected from phone number")
    company_name = models.CharField(max_length=200, blank=True)
    contact = models.ForeignKey('customers_app.Contact', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    products_enquired = models.ManyToManyField(Product, blank=True, related_name='leads')
    lead_source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    lead_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_fulfilled')
    enquiry_stage = models.CharField(max_length=30, choices=ENQUIRY_STAGE_CHOICES, default='enquiry_received')
    is_locked = models.BooleanField(default=False, help_text="Prevents stage changes after fulfillment")
    reason = models.ForeignKey(Reason, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    images = models.ImageField(upload_to='enquiry_images/', blank=True, null=True)
    image_url = models.URLField(blank=True, null=True, help_text="Google Drive image URL for the enquiry")
    next_action = models.CharField(max_length=200, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    notes = models.TextField(blank=True)
    assigned_sales_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    assignment_status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS_CHOICES, null=True, blank=True, default=None)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_leads')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    category = models.ForeignKey('products.Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    subcategory = models.ForeignKey('products.Subcategory', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    proforma_invoice_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='Proforma Invoice Number')
    invoice_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='Invoice Number')
    # Staging flag: when True, enquiry appears under Pending tab until accepted
    is_pending_review = models.BooleanField(default=False)

    def clean(self):
        super().clean()

        # Check if this is a stage change that would trigger fulfillment
        if (self.enquiry_stage == 'invoice_sent' and
            self.invoice_number and
            self.invoice_number.strip() and
            self.lead_status != 'fulfilled'):
            # Auto-set status to fulfilled when stage is invoice_sent and invoice is provided
            self.lead_status = 'fulfilled'
            # Lock the lead to prevent further stage changes
            self.is_locked = True

        # Validate locked leads cannot have stage changes
        if self.is_locked and hasattr(self, '_original_enquiry_stage'):
            if self._original_enquiry_stage != self.enquiry_stage:
                raise ValidationError({'enquiry_stage': "This enquiry is locked and cannot be modified after fulfillment."})

        if self.enquiry_stage == 'proforma_invoice_sent' and not self.proforma_invoice_number:
            raise ValidationError({'proforma_invoice_number': "Proforma Invoice Number is required when stage is 'Proforma Invoice Sent'."})

        # Check if trying to set invoice-related stages without PI first
        if self.enquiry_stage in ['invoice_sent'] and not self.proforma_invoice_number:
            raise ValidationError({'enquiry_stage': "Enter PI first. Invoice Number can only be entered after Proforma Invoice (PI) is created."})

        if self.enquiry_stage in ['invoice_sent'] and not self.invoice_number:
            raise ValidationError({'invoice_number': "Invoice Number is required when stage is 'Invoice Sent'."})
        if self.enquiry_stage in ['invoice_sent'] and self.invoice_number and len(self.invoice_number) != 10:
            raise ValidationError({'invoice_number': "Invoice Number must be 10 characters long when stage is 'Invoice Sent'."})
        if self.enquiry_stage in ['invoice_sent'] and self.invoice_number and not self.invoice_number.startswith('INV'):
            raise ValidationError({'invoice_number': "Invoice Number must start with 'INV' when stage is 'Invoice Sent'."})

    def save(self, *args, **kwargs):
        # Track original values for notifications
        if self.pk:
            try:
                original = Lead.objects.get(pk=self.pk)
                self._original_enquiry_stage = original.enquiry_stage
                self._original_lead_status = original.lead_status
                self._original_assigned_sales_person_id = original.assigned_sales_person_id
            except Lead.DoesNotExist:
                self._original_enquiry_stage = None
                self._original_lead_status = None
                self._original_assigned_sales_person_id = None
        else:
            self._original_enquiry_stage = None
            self._original_lead_status = None
            self._original_assigned_sales_person_id = None

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_date']
        


class LeadProduct(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='lead_products')
    category = models.ForeignKey('products.Category', on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey('products.Subcategory', on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to='lead_product_images/', blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1, help_text="Quantity of the product")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Price per unit")
    size = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    ankle = models.CharField(max_length=100, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)
    people = models.CharField(max_length=100, blank=True, null=True, help_text="Capacity / number of people for first aid kits or similar items")
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_date']
        

    def __str__(self):
        return f"{self.lead.contact_name} - {self.category.name if self.category else 'No Category'}"


class FollowUp(models.Model):
    """
    Tracks follow-up actions for leads/enquiries
    """
    FOLLOWUP_TYPE_CHOICES = [
        ('call', 'Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='follow_ups')
    scheduled_date = models.DateTimeField(help_text="When the follow-up should occur")
    followup_type = models.CharField(max_length=50, choices=FOLLOWUP_TYPE_CHOICES, default='call')
    notes = models.TextField(blank=True, help_text="Details about the follow-up")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    completed_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_followups',
        help_text="User who created this follow-up"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_followups',
        help_text="User responsible for this follow-up"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_date']
        verbose_name = 'Follow-up'
        verbose_name_plural = 'Follow-ups'
        

    def __str__(self):
        return f"Follow-up for {self.lead.contact_name} on {self.scheduled_date}"
    
    def save(self, *args, **kwargs):
        # Track original values for notifications
        if self.pk:
            try:
                original = FollowUp.objects.get(pk=self.pk)
                self._original_status = original.status
                self._original_assigned_to_id = original.assigned_to_id
            except FollowUp.DoesNotExist:
                self._original_status = None
                self._original_assigned_to_id = None
        else:
            self._original_status = None
            self._original_assigned_to_id = None
        
        # Update status based on dates
        if self.completed_date:
            self.status = 'completed'
        elif self.scheduled_date:
            # Fix timezone comparison - make both sides timezone-aware or naive
            now = timezone.now()
            scheduled_aware = timezone.make_aware(self.scheduled_date) if timezone.is_naive(self.scheduled_date) else self.scheduled_date

            if scheduled_aware < now and self.status != 'completed':
                self.status = 'overdue'
        
        # If this is a new follow-up and no assigned_to is set, default to created_by
        if not self.pk and self.created_by and not self.assigned_to:
            self.assigned_to = self.created_by
            
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        if self.status != 'pending' or not self.scheduled_date:
            return False
        now = timezone.now()
        scheduled_aware = timezone.make_aware(self.scheduled_date) if timezone.is_naive(self.scheduled_date) else self.scheduled_date
        return now > scheduled_aware

    @property
    def is_due_today(self):
        if self.status != 'pending' or not self.scheduled_date:
            return False
        today = timezone.now().date()
        scheduled_aware = timezone.make_aware(self.scheduled_date) if timezone.is_naive(self.scheduled_date) else self.scheduled_date
        return scheduled_aware.date() == today

    @property
    def is_upcoming(self):
        if self.status != 'pending' or not self.scheduled_date:
            return False
        now = timezone.now()
        scheduled_aware = timezone.make_aware(self.scheduled_date) if timezone.is_naive(self.scheduled_date) else self.scheduled_date
        return scheduled_aware > now

    def mark_completed(self, commit=True):
        self.status = 'completed'
        self.completed_date = timezone.now()
        if commit:
            self.save()

    def send_reminder(self):
        # Add logic to send reminder
        pass

    def assign_to(self, user):
        self.assigned_to = user
        self.save()

    def update_notes(self, notes):
        self.notes = notes
        self.save()
