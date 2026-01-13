import os
import sys
from pathlib import Path
import django
from django.conf import settings
from django.db import connection

# Setup Django if running outside manage.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')

def redact_settings(db_settings: dict) -> dict:
    redacted = dict(db_settings)
    if 'PASSWORD' in redacted and redacted['PASSWORD']:
        redacted['PASSWORD'] = '***REDACTED***'
    if 'OPTIONS' in redacted and isinstance(redacted['OPTIONS'], dict):
        # Avoid dumping SSL cert material etc.
        redacted['OPTIONS'] = {k: ('***REDACTED***' if 'key' in k.lower() or 'cert' in k.lower() else v)
                               for k, v in redacted['OPTIONS'].items()}
    return redacted

try:
    django.setup()
    # Ensure connection
    connection.ensure_connection()
    print("✅ Database connection successful!")

    # Print a concise summary first
    engine = connection.settings_dict.get('ENGINE')
    vendor = getattr(connection, 'vendor', None)
    print(f"Engine: {engine}")
    print(f"Vendor: {vendor}")

    # Print full (redacted) settings
    redacted = redact_settings(connection.settings_dict)
    print("Current DB settings:", redacted)

    # Final verdict for clarity
    is_pg = (vendor == 'postgresql') or (engine == 'django.db.backends.postgresql')
    print(f"Verdict: {'PostgreSQL ACTIVE' if is_pg else 'NOT PostgreSQL'}")
except Exception as e:
    print("❌ Database connection failed!")
    print("Error:", e)
    raise
