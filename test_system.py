#!/usr/bin/env python
import os
import sys
import django
from django.core.management import execute_from_command_line

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from crm_app.models import Lead, Contact, Account, Deal
from products.models import Category, Subcategory

def test_system():
    print("🔍 Testing Django CRM System...")
    
    # Test 1: Check migrations
    print("\n1. Checking migrations...")
    execute_from_command_line(['manage.py', 'showmigrations', '--verbosity=0'])
    
    # Test 2: Check models
    print("\n2. Testing models...")
    try:
        # Test Lead model with new fields
        lead_count = Lead.objects.count()
        print(f"   ✅ Lead model accessible - {lead_count} records")
        
        # Test Category/Subcategory models
        category_count = Category.objects.count()
        subcategory_count = Subcategory.objects.count()
        print(f"   ✅ Category model accessible - {category_count} records")
        print(f"   ✅ Subcategory model accessible - {subcategory_count} records")
        
    except Exception as e:
        print(f"   ❌ Model error: {e}")
    
    # Test 3: Check URL patterns
    print("\n3. Testing URL patterns...")
    client = Client()
    
    urls_to_test = [
        '/dashboard/',
        '/leads/',
        '/contacts/',
        '/accounts/',
        '/deals/',
        '/get_subcategories/',
    ]
    
    for url in urls_to_test:
        try:
            response = client.get(url)
            if response.status_code in [200, 302, 403]:  # 403 is OK (auth required)
                print(f"   ✅ {url} - Status: {response.status_code}")
            else:
                print(f"   ⚠️  {url} - Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {url} - Error: {e}")
    
    print("\n🎉 System test complete!")
    print("\nNext steps:")
    print("1. Run: python check_migrations_only.bat")
    print("2. Run: python manage.py runserver")
    print("3. Visit: http://127.0.0.1:8000/")

if __name__ == '__main__':
    test_system()
