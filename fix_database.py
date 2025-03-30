#!/usr/bin/env python3
"""
Database Issue Detection and Fixing Tool

This script checks for common database issues and offers fixes:
1. Detects if SQLite is being used instead of PostgreSQL
2. Checks for missing teams or players
3. Provides options to fix detected issues

Usage:
    python fix_database.py [--auto-fix]

Options:
    --auto-fix    Automatically attempt to fix any issues found
"""

import os
import sys
import argparse
import subprocess
import json
import time
from pathlib import Path

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
        from django.conf import settings
        
        print("Django environment set up successfully.")
        return True
    except ImportError as e:
        print(f"Error: Django could not be imported: {e}")
        return False
    except Exception as e:
        print(f"Error setting up Django: {e}")
        return False

def detect_database_engine():
    """Detect current database engine"""
    try:
        from django.conf import settings
        
        db_config = settings.DATABASES['default']
        engine = db_config.get('ENGINE', '')
        name = db_config.get('NAME', '')
        
        print(f"Current database engine: {engine}")
        print(f"Database name: {name}")
        
        if 'postgresql' in engine.lower():
            print("PostgreSQL is being used. Good!")
            return 'postgresql'
        elif 'sqlite' in engine.lower():
            print("WARNING: SQLite is being used instead of PostgreSQL.")
            return 'sqlite'
        else:
            print(f"Unknown database engine: {engine}")
            return 'unknown'
    except Exception as e:
        print(f"Error detecting database engine: {e}")
        return 'unknown'

def check_database_content():
    """Check if the database has expected content"""
    try:
        # Import models
        from django.contrib.auth.models import User
        from teammanager.models import Team, Player, Match
        
        teams = Team.objects.count()
        players = Player.objects.count()
        matches = Match.objects.count()
        users = User.objects.count()
        
        print(f"Database contains:")
        print(f"  Teams: {teams}")
        print(f"  Players: {players}")
        print(f"  Matches: {matches}")
        print(f"  Users: {users}")
        
        issues = []
        
        if teams == 0:
            issues.append("No teams found in the database.")
        
        if players == 0:
            issues.append("No players found in the database.")
        
        if matches == 0:
            issues.append("No matches found in the database.")
        
        if users == 0:
            issues.append("No users found in the database.")
        
        if issues:
            print("\nIssues detected:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("\nDatabase content looks good!")
            return True
    except Exception as e:
        print(f"Error checking database content: {e}")
        return False

def fix_sqlite_to_postgres():
    """Attempt to fix SQLite to PostgreSQL migration"""
    print("\nAttempting to migrate from SQLite to PostgreSQL...")
    
    # Check if the PostgreSQL migration script exists
    script_path = Path(__file__).parent / 'force_postgres_migration.py'
    
    if not script_path.exists():
        print(f"Error: PostgreSQL migration script not found at {script_path}")
        return False
    
    # Check if DATABASE_URL is set
    if not os.environ.get('DATABASE_URL'):
        print("Error: DATABASE_URL environment variable is not set.")
        print("You must set DATABASE_URL to a valid PostgreSQL connection string.")
        return False
    
    # Run the migration script
    try:
        print("Running PostgreSQL migration script...")
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True)
        
        print("\nMigration script output:")
        print(result.stdout)
        
        if result.stderr:
            print("\nErrors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\nMigration to PostgreSQL completed successfully!")
            return True
        else:
            print(f"\nMigration to PostgreSQL failed with exit code {result.returncode}")
            return False
    except Exception as e:
        print(f"Error running migration script: {e}")
        return False

def fix_missing_content():
    """Attempt to fix missing database content"""
    print("\nAttempting to restore database content...")
    
    # Check for deployment backup
    deployment_dir = Path(__file__).parent / 'deployment'
    backup_file = deployment_dir / 'deployment_db.json'
    
    if backup_file.exists() and backup_file.stat().st_size > 100:
        print(f"Found deployment backup: {backup_file}")
        
        try:
            # Load the backup using loaddata
            from django.core.management import call_command
            
            print(f"Loading data from {backup_file}...")
            call_command('loaddata', str(backup_file))
            
            # Verify content was loaded
            if check_database_content():
                print("\nDatabase content successfully restored!")
                return True
            else:
                print("\nDatabase content still has issues after restoration.")
                return False
        except Exception as e:
            print(f"Error loading backup: {e}")
            return False
    else:
        print("No valid deployment backup found.")
        
        # Try to create default data
        try:
            # Run migrations
            from django.core.management import call_command
            
            print("Running migrations...")
            call_command('migrate')
            
            # Run the data creation script if it exists
            create_data_script = Path(__file__).parent / 'smorasfotball' / 'create_complete_data.py'
            
            if create_data_script.exists():
                print("Running data creation script...")
                subprocess.run([sys.executable, str(create_data_script)], check=True)
                
                # Verify content was created
                if check_database_content():
                    print("\nDefault database content successfully created!")
                    return True
                else:
                    print("\nDatabase content still has issues after creation.")
                    return False
            else:
                print(f"Data creation script not found at {create_data_script}")
                return False
        except Exception as e:
            print(f"Error creating default data: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Check and fix database issues.')
    parser.add_argument('--auto-fix', action='store_true', help='Automatically fix detected issues')
    
    args = parser.parse_args()
    
    print("Starting database issue detection...")
    
    # Set up Django
    if not setup_django():
        print("Failed to set up Django environment. Aborting.")
        sys.exit(1)
    
    # Check database engine
    engine = detect_database_engine()
    engine_ok = engine == 'postgresql'
    
    # Check database content
    content_ok = check_database_content()
    
    # Overall status
    status_ok = engine_ok and content_ok
    
    if status_ok:
        print("\nNo database issues detected!")
        sys.exit(0)
    
    # Ask for confirmation unless auto-fix is enabled
    if not args.auto_fix:
        choice = input("\nWould you like to attempt to fix these issues? (y/n): ")
        if choice.lower() != 'y':
            print("No changes made. Exiting.")
            sys.exit(1)
    
    # Fix issues
    fixes_applied = False
    
    # Fix database engine
    if not engine_ok:
        if fix_sqlite_to_postgres():
            fixes_applied = True
            # Re-check database content after engine change
            content_ok = check_database_content()
    
    # Fix database content
    if not content_ok:
        if fix_missing_content():
            fixes_applied = True
    
    # Check final status
    if fixes_applied:
        print("\nFixes applied. Checking final status...")
        
        # Refresh Django connection
        setup_django()
        
        engine_ok = detect_database_engine() == 'postgresql'
        content_ok = check_database_content()
        status_ok = engine_ok and content_ok
        
        if status_ok:
            print("\nAll issues fixed successfully!")
            sys.exit(0)
        else:
            print("\nSome issues still remain. Manual intervention may be required.")
            sys.exit(1)
    else:
        print("\nNo fixes were successful. Manual intervention is required.")
        sys.exit(1)

if __name__ == '__main__':
    main()