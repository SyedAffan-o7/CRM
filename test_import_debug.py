#!/usr/bin/env python
"""
Test script to debug Google Sheets import functionality
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth.models import User
from leads_app.models import Lead, Product, Reason
from products.models import Category
import requests
import pandas as pd

def test_import_functionality():
    """Test the import functionality with a simple test case"""
    print("=== TESTING IMPORT FUNCTIONALITY ===")
    
    # Test 1: Check if models can be created
    print("\n1. Testing model creation...")
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_import_user',
        defaults={'email': 'test@example.com', 'first_name': 'Test', 'last_name': 'User'}
    )
    print(f"Test user: {user} (created: {created})")
    
    # Test Category creation (should work - has created_by field)
    try:
        category, created = Category.objects.get_or_create(
            name='Test Category',
            defaults={'created_by': user}
        )
        print(f"✅ Category creation: {category} (created: {created})")
    except Exception as e:
        print(f"❌ Category creation failed: {e}")
    
    # Test Product creation (should work now - no created_by field)
    try:
        product, created = Product.objects.get_or_create(
            name='Test Product',
            defaults={}
        )
        print(f"✅ Product creation: {product} (created: {created})")
    except Exception as e:
        print(f"❌ Product creation failed: {e}")
    
    # Test Reason creation (should work now - no created_by field)
    try:
        reason, created = Reason.objects.get_or_create(
            name='Test Reason',
            defaults={}
        )
        print(f"✅ Reason creation: {reason} (created: {created})")
    except Exception as e:
        print(f"❌ Reason creation failed: {e}")
    
    # Test Lead creation
    try:
        lead = Lead.objects.create(
            contact_name='Test Contact',
            phone_number='1234567890',
            company_name='Test Company',
            image_url='https://example.com/image.jpg',
            category=category,
            lead_status='not_fulfilled',
            enquiry_stage='enquiry_received',
            reason=reason,
            notes='Test import',
            created_by=user,
            assigned_sales_person=user,
        )
        print(f"✅ Lead creation: {lead}")
        
        # Add product to lead
        lead.products_enquired.add(product)
        print(f"✅ Product added to lead")
        
    except Exception as e:
        print(f"❌ Lead creation failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    print("\n2. Testing CSV parsing...")
    
    # Test CSV parsing with sample data
    sample_csv = """Customer Phone #,Customer Name,Company Name,Image URL,Category,Item,Fulfilled,Sales Invoice No.,Reason,New/Old,Local / Import,Qty,Price,Follow ups,Comments
1234567891,John Doe,ABC Corp,https://example.com/image1.jpg,Safety Equipment,Hard Hat,No,,Quality Issue,New,Local,10,25.50,Weekly,Good customer
1234567892,Jane Smith,XYZ Ltd,https://example.com/image2.jpg,PPE,Safety Gloves,Yes,INV1234567,Price,Old,Import,5,15.75,Monthly,Regular order"""
    
    try:
        df = pd.read_csv(pd.io.common.StringIO(sample_csv))
        print(f"✅ CSV parsing successful. Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"First row data: {dict(df.iloc[0])}")
        
        # Check for required columns
        required_columns = ['Customer Phone #', 'Image URL']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
        else:
            print(f"✅ All required columns present")
            
        # Test filtering for valid rows
        valid_rows = df.dropna(subset=['Image URL']).tail(20)
        print(f"✅ Valid rows: {len(valid_rows)}")
        
    except Exception as e:
        print(f"❌ CSV parsing failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == '__main__':
    test_import_functionality()
