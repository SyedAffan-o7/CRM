from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from accounts_app.models import Account, UserRole, UserProfile, UserPermissions
from accounts_app.forms import UserCreationFormWithRole, UserEditForm
from accounts_app.permissions import require_superuser
from crm_app.forms import AccountForm


@login_required
def account_list(request):
    """List all accounts"""
    if request.user.is_superuser:
        accounts = Account.objects.all()
    else:
        accounts = Account.objects.filter(created_by=request.user)

    return render(request, 'crm_app/account_list.html', {
        'accounts': accounts,
        'title': 'Accounts'
    })


@login_required
def account_add(request):
    """Add new account"""
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            if not account.created_by:
                account.created_by = request.user
            account.save()
            messages.success(request, 'Account created successfully.')
            return redirect('crm_app:account_list')
    else:
        form = AccountForm()

    return render(request, 'crm_app/account_form.html', {'form': form, 'title': 'Add Account'})


@login_required
def account_detail(request, pk):
    """Account detail view"""
    account = get_object_or_404(Account, pk=pk)
    return render(request, 'crm_app/account_detail.html', {
        'account': account,
        'title': f'Account: {account.company_name}'
    })


@login_required
def account_edit(request, pk):
    """Edit account"""
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account updated successfully.')
            return redirect('crm_app:account_detail', pk=pk)
    else:
        form = AccountForm(instance=account)

    return render(request, 'crm_app/account_form.html', {
        'form': form,
        'account': account,
        'title': f'Edit Account: {account.company_name}'
    })


# User Management Views (Superuser only)
@require_superuser
def user_management_dashboard(request):
    """Main dashboard for user management"""
    users = User.objects.select_related('profile__role').all()
    roles = UserRole.objects.filter(is_active=True)

    # Statistics
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    inactive_users = total_users - active_users
    users_by_role = {}

    for role in roles:
        count = users.filter(profile__role=role).count()
        users_by_role[role.display_name] = count

    context = {
        'users': users,
        'roles': roles,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'users_by_role': users_by_role,
        'title': 'User Management'
    }

    return render(request, 'accounts_app/user_management.html', context)


@require_superuser
def create_user(request):
    """Create a new user with role assignment"""
    # Ensure default roles exist and at least one active role is available for selection
    def ensure_default_roles():
        """Ensure only three roles exist and are active, with full permission matrices."""
        desired = [
            {"name": "SUPERUSER", "display_name": "Super Admin", "role_level": 100, "description": "Full access", "is_active": True},
            {"name": "MANAGER", "display_name": "Manager", "role_level": 60, "description": "Management oversight", "is_active": True},
            {"name": "SALESPERSON", "display_name": "Salesperson", "role_level": 40, "description": "Sales-focused", "is_active": True},
        ]
        desired_names = {r["name"] for r in desired}

        # Upsert desired roles
        roles_map = {}
        for r in desired:
            role, _ = UserRole.objects.update_or_create(
                name=r["name"],
                defaults={
                    "display_name": r["display_name"],
                    "role_level": r["role_level"],
                    "description": r["description"],
                    "is_active": True,
                },
            )
            roles_map[r["name"]] = role

        # Deactivate any other roles
        UserRole.objects.exclude(name__in=desired_names).update(is_active=False)

        # Seed permissions
        def set_perms(role, module, view=True, create=False, edit=False, delete=False, imp=False, exp=False):
            UserPermissions.objects.update_or_create(
                role=role,
                module=module,
                defaults={
                    "can_view": view,
                    "can_create": create,
                    "can_edit": edit,
                    "can_delete": delete,
                    "can_import": imp,
                    "can_export": exp,
                },
            )

        # Build module list
        modules = [m[0] for m in UserPermissions.MODULE_CHOICES]

        # SUPERUSER -> everything
        su = roles_map["SUPERUSER"]
        for m in modules:
            set_perms(su, m, True, True, True, True, True, True)

        # MANAGER -> view all; create/edit/delete for core ops; no users/settings mutation
        mgr = roles_map["MANAGER"]
        core_ce_d = {"contacts", "enquiries", "activities", "products", "accounts", "outbound"}
        for m in modules:
            if m in core_ce_d:
                set_perms(mgr, m, True, True, True, True, False, False)
            elif m in {"reports"}:
                set_perms(mgr, m, True, False, False, False, False, True)
            elif m in {"users", "settings", "import"}:
                set_perms(mgr, m, True, False, False, False, False, False)
            else:
                set_perms(mgr, m, True, False, False, False, False, False)

        # SALESPERSON -> view most; create/edit for enquiries/activities/contacts; no delete
        sp = roles_map["SALESPERSON"]
        sp_create_edit = {"enquiries", "activities", "contacts"}
        for m in modules:
            if m in sp_create_edit:
                set_perms(sp, m, True, True, True, False, False, False)
            elif m in {"outbound", "products", "accounts", "reports"}:
                set_perms(sp, m, True, False, False, False, False, False)
            else:
                # users, settings, import -> view False by default
                set_perms(sp, m, m not in {"users", "settings", "import"}, False, False, False, False, False)

    ensure_default_roles()
    if request.method == 'POST':
        form = UserCreationFormWithRole(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, f'User {user.username} created successfully with {user.profile.role.display_name} role.')
                return redirect('accounts_app:user_management')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationFormWithRole()

    return render(request, 'accounts_app/user_form.html', {
        'form': form,
        'title': 'Create New User',
        'is_edit': False
    })


