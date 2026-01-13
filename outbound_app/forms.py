from django import forms
from django.db import connection
from .models import OutboundActivity, Campaign
from customers_app.models import Contact
from leads_app.models import Lead

# Forms for outbound_app will be added here.

class OutboundActivityForm(forms.ModelForm):
    # Ensure contact uses phone_number as the submitted value to match FK to_field
    contact = forms.ModelChoiceField(
        queryset=Contact.objects.none(),
        to_field_name='phone_number',
        widget=forms.Select(attrs={'class': 'form-select', 'required': True})
    )
    
    # Restrict method to only WhatsApp and Call
    method = forms.ChoiceField(
        choices=[('WHATSAPP', 'WhatsApp'), ('PHONE', 'Phone Call')],
        widget=forms.Select(attrs={'class': 'form-select', 'required': True})
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Handle database connection issues by refreshing queries
        try:
            # Close any stale or unusable connections (works across DB backends)
            try:
                connection.close_if_unusable_or_obsolete()
            except Exception:
                # Fallback for older backends; avoid attribute errors on sqlite
                try:
                    if connection.connection and hasattr(connection.connection, 'closed') and connection.connection.closed:
                        connection.close()
                except Exception:
                    pass
            
            # Set up querysets with fresh connections
            self.fields['contact'].queryset = Contact.objects.all().order_by('full_name')
            
            # Make fields optional except contact and method
            self.fields['outcome'].required = False
            self.fields['next_step'].required = False
            self.fields['next_step_date'].required = False
            self.fields['follow_up_reminder'].required = False
            
            # Add empty option for optional fields (already optional by required=False above)
            
        except Exception as e:
            # If there's still a database issue, set empty querysets
            self.fields['contact'].queryset = Contact.objects.none()
            
            # Add a help text to inform user about the issue
            self.fields['contact'].help_text = "Database connection issue. Please refresh the page or contact admin."

    # Standard ModelForm save - no custom logic needed since FK is now working

    class Meta:
        model = OutboundActivity
        fields = [
            'contact',
            'method',
            'outcome',
            'summary',
            'next_step',
            'next_step_date',
            'follow_up_reminder',
        ]
        widgets = {
            'contact': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'outcome': forms.Select(attrs={'class': 'form-select'}),
            'summary': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Summary of conversation'}),
            'next_step': forms.Select(attrs={'class': 'form-select'}),
            'next_step_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'follow_up_reminder': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }


class SimpleOutboundActivityForm(forms.Form):
    """Simplified form that doesn't rely on database relationships"""
    
    contact_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact name'})
    )
    contact_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'})
    )
    contact_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'})
    )
    
    method = forms.ChoiceField(
        choices=[('WHATSAPP', 'WhatsApp'), ('PHONE', 'Phone Call')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    outcome = forms.ChoiceField(
        choices=OutboundActivity.OUTCOME_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    summary = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Summary of conversation'})
    )
    next_step = forms.ChoiceField(
        choices=OutboundActivity.NEXT_STEP_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    next_step_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )
    follow_up_reminder = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )
    
    def save(self, user=None):
        """Create contact and outbound activity from form data (robust for FK to to_field)."""
        from django.db import IntegrityError
        # Normalize inputs
        phone = (self.cleaned_data['contact_phone'] or '').strip()
        name = (self.cleaned_data['contact_name'] or '').strip()
        email = (self.cleaned_data.get('contact_email') or '').strip()

        # Get or create contact and ensure saved
        contact, _ = Contact.objects.get_or_create(
            phone_number=phone,
            defaults={
                'full_name': name,
                'email': email,
                'outbound_status': 'NOT_CONTACTED'
            }
        )
        # Ensure contact is persisted
        if not getattr(contact, 'phone_number', None):
            contact.phone_number = phone
        if not getattr(contact, 'full_name', None):
            contact.full_name = name
        contact.save()

        # Create outbound activity — assign contact_id explicitly (to_field='phone_number')
        try:
            activity = OutboundActivity.objects.create(
                contact_id=contact.phone_number,
                method=self.cleaned_data['method'],
                outcome=self.cleaned_data.get('outcome', ''),
                summary=self.cleaned_data.get('summary', ''),
                next_step=self.cleaned_data.get('next_step', 'NONE'),
                next_step_date=self.cleaned_data.get('next_step_date'),
                follow_up_reminder=self.cleaned_data.get('follow_up_reminder'),
                created_by=user if getattr(user, 'is_authenticated', False) else None,
            )
        except IntegrityError as e:
            # Surface a clean error explaining likely cause
            raise IntegrityError(f"Failed to save activity due to data integrity issue (FK to contact). Ensure phone '{phone}' is valid.") from e

        # Update contact status after successful activity
        if contact.outbound_status != 'CONTACTED':
            contact.outbound_status = 'CONTACTED'
            contact.save(update_fields=['outbound_status'])

        return activity
