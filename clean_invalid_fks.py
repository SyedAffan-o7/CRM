#!/usr/bin/env python3
"""
Django Foreign Key Integrity Check Script (PostgreSQL Compatible)

This script uses Django ORM to detect and optionally remove records
with invalid foreign key references, compatible with PostgreSQL and other databases.

Usage: python clean_invalid_fks.py
"""

import os
import sys
from pathlib import Path
import django
from django.db import transaction
from django.apps import apps

# Setup Django environment
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

def get_foreign_key_fields(model_class):
    """
    Get all foreign key fields from a Django model.
    Returns a list of tuples: (field_name, related_model, field_object)
    """
    fk_fields = []
    for field in model_class._meta.get_fields():
        if hasattr(field, 'related_model') and field.related_model:
            # This is a ForeignKey or OneToOneField
            if hasattr(field, 'column') and field.column:
                fk_fields.append((field.name, field.related_model, field))
    return fk_fields

def get_table_name(model_class):
    """Get the database table name for a Django model."""
    return model_class._meta.db_table

def clean_invalid_foreign_keys_orm():
    """
    Main function to clean invalid foreign keys using Django ORM (PostgreSQL compatible).
    """
    print("=" * 60)
    print("Django Foreign Key Integrity Check (ORM-based)")
    print("=" * 60)
    
    try:
        # Import the OutboundActivity model
        from outbound_app.models import OutboundActivity
        
        print(f"Analyzing model: {OutboundActivity.__name__}")
        print(f"Database table: {OutboundActivity._meta.db_table}")
        print("-" * 60)
        
        # Get all foreign key fields
        fk_fields = get_foreign_key_fields(OutboundActivity)
        
        if not fk_fields:
            print("No foreign key fields found in OutboundActivity model.")
            return
        
        print(f"Found {len(fk_fields)} foreign key field(s):")
        for field_name, related_model, field_obj in fk_fields:
            nullable = "nullable" if field_obj.null else "required"
            print(f"  - {field_name} -> {related_model.__name__} ({nullable})")
        print()
        
        total_records = OutboundActivity.objects.count()
        print(f"Total OutboundActivity records: {total_records}")
        print()
        
        invalid_records = []
        deletion_stats = {}
        
        # Check each foreign key field using ORM
        for field_name, related_model, field_obj in fk_fields:
            print(f"Checking {field_name} -> {related_model.__name__}...")
            
            try:
                # Find records with invalid foreign keys using ORM
                # Get all non-null FK values
                fk_values = OutboundActivity.objects.filter(
                    **{f"{field_name}__isnull": False}
                ).values_list(field_name, flat=True).distinct()
                
                if not fk_values:
                    print(f"  ✅ No {field_name} references to check")
                    deletion_stats[field_name] = {'count': 0, 'invalid_fk_values': []}
                    continue
                
                # Check which FK values exist in the related model
                existing_ids = set(related_model.objects.filter(
                    id__in=fk_values
                ).values_list('id', flat=True))
                
                invalid_fk_values = [fk_val for fk_val in fk_values if fk_val not in existing_ids]
                
                if invalid_fk_values:
                    # Find records with these invalid FK values
                    invalid_records_for_field = OutboundActivity.objects.filter(
                        **{f"{field_name}__in": invalid_fk_values}
                    )
                    
                    count = invalid_records_for_field.count()
                    print(f"  ❌ Found {count} records with invalid {field_name}:")
                    print(f"     Invalid {field_name} values: {', '.join(map(str, invalid_fk_values))}")
                    
                    invalid_records.extend(invalid_records_for_field)
                    deletion_stats[field_name] = {
                        'count': count,
                        'invalid_fk_values': invalid_fk_values
                    }
                else:
                    print(f"  ✅ All {field_name} references are valid")
                    deletion_stats[field_name] = {'count': 0, 'invalid_fk_values': []}
                    
            except Exception as e:
                print(f"  ⚠️  Error checking {field_name}: {e}")
                deletion_stats[field_name] = {'count': 0, 'invalid_fk_values': [], 'error': str(e)}
                continue
        
        print()
        print("-" * 60)
        
        # Remove duplicates
        unique_invalid_records = list(set(invalid_records))
        
        if unique_invalid_records:
            print(f"SUMMARY: Found {len(unique_invalid_records)} OutboundActivity record(s) with invalid foreign keys")
            
            # Show breakdown by FK field
            print("\nBreakdown by foreign key field:")
            for field_name, stats in deletion_stats.items():
                if stats['count'] > 0:
                    print(f"  - {field_name}: {stats['count']} invalid references")
                    print(f"    Missing IDs: {', '.join(map(str, stats['invalid_fk_values']))}")
            
            # Confirm deletion
            print(f"\nThis will DELETE {len(unique_invalid_records)} OutboundActivity record(s).")
            response = input("Do you want to proceed? (yes/no): ").lower().strip()
            
            if response in ['yes', 'y']:
                with transaction.atomic():
                    # Delete the records using ORM
                    deleted_count = 0
                    for record in unique_invalid_records:
                        record.delete()
                        deleted_count += 1
                    
                    print(f"\n✅ Successfully deleted {deleted_count} OutboundActivity record(s)")
                    
                    # Verify cleanup
                    remaining_records = OutboundActivity.objects.count()
                    print(f"Remaining OutboundActivity records: {remaining_records}")
                    
            else:
                print("❌ Deletion cancelled by user")
                return
                
        else:
            print("✅ No invalid foreign key references found!")
            print("All OutboundActivity records have valid foreign keys.")
        
        print()
        print("=" * 60)
        print("CLEANUP COMPLETE")
        print("=" * 60)
        
        if total_deleted > 0:
            print(f"Total records deleted: {total_deleted}")
            print("\nYou can now run 'python manage.py migrate' safely.")
        else:
            print("No records were deleted.")
            
        print("\nForeign key validation summary:")
        for field_name, stats in deletion_stats.items():
            status = "✅ CLEAN" if stats['count'] == 0 else f"❌ {stats['count']} INVALID"
            print(f"  {field_name}: {status}")
            
    except ImportError as e:
        print(f"❌ Error importing OutboundActivity model: {e}")
        print("Make sure you're running this script from the Django project root directory.")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

        print()
        print("=" * 60)
        print("CLEANUP COMPLETE")
        print("=" * 60)
        
        print("\nForeign key validation summary:")
        for field_name, stats in deletion_stats.items():
            status = "✅ CLEAN" if stats['count'] == 0 else f"❌ {stats['count']} INVALID"
            print(f"  {field_name}: {status}")
            
    except ImportError as e:
        print(f"❌ Error importing OutboundActivity model: {e}")
        print("Make sure you're running this script from the Django project root directory.")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def run_foreign_key_check_orm():
    """
    Run a comprehensive foreign key check without deleting anything (ORM-based).
    """
    print("Running FK integrity check (read-only mode, ORM-based)...")
    
    try:
        from outbound_app.models import OutboundActivity
        
        fk_fields = get_foreign_key_fields(OutboundActivity)
        
        print(f"Checking {len(fk_fields)} foreign key field(s) in OutboundActivity...")
        
        total_violations = 0
        for field_name, related_model, field_obj in fk_fields:
            try:
                # Get all non-null FK values
                fk_values = OutboundActivity.objects.filter(
                    **{f"{field_name}__isnull": False}
                ).values_list(field_name, flat=True).distinct()
                
                if not fk_values:
                    print(f"  ✅ {field_name}: No references to check")
                    continue
                
                # Check which FK values exist in the related model
                existing_ids = set(related_model.objects.filter(
                    id__in=fk_values
                ).values_list('id', flat=True))
                
                invalid_fk_values = [fk_val for fk_val in fk_values if fk_val not in existing_ids]
                
                if invalid_fk_values:
                    count = OutboundActivity.objects.filter(
                        **{f"{field_name}__in": invalid_fk_values}
                    ).count()
                    print(f"  ❌ {field_name}: {count} records with invalid references")
                    total_violations += count
                else:
                    print(f"  ✅ {field_name}: All references are valid")
                    
            except Exception as e:
                print(f"  ⚠️  {field_name}: Error checking - {e}")
        
        if total_violations == 0:
            print("✅ No foreign key violations detected")
        else:
            print(f"❌ Found {total_violations} total foreign key violations")
                
    except Exception as e:
        print(f"❌ Error running FK check: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--check-only':
        run_foreign_key_check_orm()
    else:
        clean_invalid_foreign_keys_orm()
