from django import forms
from django.utils import timezone
from django.forms import ModelForm
from .models import FollowUp, Lead
from django.db.models import Q
from django.contrib.auth.models import User

class FollowUpForm(ModelForm):
    """
    Form for creating and updating follow-ups
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.lead = kwargs.pop('lead', None)
        super().__init__(*args, **kwargs)
        
        # Set default scheduled date to 1 hour from now
        if not self.instance.pk:
            self.fields['scheduled_date'].initial = timezone.now() + timezone.timedelta(hours=1)
        
        # If this is an existing follow-up, don't allow changing the lead
        if self.instance and self.instance.pk:
            self.fields['lead'].disabled = True
        
        # If lead is provided, set it as initial value and make the field hidden
        if self.lead:
            self.fields['lead'].initial = self.lead
            self.fields['lead'].widget = forms.HiddenInput()
        
        # Set the current user as the default assigned_to if not set
        if self.request and not self.instance.pk and 'assigned_to' in self.fields:
            self.fields['assigned_to'].initial = self.request.user
    
    class Meta:
        model = FollowUp
        fields = ['lead', 'scheduled_date', 'followup_type', 'notes', 'assigned_to']
        widgets = {
            'scheduled_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control datetimepicker-input',
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'followup_type': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Enter follow-up details...'
            }),
        }
    
    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data.get('scheduled_date')
        # Only enforce future date when status is pending (new follow-ups are pending by default)
        status = getattr(self.instance, 'status', 'pending')
        if status == 'pending' and scheduled_date and scheduled_date < timezone.now():
            raise forms.ValidationError("Scheduled date cannot be in the past for a pending follow-up.")
        return scheduled_date
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set created_by to the current user if this is a new follow-up
        if not instance.pk and self.request:
            instance.created_by = self.request.user
        
        # If no assigned_to is set, default to the current user
        if not instance.assigned_to and self.request:
            instance.assigned_to = self.request.user
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance


class FollowUpStatusForm(forms.ModelForm):
    """
    Simple form for updating follow-up status
    """
    class Meta:
        model = FollowUp
        fields = ['status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Add any additional notes...'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show completed status if not already completed
        if self.instance and self.instance.status == 'completed':
            self.fields['status'].choices = [
                ('completed', 'Completed')
            ]
        else:
            self.fields['status'].choices = [
                ('pending', 'Pending'),
                ('completed', 'Mark as Completed'),
                ('overdue', 'Mark as Overdue')
            ]
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Update completed_date if status is being changed to completed
        if 'status' in self.changed_data and instance.status == 'completed':
            instance.completed_date = timezone.now()
        
        if commit:
            instance.save()
        
        return instance
