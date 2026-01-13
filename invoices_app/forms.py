from django import forms
from django.forms import inlineformset_factory
from django.db.models import Q

from customers_app.models import Contact
from leads_app.models import Lead

from .models import Invoice, InvoiceItem


class InvoiceForm(forms.ModelForm):
    contact = forms.ModelChoiceField(
        queryset=Contact.objects.all().order_by('full_name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Customer Name',
    )

    class Meta:
        model = Invoice
        fields = ['contact', 'lead', 'invoice_number', 'issue_date', 'due_date', 'currency', 'status', 'notes']
        widgets = {
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Manual invoice number entry; required
        if 'invoice_number' in self.fields:
            self.fields['invoice_number'].required = True
        self.fields['contact'].label_from_instance = lambda obj: obj.full_name or (obj.phone_number or '')

        # Limit the customer dropdown to only those contacts that still have at
        # least one open enquiry (enquiry_stage != 'invoice_sent'). We consider:
        # - leads explicitly linked via the FK, and
        # - orphan leads (no contact FK) matched by phone number or contact_name.
        # For now, show **all** contacts in the dropdown so every customer is selectable
        # when creating an invoice.
        contact_qs = Contact.objects.all()

        self.fields['contact'].queryset = contact_qs.distinct().order_by('full_name')
        # Remove default '---------" placeholder text
        self.fields['contact'].empty_label = ''

        # Related enquiry dropdown depends on selected contact
        self.fields['lead'].queryset = Lead.objects.none()
        self.fields['lead'].required = False
        self.fields['lead'].label = 'Related Enquiry'
        # Make Related Enquiry look like other controls and remove '---------' text
        self.fields['lead'].widget.attrs.setdefault('class', 'form-select')
        self.fields['lead'].empty_label = ''

        contact_id = None
        if 'contact' in self.data:
            try:
                contact_id = int(self.data.get('contact'))
            except (TypeError, ValueError):
                contact_id = None
        elif self.instance and self.instance.contact_id:
            contact_id = self.instance.contact_id

        if contact_id:
            try:
                contact = Contact.objects.get(pk=contact_id)
            except Contact.DoesNotExist:
                contact = None

            qs = Lead.objects.filter(contact_id=contact_id)

            if contact is not None:
                qs = Lead.objects.filter(
                    Q(contact_id=contact_id)
                    | Q(contact__isnull=True, phone_number=contact.phone_number)
                    | Q(contact__isnull=True, contact_name__iexact=contact.full_name)
                )

            # Only show enquiries that are not yet completed (exclude 'invoice_sent').
            qs = qs.exclude(enquiry_stage='invoice_sent')

            if self.instance and self.instance.lead_id:
                qs = qs | Lead.objects.filter(pk=self.instance.lead_id)

            self.fields['lead'].queryset = qs.order_by('-created_date').distinct()


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['description', 'quantity', 'unit_price', 'discount_percent']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow rows to be completely empty; we'll enforce requirements in clean()
        for name in ['description', 'quantity', 'unit_price', 'discount_percent']:
            if name in self.fields:
                self.fields[name].required = False

    def clean(self):
        cleaned_data = super().clean()
        desc = cleaned_data.get('description')
        qty = cleaned_data.get('quantity')
        price = cleaned_data.get('unit_price')
        discount = cleaned_data.get('discount_percent')

        # If the row has no core data (description/quantity/price), treat as empty
        # regardless of discount value (it might be 0 by default).
        if not desc and qty in (None, '') and price in (None, ''):
            cleaned_data['DELETE'] = True
            return cleaned_data

        # If any data is entered, enforce required fields
        errors = {}
        if not desc:
            errors['description'] = 'This field is required.'
        if qty in (None, ''):
            errors['quantity'] = 'This field is required.'
        if price in (None, ''):
            errors['unit_price'] = 'This field is required.'

        # Default discount to 0 if left empty
        if discount in (None, ''):
            cleaned_data['discount_percent'] = 0

        if errors:
            raise forms.ValidationError(errors)

        return cleaned_data


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True,
)
