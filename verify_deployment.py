#!/usr/bin/env python
"""
Deployment verification script for Django CRM
Run this after deployment to verify everything is working correctly
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

def verify_deployment():
    """Verify deployment is successful"""
    print("🔍 Verifying Django CRM Deployment...")
    
    # Check database connection
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ Database connection: OK")
    except Exception as e:
        print(f"❌ Database connection: FAILED - {e}")
        return False
    
    # Check models
    try:
        from django.contrib.auth.models import User
        from accounts_app.models import UserRole, UserProfile
        from leads_app.models import Lead
        from customers_app.models import Contact
        
        user_count = User.objects.count()
        role_count = UserRole.objects.count()
        print(f"✅ Models: OK - {user_count} users, {role_count} roles")
    except Exception as e:
        print(f"❌ Models: FAILED - {e}")
        return False
    
    # Check static files
    try:
        from django.conf import settings
        static_root = settings.STATIC_ROOT
        if os.path.exists(static_root):
            print("✅ Static files: OK")
        else:
            print("⚠️  Static files: Not collected (run collectstatic)")
    except Exception as e:
        print(f"❌ Static files: FAILED - {e}")
    
    # Check superuser exists
    try:
        if User.objects.filter(is_superuser=True).exists():
            print("✅ Superuser: OK")
        else:
            print("⚠️  Superuser: Not found (create one)")
    except Exception as e:
        print(f"❌ Superuser check: FAILED - {e}")
    
    # Check roles are initialized
    try:
        required_roles = ['SUPERUSER', 'ADMIN', 'MANAGER', 'SALESPERSON', 'SUPPORT', 'VIEWER']
        existing_roles = list(UserRole.objects.values_list('name', flat=True))
        missing_roles = [role for role in required_roles if role not in existing_roles]
        
        if not missing_roles:
            print("✅ Roles: OK - All default roles exist")
        else:
            print(f"⚠️  Roles: Missing {missing_roles} (run init_roles command)")
    except Exception as e:
        print(f"❌ Roles check: FAILED - {e}")
    
    print("\n🚀 Deployment verification complete!")
    print("📝 Next steps:")
    print("   1. Access your application at your Render URL")
    print("   2. Login with admin credentials")
    print("   3. Change default password immediately")
    print("   4. Configure user roles and permissions")
    print("   5. Add your team members")
    
    return True

if __name__ == "__main__":
    verify_deployment()
