#!/usr/bin/env python3
"""
Ensure PostgreSQL Use

This script checks if the database is using PostgreSQL and takes steps to migrate
data from SQLite to PostgreSQL if necessary. It's designed to be run after deployment.

Usage:
    python ensure_postgres.py
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path

# Add Django project to path
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball')
sys.path.append(BASE_DIR)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')

try:
    import django
    django.setup()
    from django.core.management import call_command
    from django.conf import settings
    from django.db import connections
except ImportError:
    print("Error: Django could not be imported. Make sure Django is installed.")
    sys.exit(1)

def is_postgres_active():
    """Check if PostgreSQL is actually being used"""
    db_config = settings.DATABASES['default']
    engine = db_config.get('ENGINE', '')
    
    print(f"Current database engine: {engine}")
    return 'postgresql' in engine

def is_sqlite_active():
    """Check if SQLite is being used"""
    db_config = settings.DATABASES['default']
    engine = db_config.get('ENGINE', '')
    
    print(f"Current database engine: {engine}")
    return 'sqlite3' in engine

def get_database_counts():
    """Get counts of objects in the database"""
    try:
        # Import models
        from django.contrib.auth.models import User
        from teammanager.models import Team, Player, Match
        
        return {
            'teams': Team.objects.count(),
            'players': Player.objects.count(),
            'matches': Match.objects.count(),
            'users': User.objects.count(),
        }
    except Exception as e:
        print(f"Error counting database objects: {str(e)}")
        return {'teams': 0, 'players': 0, 'matches': 0, 'users': 0}

def force_postgres_environment():
    """Force the DATABASE_URL environment variable to be set"""
    # Check if the DATABASE_URL environment variable is already set
    if os.environ.get('DATABASE_URL'):
        print(f"DATABASE_URL is already set: {os.environ.get('DATABASE_URL', '').split('@')[0]}...")
        return True
    
    # Check if we have the credentials in a file
    repo_root = Path(settings.BASE_DIR).parent
    creds_file = repo_root / 'deployment' / 'postgres_credentials.json'
    
    if creds_file.exists():
        try:
            with open(creds_file, 'r') as f:
                creds = json.load(f)
                
                if 'DATABASE_URL' in creds:
                    os.environ['DATABASE_URL'] = creds['DATABASE_URL']
                    print("Set DATABASE_URL from credentials file")
                    return True
                else:
                    print("Credentials file doesn't contain DATABASE_URL")
        except Exception as e:
            print(f"Error reading credentials file: {str(e)}")
    
    # If we reach here, we couldn't set DATABASE_URL
    print("Failed to set DATABASE_URL. PostgreSQL cannot be used.")
    return False

def export_data_from_sqlite():
    """Export data from SQLite to a JSON file"""
    if not is_sqlite_active():
        print("SQLite is not currently active, cannot export data")
        return None
    
    try:
        # Create a backup of the current SQLite database
        timestamp = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        backup_file = f"sqlite_export_{timestamp}.json"
        
        print(f"Exporting SQLite data to {backup_file}...")
        call_command('dumpdata', output=backup_file)
        
        if os.path.exists(backup_file) and os.path.getsize(backup_file) > 100:
            print(f"SQLite data exported to {backup_file}")
            return backup_file
        else:
            print("Error: Export file is too small or doesn't exist")
            return None
    except Exception as e:
        print(f"Error exporting SQLite data: {str(e)}")
        return None

def save_postgres_credentials():
    """Save PostgreSQL credentials to a file for future use"""
    if not os.environ.get('DATABASE_URL'):
        print("DATABASE_URL not set, cannot save credentials")
        return False
    
    try:
        # Save credentials to deployment directory
        repo_root = Path(settings.BASE_DIR).parent
        deployment_dir = repo_root / 'deployment'
        os.makedirs(deployment_dir, exist_ok=True)
        
        creds_file = deployment_dir / 'postgres_credentials.json'
        
        # Save only the DATABASE_URL to avoid saving other sensitive credentials
        with open(creds_file, 'w') as f:
            json.dump({'DATABASE_URL': os.environ.get('DATABASE_URL')}, f)
        
        print(f"PostgreSQL credentials saved to {creds_file}")
        return True
    except Exception as e:
        print(f"Error saving PostgreSQL credentials: {str(e)}")
        return False

def migrate_to_postgres(data_file):
    """Migrate data from SQLite to PostgreSQL"""
    if not data_file or not os.path.exists(data_file):
        print("No data file available for migration")
        return False
    
    if not force_postgres_environment():
        print("Cannot migrate to PostgreSQL: DATABASE_URL not set")
        return False
    
    try:
        # Restart Django to use PostgreSQL
        print("Restarting Django with PostgreSQL settings...")
        import django
        django.setup()
        
        # Ensure migrations are applied
        print("Applying migrations to PostgreSQL...")
        call_command('migrate')
        
        # Load data into PostgreSQL
        print(f"Loading data from {data_file} into PostgreSQL...")
        call_command('loaddata', data_file)
        
        # Verify data was loaded
        counts = get_database_counts()
        print(f"PostgreSQL database now contains: {counts['teams']} teams, "
              f"{counts['players']} players, {counts['matches']} matches, "
              f"{counts['users']} users")
        
        # Save PostgreSQL credentials for future use
        save_postgres_credentials()
        
        return counts['teams'] > 0 and counts['players'] > 0
    except Exception as e:
        print(f"Error migrating to PostgreSQL: {str(e)}")
        return False

def main():
    print("Checking database configuration...")
    
    # Check if the database is using PostgreSQL
    if is_postgres_active():
        print("PostgreSQL is active. No migration needed.")
        
        # Save PostgreSQL credentials for future use
        if os.environ.get('DATABASE_URL'):
            save_postgres_credentials()
            
        sys.exit(0)
    
    # If SQLite is active, migrate to PostgreSQL
    if is_sqlite_active():
        print("SQLite is active. Attempting to migrate to PostgreSQL...")
        
        # Get current counts
        counts = get_database_counts()
        print(f"Current SQLite database contains: {counts['teams']} teams, "
              f"{counts['players']} players, {counts['matches']} matches, "
              f"{counts['users']} users")
        
        # Export data from SQLite
        data_file = export_data_from_sqlite()
        
        # Migrate to PostgreSQL
        if data_file:
            success = migrate_to_postgres(data_file)
            
            if success:
                print("Migration to PostgreSQL successful!")
                
                # Mark as production to ensure future restores use PostgreSQL
                repo_root = Path(settings.BASE_DIR).parent
                marker_path = repo_root / 'deployment' / 'IS_PRODUCTION_ENVIRONMENT'
                with open(marker_path, 'w') as f:
                    f.write(f"This instance was marked as production after PostgreSQL migration.\n")
                
                # Clean up
                try:
                    os.remove(data_file)
                    print(f"Removed temporary file {data_file}")
                except:
                    pass
                
                sys.exit(0)
            else:
                print("Migration to PostgreSQL failed!")
                sys.exit(1)
        else:
            print("Failed to export data from SQLite")
            sys.exit(1)
    
    print("Unknown database engine. Cannot ensure PostgreSQL use.")
    sys.exit(1)

if __name__ == "__main__":
    main()