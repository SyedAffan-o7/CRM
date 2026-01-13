#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from customers_app.forms import CustomerImportForm
import io

# Create test CSV data with some duplicates
csv_data = '''full_name,phone_number,email,company_name
Test User 1,+1234567890,test1@example.com,Test Company A
Test User 2,+0987654321,test2@example.com,Test Company B
Test User 1,+1234567890,test1-duplicate@example.com,Test Company A Duplicate
Test User 3,+1122334455,test3@example.com,Test Company C'''

# Create a file-like object
file_obj = io.BytesIO(csv_data.encode('utf-8'))
file_obj.name = 'test_duplicates.csv'

# Create form with the file
form = CustomerImportForm(files={'file': file_obj})

if form.is_valid():
    customers_data, errors = form.process_file()
    print(f'Found {len(customers_data)} customers to process')
    print(f'Found {len(errors)} errors')
    for i, customer in enumerate(customers_data):
        print(f'{i+1}. {customer["full_name"]}: {customer["phone_number"]} - Row {customer["row_number"]}')
else:
    print('Form validation errors:', form.errors)
