#!/usr/bin/env python3
"""
Force PostgreSQL Migration Utility

This script forces the application to migrate data from SQLite to PostgreSQL.
Use this script if the automatic migration during deployment did not work.

Usage:
    python force_postgres_migration.py

Requirements:
    - Valid DATABASE_URL environment variable pointing to a PostgreSQL database
    - Django application with models for Player, Team, Match, etc.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
import time

def check_postgres_url():
    """Check if DATABASE_URL is set for PostgreSQL"""
    db_url = os.environ.get('DATABASE_URL', '')
    
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        print("You must set DATABASE_URL to a valid PostgreSQL connection string.")
        return False
    
    if 'postgresql' not in db_url.lower():
        print(f"ERROR: DATABASE_URL does not appear to be a PostgreSQL connection.")
        print("The connection string should start with 'postgresql://'")
        return False
    
    print(f"PostgreSQL DATABASE_URL found: {db_url.split('@')[0]}...")
    return True

def setup_django():
    """Set up Django environment"""
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
        
        print("Django environment set up successfully.")
        return True
    except ImportError as e:
        print(f"Error: Django could not be imported: {e}")
        print("Make sure Django is installed.")
        return False
    except Exception as e:
        print(f"Error setting up Django: {e}")
        return False

def detect_database_engine():
    """Detect which database engine is currently being used"""
    try:
        from django.conf import settings
        
        engine = settings.DATABASES['default'].get('ENGINE', '')
        print(f"Current database engine: {engine}")
        
        if 'postgresql' in engine.lower():
            print("PostgreSQL is already being used.")
            return 'postgresql'
        elif 'sqlite' in engine.lower():
            print("SQLite is currently being used.")
            return 'sqlite'
        else:
            print(f"Unknown database engine: {engine}")
            return 'unknown'
    except Exception as e:
        print(f"Error detecting database engine: {e}")
        return 'unknown'

def export_sqlite_data():
    """Export data from SQLite to a JSON file"""
    try:
        # Create a backup of the current SQLite database
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_file = f"sqlite_export_{timestamp}.json"
        
        print(f"Exporting SQLite data to {backup_file}...")
        
        from django.core.management import call_command
        call_command('dumpdata', output=backup_file)
        
        if os.path.exists(backup_file) and os.path.getsize(backup_file) > 100:
            print(f"SQLite data exported to {backup_file} ({os.path.getsize(backup_file)} bytes)")
            return backup_file
        else:
            print("Error: Export file is too small or doesn't exist")
            return None
    except Exception as e:
        print(f"Error exporting SQLite data: {e}")
        return None

def save_postgres_credentials():
    """Save PostgreSQL credentials to a file for future use"""
    if not os.environ.get('DATABASE_URL'):
        print("DATABASE_URL not set, cannot save credentials")
        return False
    
    try:
        # Save credentials to deployment directory
        deployment_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deployment')
        os.makedirs(deployment_dir, exist_ok=True)
        
        creds_file = os.path.join(deployment_dir, 'postgres_credentials.json')
        
        # Save only the DATABASE_URL to avoid saving other sensitive credentials
        with open(creds_file, 'w') as f:
            json.dump({'DATABASE_URL': os.environ.get('DATABASE_URL')}, f)
        
        print(f"PostgreSQL credentials saved to {creds_file}")
        
        # Update the IS_PRODUCTION_ENVIRONMENT marker
        marker_path = os.path.join(deployment_dir, 'IS_PRODUCTION_ENVIRONMENT')
        with open(marker_path, 'w') as f:
            f.write(f"This instance was marked as production after PostgreSQL migration on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print("Environment marked as production")
        return True
    except Exception as e:
        print(f"Error saving PostgreSQL credentials: {e}")
        return False

def get_database_counts():
    """Get counts of objects in the database"""
    try:
        # Get models
        from django.contrib.auth.models import User
        from teammanager.models import Team, Player, Match
        
        teams = Team.objects.count()
        players = Player.objects.count()
        matches = Match.objects.count()
        users = User.objects.count()
        
        print(f"Database contains: {teams} teams, {players} players, {matches} matches, {users} users")
        
        return {
            'teams': teams,
            'players': players,
            'matches': matches,
            'users': users,
        }
    except Exception as e:
        print(f"Error counting database objects: {e}")
        return {'teams': 0, 'players': 0, 'matches': 0, 'users': 0}

def migrate_to_postgres(data_file):
    """Migrate data from SQLite to PostgreSQL"""
    if not data_file or not os.path.exists(data_file):
        print("No data file available for migration")
        return False
    
    try:
        # Apply migrations to PostgreSQL to ensure tables exist
        print("Applying migrations to PostgreSQL...")
        from django.core.management import call_command
        call_command('migrate')
        
        # Load data into PostgreSQL
        print(f"Loading data from {data_file} into PostgreSQL...")
        call_command('loaddata', data_file)
        
        # Verify data was loaded
        counts = get_database_counts()
        
        # Save PostgreSQL credentials for future use
        save_postgres_credentials()
        
        print("Migration to PostgreSQL completed successfully!")
        
        return counts['teams'] > 0 and counts['players'] > 0
    except Exception as e:
        print(f"Error migrating to PostgreSQL: {e}")
        return False

def main():
    print("Starting force migration to PostgreSQL...")
    
    # Check if PostgreSQL URL is set
    if not check_postgres_url():
        print("Aborting migration: DATABASE_URL is not set or invalid.")
        sys.exit(1)
    
    # Set up Django
    if not setup_django():
        print("Aborting migration: Failed to set up Django environment.")
        sys.exit(1)
    
    # Detect current database engine
    engine = detect_database_engine()
    
    if engine == 'postgresql':
        print("PostgreSQL is already being used. No migration needed.")
        
        # Still save credentials for future use
        save_postgres_credentials()
        
        # Check database contents
        get_database_counts()
        
        sys.exit(0)
    
    if engine == 'sqlite':
        print("SQLite is being used. Starting migration to PostgreSQL...")
        
        # Get current database state
        print("Checking current database state:")
        get_database_counts()
        
        # Export SQLite data
        data_file = export_sqlite_data()
        
        if not data_file:
            print("Aborting migration: Failed to export SQLite data.")
            sys.exit(1)
        
        # Migrate to PostgreSQL
        if migrate_to_postgres(data_file):
            print("Migration to PostgreSQL completed successfully!")
            
            # Clean up
            try:
                os.remove(data_file)
                print(f"Removed temporary file {data_file}")
            except:
                pass
            
            sys.exit(0)
        else:
            print("Migration to PostgreSQL failed.")
            sys.exit(1)
    
    print("Aborting migration: Unknown or unsupported database engine.")
    sys.exit(1)

if __name__ == "__main__":
    main()