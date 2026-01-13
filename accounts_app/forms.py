from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from accounts_app.models import UserRole, UserProfile

class UserCreationFormWithRole(UserCreationForm):
    """Form for creating new users with role assignment"""
    role = forms.ModelChoiceField(
        queryset=UserRole.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select a role"
    )
    employee_id = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employee ID'})
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    date_joined = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to all fields
        for field_name in self.fields:
            if field_name not in ['role']:
                self.fields[field_name].widget.attrs.update({'class': 'form-control'})

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        phone = (cleaned_data.get('phone') or '').strip()
        if role and role.name != 'SALESPERSON' and not phone:
            raise ValidationError('Phone number is required for this role.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = True
        if commit:
            user.save()

        # Create user profile
        role = self.cleaned_data.get('role')

        # Handle phone: set to None if empty
        phone_val = self.cleaned_data.get('phone', '').strip()
        if not phone_val:
            phone_val = None

        # Enforce unique phone at DB level: clean_phone will validate before save
        UserProfile.objects.create(
            user=user,
            role=role,
            employee_id=self.cleaned_data.get('employee_id', ''),
            department=self.cleaned_data.get('department', ''),
            phone=phone_val,
            date_joined=self.cleaned_data.get('date_joined')
        )

        return user

class UserEditForm(forms.ModelForm):
    """Form for editing existing users"""
    role = forms.ModelChoiceField(
        queryset=UserRole.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    employee_id = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employee ID'})
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    date_joined = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to all fields
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})

        # Set initial values from profile
        if self.instance and hasattr(self.instance, 'profile'):
            profile = self.instance.profile
            self.fields['role'].initial = profile.role
            self.fields['employee_id'].initial = profile.employee_id
            self.fields['department'].initial = profile.department
            self.fields['phone'].initial = profile.phone
            self.fields['date_joined'].initial = profile.date_joined

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        phone = (cleaned_data.get('phone') or '').strip()
        # Role validation only; duplicates are allowed now
        if role and role.name != 'SALESPERSON' and not phone:
            raise ValidationError('Phone number is required for this role.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.save()

        # Update user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data.get('role')
        profile.employee_id = self.cleaned_data.get('employee_id', '')
        profile.department = self.cleaned_data.get('department', '')
        # Handle phone: set to None if empty
        phone_val = self.cleaned_data.get('phone', '').strip()
        if not phone_val:
            phone_val = None
        profile.phone = phone_val
        profile.date_joined = self.cleaned_data.get('date_joined')
        profile.save()

        return user

class RolePermissionForm(forms.ModelForm):
    """Form for managing role permissions"""
    class Meta:
        model = UserRole
        fields = ('name', 'display_name', 'description', 'role_level', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})
