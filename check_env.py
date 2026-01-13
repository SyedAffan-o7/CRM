#!/usr/bin/env python3
"""
Simple script to check .env file and DATABASE_URL
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / '.env'

print(f"Project root: {PROJECT_ROOT}")
print(f"Looking for .env at: {ENV_PATH}")
print(f".env exists: {ENV_PATH.exists()}")

if ENV_PATH.exists():
    print(f".env file size: {ENV_PATH.stat().st_size} bytes")
    
    # Read raw content
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Raw .env content ({len(content)} chars):")
    print("=" * 50)
    print(repr(content))  # Show with escape characters
    print("=" * 50)
    
    # Load with dotenv
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    
    # Check what we got
    database_url = os.getenv('DATABASE_URL')
    debug = os.getenv('DEBUG')
    
    print(f"DATABASE_URL from os.getenv(): {repr(database_url)}")
    print(f"DEBUG from os.getenv(): {repr(debug)}")
    
    # Check if DATABASE_URL is in the content
    if 'DATABASE_URL' in content:
        print("✅ DATABASE_URL found in .env content")
        # Extract the line
        for line in content.split('\n'):
            if line.strip().startswith('DATABASE_URL'):
                print(f"DATABASE_URL line: {repr(line)}")
    else:
        print("❌ DATABASE_URL not found in .env content")
        
else:
    print("❌ .env file does not exist!")
    print("You need to create it. Here's what to do:")
    print("1. Copy .env.example to .env")
    print("2. Edit .env with your Supabase DATABASE_URL")
    print()
    print("Example .env content:")
    print("DATABASE_URL=postgresql://user:password@host:5432/database")
    print("DEBUG=True")
    print("DB_SSL_REQUIRED=True")
