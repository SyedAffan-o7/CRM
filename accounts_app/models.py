from django.db import models
from django.contrib.auth.models import User


class Account(models.Model):
    ACCOUNT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('prospect', 'Prospect'),
    ]

    company_name = models.CharField(max_length=200)
    primary_contact = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    address = models.TextField(blank=True)
    industry_type = models.CharField(max_length=100, blank=True)
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS_CHOICES, default='prospect')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_accounts')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

    class Meta:
        ordering = ['company_name']


class UserRole(models.Model):
    """Defines user roles with different permission levels"""
    ROLE_CHOICES = [
        ('SUPERUSER', 'Super User'),
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('SALESPERSON', 'Salesperson'),
        ('SUPPORT', 'Support Staff'),
        ('VIEWER', 'Viewer Only'),
    ]

    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    role_level = models.IntegerField(default=0, help_text="Higher number = more permissions")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    class Meta:
        ordering = ['-role_level', 'name']


class UserPermissions(models.Model):
    """Defines which modules each role can access"""
    MODULE_CHOICES = [
        ('contacts', 'Contacts Management'),
        ('enquiries', 'Enquiries Management'),
        ('outbound', 'Outbound Activities'),
        ('activities', 'Activity Logs'),
        ('products', 'Products & Categories'),
        ('accounts', 'Accounts & Companies'),
        ('reports', 'Reports & Analytics'),
        ('users', 'User Management'),
        ('settings', 'System Settings'),
        ('import', 'Data Import'),
    ]

    role = models.ForeignKey(UserRole, on_delete=models.CASCADE, related_name='permissions')
    module = models.CharField(max_length=50, choices=MODULE_CHOICES)
    can_view = models.BooleanField(default=True)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_import = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role.display_name} - {self.get_module_display()}"

    class Meta:
        unique_together = ['role', 'module']
        ordering = ['role', 'module']


class UserProfile(models.Model):
    """Extended user profile with role and additional information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True, blank=True)
    employee_id = models.CharField(max_length=50, blank=True, help_text="Employee/Staff ID")
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True)
    date_joined = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Track original role for notifications
        if self.pk:
            try:
                original = UserProfile.objects.get(pk=self.pk)
                self._original_role_id = original.role_id
            except UserProfile.DoesNotExist:
                self._original_role_id = None
        else:
            self._original_role_id = None
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.role.display_name if self.role else 'No Role'}"

    def has_permission(self, module, permission_type='view'):
        """Check if user has permission for a specific module and action"""
        if not self.role:
            return False

        try:
            permission = self.role.permissions.get(module=module)
            permission_map = {
                'view': permission.can_view,
                'create': permission.can_create,
                'edit': permission.can_edit,
                'delete': permission.can_delete,
                'import': permission.can_import,
                'export': permission.can_export,
            }
            return permission_map.get(permission_type, False)
        except UserPermissions.DoesNotExist:
            return False

    @property
    def accessible_modules(self):
        """Get list of modules user can access"""
        if not self.role:
            return []

        return self.role.permissions.filter(
            can_view=True
        ).values_list('module', flat=True)

    class Meta:
        ordering = ['user__username']