@require_superuser
def edit_user(request, user_id):
    """Edit an existing user"""
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        print(f"DEBUG edit_user: POST data = {request.POST}")
        form = UserEditForm(request.POST, instance=user)
        print(f"DEBUG edit_user: Form is valid = {form.is_valid()}")
        if form.is_valid():
            print(f"DEBUG edit_user: Form cleaned data = {form.cleaned_data}")
            try:
                user = form.save()
                print(f"DEBUG edit_user: User saved successfully, role = {user.profile.role if hasattr(user, 'profile') else 'No profile'}")
                messages.success(request, f'User {user.username} updated successfully.')
                return redirect('accounts_app:user_management')
            except Exception as e:
                print(f"DEBUG edit_user: Error saving user: {e}")
                messages.error(request, f'Error updating user: {str(e)}')
        else:
            print(f"DEBUG edit_user: Form errors = {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserEditForm(instance=user)

    return render(request, 'accounts_app/user_form.html', {
        'form': form,
        'user': user,
        'title': f'Edit User: {user.username}',
        'is_edit': True
    })


@require_superuser
def toggle_user_status(request, user_id):
    """Toggle user active/inactive status"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()

        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {user.username} {status}.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'is_active': user.is_active})

    return redirect('accounts_app:user_management')


@require_superuser
def role_management(request):
    """Manage user roles and their permissions"""
    roles = UserRole.objects.all()
    permissions = UserPermissions.objects.select_related('role').all()

    if request.method == 'POST':
        # Handle role creation/update
        role_id = request.POST.get('role_id')
        if role_id:
            role = get_object_or_404(UserRole, id=role_id)
            role.name = request.POST.get('name')
            role.display_name = request.POST.get('display_name')
            role.description = request.POST.get('description')
            role.role_level = request.POST.get('role_level', 0)
            role.is_active = request.POST.get('is_active', False) == 'on'
            role.save()
            messages.success(request, f'Role {role.display_name} updated successfully.')
        else:
            # Create new role
            UserRole.objects.create(
                name=request.POST.get('name'),
                display_name=request.POST.get('display_name'),
                description=request.POST.get('description'),
                role_level=request.POST.get('role_level', 0),
                is_active=request.POST.get('is_active', False) == 'on'
            )
            messages.success(request, 'New role created successfully.')

        return redirect('accounts_app:role_management')

    context = {
        'roles': roles,
        'permissions': permissions,
        'title': 'Role Management'
    }

    return render(request, 'accounts_app/role_management.html', context)


@require_superuser
def delete_role(request, role_id):
    """Delete a user role"""
    role = get_object_or_404(UserRole, id=role_id)

    if request.method == 'POST':
        # Check if role is assigned to any users
        users_with_role = User.objects.filter(profile__role=role).count()

        if users_with_role > 0:
            messages.error(request, f'Cannot delete role {role.display_name}. It is assigned to {users_with_role} users.')
        else:
            role.delete()
            messages.success(request, f'Role {role.display_name} deleted successfully.')

    return redirect('accounts_app:role_management')


@require_superuser
def user_permissions_detail(request, user_id):
    """Show detailed permissions for a specific user"""
    user = get_object_or_404(User, id=user_id)
    permissions = []

    if hasattr(user, 'profile') and user.profile.role:
        for permission in user.profile.role.permissions.all():
            permissions.append({
                'module': permission.get_module_display(),
                'can_view': permission.can_view,
                'can_create': permission.can_create,
                'can_edit': permission.can_edit,
                'can_delete': permission.can_delete,
                'can_import': permission.can_import,
                'can_export': permission.can_export,
            })

    context = {
        'user': user,
        'permissions': permissions,
        'title': f'Permissions for {user.username}'
    }

    return render(request, 'accounts_app/user_permissions.html', context)


@require_superuser
def bulk_user_actions(request):
    """Handle bulk actions on users"""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_ids = request.POST.getlist('user_ids')

        if not user_ids:
            messages.error(request, 'No users selected.')
            return redirect('accounts_app:user_management')

        users = User.objects.filter(id__in=user_ids)

        if action == 'activate':
            users.update(is_active=True)
            messages.success(request, f'Activated {len(users)} users.')
        elif action == 'deactivate':
            users.update(is_active=False)
            messages.success(request, f'Deactivated {len(users)} users.')
        elif action == 'delete':
            # Only delete users without important data
            users.filter(is_active=False).delete()
            messages.success(request, f'Deleted {len(users.filter(is_active=False))} inactive users.')

    return redirect('accounts_app:user_management')


@require_superuser
def delete_user(request, user_id):
    """Delete a specific user"""
    user = get_object_or_404(User, id=user_id)
    
    # Prevent deleting yourself
    if user.id == request.user.id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts_app:user_management')
    
    # Prevent deleting superusers
    if user.is_superuser:
        messages.error(request, 'Cannot delete superuser accounts for security reasons.')
        return redirect('accounts_app:user_management')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" has been permanently deleted.')
        return redirect('accounts_app:user_management')
    
    return render(request, 'accounts_app/user_confirm_delete.html', {
        'user_to_delete': user,
        'title': f'Delete User: {user.username}'
    })


@require_superuser
def reset_user_password(request, user_id):
    """Reset user password"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not new_password:
            messages.error(request, 'Password cannot be empty.')
        elif new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, f'Password for {user.username} has been reset successfully.')
            return redirect('accounts_app:user_management')
    
    return render(request, 'accounts_app/user_password_reset.html', {
        'user_to_reset': user,
        'title': f'Reset Password: {user.username}'
    })


@require_superuser
def view_user_credentials(request, user_id):
    """View user credentials and details"""
    user = get_object_or_404(User, id=user_id)
    
    # Get user's activity statistics
    created_leads = user.created_leads.count() if hasattr(user, 'created_leads') else 0
    assigned_leads = user.assigned_leads.count() if hasattr(user, 'assigned_leads') else 0
    created_activities = user.activities.count() if hasattr(user, 'activities') else 0
    
    context = {
        'user_detail': user,
        'created_leads': created_leads,
        'assigned_leads': assigned_leads,
        'created_activities': created_activities,
        'title': f'User Details: {user.username}'
    }
    
    return render(request, 'accounts_app/user_credentials.html', context)
