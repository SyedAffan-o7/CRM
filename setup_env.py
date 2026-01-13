#!/usr/bin/env python3
"""
Script to create .env file with PostgreSQL/Supabase configuration
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / '.env'

# Template for .env with PostgreSQL/Supabase
ENV_TEMPLATE = """# Django CRM Environment Configuration
# PostgreSQL Database (Supabase)
DATABASE_URL=postgresql://postgres.your-project-ref:your-password@aws-0-region.pooler.supabase.com:5432/postgres
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DB_CONN_MAX_AGE=600
DB_SSL_REQUIRED=True

# Security (change in production)
SECRET_KEY=django-insecure-your-secret-key-here-change-in-production
"""

def create_env_file():
    print("Setting up .env file for PostgreSQL/Supabase...")
    print(f"Target location: {ENV_PATH}")
    
    if ENV_PATH.exists():
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print("❌ Setup cancelled")
            return
    
    # Write the template
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.write(ENV_TEMPLATE.strip())
    
    print("✅ .env file created successfully!")
    print()
    print("🔧 IMPORTANT: You need to edit .env and replace:")
    print("   1. 'your-project-ref' with your Supabase project reference")
    print("   2. 'your-password' with your database password")
    print("   3. 'aws-0-region' with your Supabase region (e.g., us-east-1)")
    print()
    print("📋 Your Supabase connection string should look like:")
    print("   postgresql://postgres.abcdefgh:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres")
    print()
    print("🔍 Find your connection details in:")
    print("   Supabase Dashboard → Settings → Database → Connection string")

if __name__ == '__main__':
    create_env_file()
