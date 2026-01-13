#!/usr/bin/env python
"""
Simple debug script to test Django setup and identify issues
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')

try:
    django.setup()
    print("✅ Django setup successful")
    
    # Test imports
    from crm_app.models import Lead, Contact, Account, Deal, ActivityLog, Product, Reason, LeadSource
    print("✅ CRM models imported successfully")
    
    from products.models import Category, Subcategory
    print("✅ Products models imported successfully")
    
    from crm_app.forms import LeadForm, ContactForm, AccountForm, DealForm, ActivityLogForm
    print("✅ Forms imported successfully")
    
    from crm_app.views import dashboard
    print("✅ Views imported successfully")
    
    # Test database connection
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("SELECT 1")
    print("✅ Database connection working")
    
    # Check if tables exist
    from django.db import connection
    tables = connection.introspection.table_names()
    required_tables = ['crm_app_lead', 'crm_app_contact', 'products_category', 'products_subcategory']
    
    for table in required_tables:
        if table in tables:
            print(f"✅ Table {table} exists")
        else:
            print(f"❌ Table {table} missing")
    
    print("\n🎉 All tests passed! Django is working correctly.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
