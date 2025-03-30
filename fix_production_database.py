#!/usr/bin/env python3
"""
Fix Production Database

This is a standalone script designed to fix the production database configuration
when redeploying the application. Run this script in the production environment
after deployment to ensure that:

1. A PostgreSQL database is created and configured
2. Data is migrated from SQLite to PostgreSQL
3. The DATABASE_URL environment variable is set correctly

Usage:
    python fix_production_database.py

This script does not depend on Django being already set up correctly, so it's
safe to run when the application is failing to start due to database issues.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

def create_postgresql_database():
    """Create a PostgreSQL database in Replit"""
    print("Creating PostgreSQL database...")

    # Check if DATABASE_URL is already set
    db_url = os.environ.get('DATABASE_URL')
    if db_url and isinstance(db_url, str) and db_url.startswith('postgres'):
        print(f"PostgreSQL database already configured")
        return True
    
    # Check if we have PostgreSQL credentials
    if all(k in os.environ for k in ['PGDATABASE', 'PGUSER', 'PGPASSWORD', 'PGHOST', 'PGPORT']):
        # Construct DATABASE_URL
        db_url = (f"postgresql://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}@"
                 f"{os.environ['PGHOST']}:{os.environ['PGPORT']}/{os.environ['PGDATABASE']}")
        
        # Set DATABASE_URL environment variable
        os.environ['DATABASE_URL'] = db_url
        print(f"Created DATABASE_URL from PostgreSQL credentials")

        # Save to .env file
        with open('.env', 'a') as f:
            f.write(f"\nDATABASE_URL=\"{db_url}\"\n")
        
        print("Saved DATABASE_URL to .env file")
        return True
    
    # No existing PostgreSQL credentials, try to create a database
    try:
        print("Attempting to create a PostgreSQL database using Replit's database API...")
        
        # Try to use Replit's database button functionality
        result = subprocess.run([sys.executable, '-c', 
                   'from replit.database import DatabaseCreateRequest; ' +
                   'req = DatabaseCreateRequest(); print(req.database_type)'],
                   capture_output=True, text=True)
        
        print(f"Database creation result: {result.stdout.strip()}")
        
        # Give Replit time to create the database
        print("Waiting for database to be created...")
        time.sleep(5)
        
        # Check if environment variables were set
        if all(k in os.environ for k in ['PGDATABASE', 'PGUSER', 'PGPASSWORD', 'PGHOST', 'PGPORT']):
            # Construct DATABASE_URL
            db_url = (f"postgresql://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}@"
                     f"{os.environ['PGHOST']}:{os.environ['PGPORT']}/{os.environ['PGDATABASE']}")
            
            # Set DATABASE_URL environment variable
            os.environ['DATABASE_URL'] = db_url
            print(f"Created DATABASE_URL from newly created PostgreSQL credentials")
            
            # Save to .env file
            with open('.env', 'a') as f:
                f.write(f"\nDATABASE_URL=\"{db_url}\"\n")
            
            print("Saved DATABASE_URL to .env file")
            return True
    except Exception as e:
        print(f"Error creating PostgreSQL database: {e}")
    
    # If automatic creation fails, provide instructions
    print("\nCouldn't create PostgreSQL database automatically.")
    print("Please follow these manual steps:")
    print("1. Click on the 'Database' button in Replit's sidebar")
    print("2. Select 'PostgreSQL' as the database type")
    print("3. Click 'Create' to create a PostgreSQL database")
    print("4. Re-run this script after creating the database")
    
    return False

def create_credentials_file():
    """Create PostgreSQL credentials file for Django"""
    if not os.environ.get('DATABASE_URL'):
        print("DATABASE_URL not set, cannot create credentials file")
        return False
    
    try:
        # Save credentials to deployment directory
        deployment_dir = Path('deployment')
        deployment_dir.mkdir(exist_ok=True)
        
        creds_file = deployment_dir / 'postgres_credentials.json'
        
        # Save only the DATABASE_URL to avoid saving other sensitive credentials
        with open(creds_file, 'w') as f:
            json.dump({'DATABASE_URL': os.environ.get('DATABASE_URL')}, f)
        
        print(f"PostgreSQL credentials saved to {creds_file}")
        
        # Create a backup copy
        backup_file = deployment_dir / 'postgres_creds_backup.json'
        with open(backup_file, 'w') as f:
            json.dump({'DATABASE_URL': os.environ.get('DATABASE_URL')}, f)
        
        print(f"Backup credentials saved to {backup_file}")
        
        # Mark as production
        marker_path = deployment_dir / 'IS_PRODUCTION_ENVIRONMENT'
        with open(marker_path, 'w') as f:
            f.write(f"This instance was marked as production on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        perm_marker_path = deployment_dir / 'PERMANENT_PRODUCTION_MARKER'
        with open(perm_marker_path, 'w') as f:
            f.write(f"This instance was permanently marked as production on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        return True
    except Exception as e:
        print(f"Error creating credentials file: {e}")
        return False

def migrate_data():
    """Run the comprehensive database migration script"""
    try:
        print("Running comprehensive database migration script...")
        result = subprocess.run(['python', 'fix_production_postgres.py'], 
                              capture_output=True, text=True)
        
        print("Migration script output:")
        print(result.stdout)
        
        if result.returncode != 0:
            print("WARNING: Migration script returned non-zero exit code")
            print(f"Error output: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"Error running migration script: {e}")
        return False

def restart_django_server():
    """Restart the Django server"""
    try:
        print("Attempting to restart Django server...")
        # Kill any existing Django server processes
        subprocess.run(["pkill", "-f", "python manage.py runserver"], 
                      capture_output=True, text=True)
        
        # Restart server in background
        subprocess.Popen(["cd smorasfotball && python manage.py runserver 0.0.0.0:5000"],
                        shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("Django server restart initiated")
        return True
    except Exception as e:
        print(f"Error restarting Django server: {e}")
        return False

def main():
    print("=" * 60)
    print("PRODUCTION DATABASE FIX UTILITY")
    print("=" * 60)
    print("This script will:") 
    print("1. Create a PostgreSQL database if needed")
    print("2. Set up DATABASE_URL environment variable")
    print("3. Migrate data from SQLite to PostgreSQL")
    print("4. Restart the Django server")
    print("=" * 60)
    
    # Step 1: Create PostgreSQL database
    if not create_postgresql_database():
        print("Failed to create PostgreSQL database")
        return False
    
    # Step 2: Create credentials file for Django
    if not create_credentials_file():
        print("Failed to create credentials file")
        print("Continuing anyway...")
    
    # Step 3: Migrate data
    if not migrate_data():
        print("WARNING: Data migration may not have completed successfully")
        print("Continuing anyway...")
    
    # Step 4: Restart Django server
    if not restart_django_server():
        print("WARNING: Failed to restart Django server")
        print("You may need to restart the server manually")
    
    print("=" * 60)
    print("Database fix process completed")
    print("To verify that PostgreSQL is being used, run:")
    print("  cd smorasfotball && python manage.py dbstatus")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)