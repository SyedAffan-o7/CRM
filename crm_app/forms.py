from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from accounts_app.models import Account
from customers_app.models import Contact
from deals_app.models import Deal
from activities_app.models import ActivityLog
from leads_app.models import Product, Lead, Reason, LeadSource
from products.models import Category, Subcategory


class LeadForm(forms.ModelForm):
    invoice_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    invoice_amount = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    invoice_status = forms.ChoiceField(required=False, choices=[('pending', 'Pending'), ('paid', 'Paid')], widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Lead
        fields = [
            'contact_name', 'phone_number', 'country', 'company_name', 'category', 'subcategory',
            'lead_source', 'enquiry_stage', 'proforma_invoice_number', 'invoice_number', 'invoice_date', 'invoice_amount', 'invoice_status',
            'images', 'next_action', 'notes', 'assigned_sales_person'
        ]
        widgets = {
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'country': forms.HiddenInput(),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter company name'}),
            'category': forms.Select(attrs={'class': 'form-control', 'id': 'id_category'}),
            'subcategory': forms.Select(attrs={'class': 'form-control', 'id': 'id_subcategory'}),
            'enquiry_stage': forms.Select(attrs={'class': 'form-control', 'onchange': 'toggleInvoiceFields()'}),
            'proforma_invoice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PI Number', 'data-stage': 'proforma_invoice_sent'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Invoice Number', 'data-stage': 'invoice_made,invoice_sent'}),
            'images': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'next_action': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Next action required'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes'}),
            'assigned_sales_person': forms.Select(attrs={'class': 'form-control'}),
        }
    
    lead_source = forms.ModelChoiceField(
        queryset=LeadSource.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        empty_label="Select Lead Source"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['subcategory'].queryset = Subcategory.objects.none()
        self.fields['subcategory'].empty_label = "Select Subcategory"
        
        # Handle assigned_sales_person field based on user permissions
        if self.user and not self.user.is_superuser:
            # For non-superusers, auto-assign to themselves and hide the field
            self.fields['assigned_sales_person'].initial = self.user
            self.fields['assigned_sales_person'].widget = forms.HiddenInput()
            self.fields['assigned_sales_person'].required = False
        else:
            # For superusers/admins, show the full dropdown
            self.fields['assigned_sales_person'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
            self.fields['assigned_sales_person'].empty_label = "Select Sales Person"
            self.fields['assigned_sales_person'].required = True
        
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['subcategory'].queryset = Subcategory.objects.filter(category_id=category_id, is_active=True)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.category:
            self.fields['subcategory'].queryset = self.instance.category.subcategories.filter(is_active=True)

    def clean_phone_number(self):
        """Prevent duplicate enquiries for the same phone number."""
        phone = self.cleaned_data.get('phone_number')
        if not phone:
            return phone
        # Local import to avoid potential circular imports at module load
        from leads_app.models import Lead as LeadModel
        qs = LeadModel.objects.filter(phone_number=phone)
        # If editing, exclude the current instance
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("An enquiry with this phone number already exists.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        enquiry_stage = cleaned_data.get('enquiry_stage')
        
        if enquiry_stage == 'proforma_invoice_sent' and not cleaned_data.get('proforma_invoice_number'):
            self.add_error('proforma_invoice_number', "Proforma Invoice Number is required when stage is 'Proforma Invoice Sent'.")
        
        if enquiry_stage in ['invoice_sent'] and not cleaned_data.get('invoice_number'):
            self.add_error('invoice_number', "Invoice Number is required when stage is 'Invoice Sent'.")
        
        return cleaned_data


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['full_name', 'phone_number', 'whatsapp_number', 'company', 
                 'role_position', 'address', 'notes']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'WhatsApp number'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'role_position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Role/Position'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes'}),
        }


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['company_name', 'primary_contact', 'phone_number', 'address', 
                 'industry_type', 'account_status', 'notes']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter company name'}),
            'primary_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primary contact person'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Company address'}),
            'industry_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Industry type'}),
            'account_status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes'}),
        }


class DealForm(forms.ModelForm):
    class Meta:
        model = Deal
        fields = ['deal_name', 'contact', 'account', 'products_services', 'deal_value', 
                 'deal_stage', 'expected_close_date', 'probability_percent', 'sales_person_assigned', 
                 'reason_win_loss', 'notes']
        widgets = {
            'deal_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter deal name'}),
            'contact': forms.Select(attrs={'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-control', 'data-placeholder': 'Select account (optional)'}),
            'products_services': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Products/Services'}),
            'deal_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Deal value'}),
            'deal_stage': forms.Select(attrs={'class': 'form-control'}),
            'expected_close_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'probability_percent': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'sales_person_assigned': forms.Select(attrs={'class': 'form-control'}),
            'reason_win_loss': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for win/loss'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes'}),
        }


class ActivityLogForm(forms.ModelForm):
    class Meta:
        model = ActivityLog
        fields = ['activity_type', 'subject', 'description', 'contact', 'lead', 'deal', 'activity_date']
        widgets = {
            'activity_type': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Activity subject'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Activity description'}),
            'contact': forms.Select(attrs={'class': 'form-control'}),
            'lead': forms.Select(attrs={'class': 'form-control'}),
            'deal': forms.Select(attrs={'class': 'form-control'}),
            'activity_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
