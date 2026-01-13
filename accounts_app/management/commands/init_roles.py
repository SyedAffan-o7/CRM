from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts_app.models import UserRole, UserPermissions, UserProfile

class Command(BaseCommand):
    help = 'Initialize default user roles and permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all roles and permissions to defaults',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting all roles and permissions...')
            UserRole.objects.all().delete()
            UserPermissions.objects.all().delete()

        self.create_default_roles()
        self.create_default_permissions()
        self.create_superuser_profile()

        self.stdout.write(
            self.style.SUCCESS('Successfully initialized user roles and permissions!')
        )

    def create_default_roles(self):
        """Create default user roles"""
        roles_data = [
            {
                'name': 'SUPERUSER',
                'display_name': 'Super User',
                'description': 'Full system access with all permissions',
                'role_level': 100,
            },
            {
                'name': 'ADMIN',
                'display_name': 'Administrator',
                'description': 'Administrative access with user management capabilities',
                'role_level': 80,
            },
            {
                'name': 'MANAGER',
                'display_name': 'Manager',
                'description': 'Management access with oversight capabilities',
                'role_level': 60,
            },
            {
                'name': 'SALESPERSON',
                'display_name': 'Salesperson',
                'description': 'Sales team member with customer and enquiry access',
                'role_level': 40,
            },
            {
                'name': 'SUPPORT',
                'display_name': 'Support Staff',
                'description': 'Support team member with limited access',
                'role_level': 20,
            },
            {
                'name': 'VIEWER',
                'display_name': 'Viewer Only',
                'description': 'Read-only access to system data',
                'role_level': 10,
            },
        ]

        for role_data in roles_data:
            role, created = UserRole.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
            if created:
                self.stdout.write(f"Created role: {role.display_name}")
            else:
                # Update existing role
                for key, value in role_data.items():
                    setattr(role, key, value)
                role.save()
                self.stdout.write(f"Updated role: {role.display_name}")

    def create_default_permissions(self):
        """Create default permissions for each role"""

        # Super User - Full access to everything
        self.create_role_permissions('SUPERUSER', [
            ('contacts', True, True, True, True, True, True),
            ('enquiries', True, True, True, True, True, True),
            ('outbound', True, True, True, True, True, True),
            ('activities', True, True, True, True, True, True),
            ('products', True, True, True, True, True, True),
            ('accounts', True, True, True, True, True, True),
            ('reports', True, True, True, True, True, True),
            ('users', True, True, True, True, True, True),
            ('settings', True, True, True, True, True, True),
            ('import', True, True, True, True, True, True),
        ])

        # Administrator - Most permissions except some advanced features
        self.create_role_permissions('ADMIN', [
            ('contacts', True, True, True, True, True, True),
            ('enquiries', True, True, True, True, True, True),
            ('outbound', True, True, True, True, True, True),
            ('activities', True, True, True, True, True, True),
            ('products', True, True, True, True, True, True),
            ('accounts', True, True, True, True, True, True),
            ('reports', True, True, True, True, True, True),
            ('users', True, True, True, True, False, False),
            ('settings', True, True, True, True, False, False),
            ('import', True, True, True, True, True, True),
        ])

        # Manager - Management oversight
        self.create_role_permissions('MANAGER', [
            ('contacts', True, True, True, True, True, True),
            ('enquiries', True, True, True, True, True, True),
            ('outbound', True, True, True, True, True, True),
            ('activities', True, True, True, True, True, True),
            ('products', True, True, True, False, True, True),
            ('accounts', True, True, True, False, True, True),
            ('reports', True, True, True, True, True, True),
            ('users', True, False, False, False, False, False),
            ('settings', False, False, False, False, False, False),
            ('import', False, False, False, False, False, False),
        ])

        # Salesperson - Sales focused permissions
        self.create_role_permissions('SALESPERSON', [
            ('contacts', True, True, True, False, False, False),
            ('enquiries', True, True, True, False, False, False),
            ('outbound', True, True, True, False, False, False),
            ('activities', True, True, True, False, False, False),
            ('products', True, True, False, False, False, False),
            ('accounts', True, True, False, False, False, False),
            ('reports', True, False, False, False, False, False),
            ('users', False, False, False, False, False, False),
            ('settings', False, False, False, False, False, False),
            ('import', False, False, False, False, False, False),
        ])

        # Support Staff - Limited access
        self.create_role_permissions('SUPPORT', [
            ('contacts', True, True, True, False, False, False),
            ('enquiries', True, True, True, False, False, False),
            ('outbound', True, True, False, False, False, False),
            ('activities', True, True, False, False, False, False),
            ('products', True, False, False, False, False, False),
            ('accounts', True, False, False, False, False, False),
            ('reports', True, False, False, False, False, False),
            ('users', False, False, False, False, False, False),
            ('settings', False, False, False, False, False, False),
            ('import', False, False, False, False, False, False),
        ])

        # Viewer Only - Read-only access
        self.create_role_permissions('VIEWER', [
            ('contacts', True, False, False, False, False, False),
            ('enquiries', True, False, False, False, False, False),
            ('outbound', True, False, False, False, False, False),
            ('activities', True, False, False, False, False, False),
            ('products', True, False, False, False, False, False),
            ('accounts', True, False, False, False, False, False),
            ('reports', True, False, False, False, False, False),
            ('users', False, False, False, False, False, False),
            ('settings', False, False, False, False, False, False),
            ('import', False, False, False, False, False, False),
        ])

    def create_role_permissions(self, role_name, permissions_list):
        """Create permissions for a specific role"""
        try:
            role = UserRole.objects.get(name=role_name)

            for module, can_view, can_create, can_edit, can_delete, can_import, can_export in permissions_list:
                permission, created = UserPermissions.objects.get_or_create(
                    role=role,
                    module=module,
                    defaults={
                        'can_view': can_view,
                        'can_create': can_create,
                        'can_edit': can_edit,
                        'can_delete': can_delete,
                        'can_import': can_import,
                        'can_export': can_export,
                    }
                )

                if created:
                    self.stdout.write(f"  Created permission: {role.display_name} -> {module}")
                else:
                    # Update existing permission
                    permission.can_view = can_view
                    permission.can_create = can_create
                    permission.can_edit = can_edit
                    permission.can_delete = can_delete
                    permission.can_import = can_import
                    permission.can_export = can_export
                    permission.save()
                    self.stdout.write(f"  Updated permission: {role.display_name} -> {module}")

        except UserRole.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f'Role {role_name} not found. Skipping permissions.')
            )

    def create_superuser_profile(self):
        """Ensure superusers have proper profiles"""
        superusers = User.objects.filter(is_superuser=True)

        for superuser in superusers:
            profile, created = UserProfile.objects.get_or_create(
                user=superuser,
                defaults={
                    'role': UserRole.objects.get(name='SUPERUSER'),
                    'is_active': True,
                }
            )

            if created:
                self.stdout.write(f"Created profile for superuser: {superuser.username}")
            else:
                # Update existing profile
                profile.role = UserRole.objects.get(name='SUPERUSER')
                profile.is_active = True
                profile.save()
                self.stdout.write(f"Updated profile for superuser: {superuser.username}")
