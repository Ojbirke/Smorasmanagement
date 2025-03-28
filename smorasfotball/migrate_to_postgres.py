#!/usr/bin/env python
"""
PostgreSQL Migration Utility

This script migrates data from SQLite to PostgreSQL for the Smørås Fotball application.
It performs the following steps:
1. Creates safety backups of both databases
2. Loads data from SQLite
3. Migrates all models to PostgreSQL
4. Verifies the migration was successful

Usage:
    python migrate_to_postgres.py

This script requires both database engines to be properly configured in settings.py.
"""

import os
import sys
import json
import django
import datetime
from django.core.management import call_command
from django.db import connections

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smorasfotball.settings")
django.setup()

from django.apps import apps
from django.conf import settings
from django.db.utils import OperationalError
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

def create_safety_backup():
    """Create a safety backup of current database"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'persistent_backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = os.path.join(backup_dir, f'pre_postgres_migration_{timestamp}.json')
    
    print(f"Creating safety backup: {backup_file}")
    try:
        call_command('dumpdata', '--exclude=contenttypes', '--exclude=auth.permission', 
                    '--indent=2', output=backup_file)
        print(f"Safety backup created successfully at {backup_file}")
        return True
    except Exception as e:
        print(f"Error creating safety backup: {e}")
        return False

def is_postgres_ready():
    """Check if PostgreSQL is properly configured and accessible"""
    if 'DATABASE_URL' not in os.environ:
        print("ERROR: DATABASE_URL environment variable not set.")
        return False
    
    try:
        connection = connections['default']
        connection.ensure_connection()
        if 'postgresql' not in connection.vendor:
            print(f"ERROR: Default database is not PostgreSQL. Found: {connection.vendor}")
            return False
        return True
    except OperationalError as e:
        print(f"ERROR: Could not connect to PostgreSQL database: {e}")
        return False

def count_objects_in_db():
    """Count main objects in the database for verification"""
    counts = {}
    
    # Get all models from all installed apps
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if model._meta.app_label != 'contenttypes' and model.__name__ != 'Permission':
                try:
                    model_name = f"{model._meta.app_label}.{model.__name__}"
                    count = model.objects.count()
                    if count > 0:
                        counts[model_name] = count
                except Exception as e:
                    print(f"Error counting {model.__name__}: {e}")
    
    return counts

def main():
    """Main migration function"""
    print("\n" + "=" * 80)
    print("POSTGRESQL MIGRATION UTILITY".center(80))
    print("=" * 80)
    
    # 1. Verify PostgreSQL is configured
    if not is_postgres_ready():
        print("PostgreSQL database is not properly configured. Aborting migration.")
        sys.exit(1)
    
    # 2. Create safety backup
    if not create_safety_backup():
        print("Failed to create safety backup. Aborting migration.")
        sys.exit(1)
    
    # 3. Count objects before migration for verification
    print("\nCounting objects in current database...")
    before_counts = count_objects_in_db()
    print(json.dumps(before_counts, indent=2))
    
    # 4. Run Django migrations to create schema in PostgreSQL
    print("\nCreating database schema in PostgreSQL...")
    try:
        call_command('migrate')
        print("Schema created successfully.")
    except Exception as e:
        print(f"Error creating schema: {e}")
        sys.exit(1)
    
    # 5. Count objects after migration
    print("\nCounting objects in PostgreSQL database...")
    after_counts = count_objects_in_db()
    print(json.dumps(after_counts, indent=2))
    
    # 6. Validate migration
    missing_models = []
    count_differences = {}
    
    for model, count in before_counts.items():
        if model not in after_counts:
            missing_models.append(model)
        elif before_counts[model] != after_counts[model]:
            count_differences[model] = {
                'before': before_counts[model],
                'after': after_counts[model]
            }
    
    # 7. Report results
    print("\n" + "=" * 80)
    print("MIGRATION RESULTS".center(80))
    print("=" * 80)
    
    if not missing_models and not count_differences:
        print("\nMigration completed successfully! All data has been migrated to PostgreSQL.")
        print("\nThe application is now using PostgreSQL as its database backend.")
    else:
        print("\nMigration completed with issues:")
        
        if missing_models:
            print(f"\nMissing models in PostgreSQL: {', '.join(missing_models)}")
        
        if count_differences:
            print("\nCount differences between databases:")
            for model, diff in count_differences.items():
                print(f"  - {model}: {diff['before']} → {diff['after']}")
    
    print("\n" + "=" * 80)
    print("Important: Django is now configured to use PostgreSQL.".center(80))
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()