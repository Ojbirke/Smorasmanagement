#!/usr/bin/env python3
"""
Configure External PostgreSQL Database

This script configures the application to use an external PostgreSQL database.
It creates the necessary environment variables and configuration files to
connect to the specified PostgreSQL database without migrating data from SQLite.

Usage:
    python configure_external_postgres.py [database_name] [host] [user] [password] [port]

    If parameters are not provided, they will be prompted for interactively.
"""

import os
import sys
import json
import getpass
from pathlib import Path

# Default values for the external database
DEFAULT_DB_NAME = "myteamsno_smorasg2015"
DEFAULT_DB_HOST = "localhost"  # Change this to your external host
DEFAULT_DB_PORT = "5432"
DEFAULT_DB_USER = "postgres"   # Change this to your external database user

def get_connection_params():
    """Get database connection parameters from command line or user input"""
    if len(sys.argv) >= 6:
        db_name = sys.argv[1]
        db_host = sys.argv[2]
        db_user = sys.argv[3]
        db_password = sys.argv[4]
        db_port = sys.argv[5]
    else:
        print("Please provide the external PostgreSQL database connection details:")
        db_name = input(f"Database name [{DEFAULT_DB_NAME}]: ") or DEFAULT_DB_NAME
        db_host = input(f"Database host [{DEFAULT_DB_HOST}]: ") or DEFAULT_DB_HOST
        db_user = input(f"Database user [{DEFAULT_DB_USER}]: ") or DEFAULT_DB_USER
        db_password = getpass.getpass("Database password: ")
        db_port = input(f"Database port [{DEFAULT_DB_PORT}]: ") or DEFAULT_DB_PORT
    
    return {
        'name': db_name,
        'host': db_host,
        'user': db_user,
        'password': db_password,
        'port': db_port
    }

def create_database_url(db_params):
    """Create PostgreSQL database URL from parameters"""
    return f"postgres://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['name']}"

def save_database_url(db_url):
    """Save DATABASE_URL to .env file and current environment"""
    # Save to .env file for persistence
    env_path = Path('.env')
    
    if env_path.exists():
        # Read existing .env file
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Replace DATABASE_URL if it exists, otherwise append
        database_url_exists = False
        for i, line in enumerate(lines):
            if line.startswith('DATABASE_URL='):
                lines[i] = f"DATABASE_URL={db_url}\n"
                database_url_exists = True
                break
        
        if not database_url_exists:
            lines.append(f"DATABASE_URL={db_url}\n")
        
        # Write back to .env file
        with open(env_path, 'w') as f:
            f.writelines(lines)
    else:
        # Create new .env file
        with open(env_path, 'w') as f:
            f.write(f"DATABASE_URL={db_url}\n")
    
    # Set in current environment
    os.environ['DATABASE_URL'] = db_url
    
    print(f"Database URL saved to .env file and set in current environment")

def disable_auto_restore():
    """Disable auto restore functionality to prevent SQLite migration"""
    # Create a marker file to skip auto-restore
    skip_restore_path = Path('deployment/SKIP_DB_RESTORE')
    skip_restore_path.parent.mkdir(exist_ok=True)
    skip_restore_path.touch()
    
    print(f"Auto-restore functionality disabled. No data will be migrated from SQLite.")

def verify_settings():
    """Verify the Django settings will use the external PostgreSQL database"""
    try:
        # Add Django project to path
        BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball')
        sys.path.append(BASE_DIR)
        
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
        
        import django
        django.setup()
        from django.conf import settings
        
        # Verify the database settings
        db_settings = settings.DATABASES['default']
        engine = db_settings.get('ENGINE', '')
        
        if 'postgresql' in engine:
            print("Database ENGINE is correctly set to PostgreSQL")
            return True
        else:
            print(f"Warning: Database ENGINE is not set to PostgreSQL: {engine}")
            return False
    except Exception as e:
        print(f"Error verifying Django settings: {e}")
        return False

def main():
    """Main function to configure the external PostgreSQL database"""
    print("Configuring external PostgreSQL database connection")
    
    # Get database connection parameters
    db_params = get_connection_params()
    
    # Create database URL
    db_url = create_database_url(db_params)
    
    # Save database URL
    save_database_url(db_url)
    
    # Disable auto-restore
    disable_auto_restore()
    
    # Mark as production environment
    prod_marker_path = Path('deployment/IS_PRODUCTION_ENVIRONMENT')
    prod_marker_path.parent.mkdir(exist_ok=True)
    prod_marker_path.touch()
    
    # Verify settings
    if verify_settings():
        print("\nExternal PostgreSQL database configuration complete!")
        print("The application will now use the external database without migrating data from SQLite.")
        print("\nYou should now run the following commands:")
        print("1. cd smorasfotball")
        print("2. python manage.py migrate")
        print("3. python manage.py createsuperuser")
    else:
        print("\nWarning: There might be issues with the database configuration.")
        print("Please check the settings.py file and ensure it uses the DATABASE_URL environment variable.")

if __name__ == "__main__":
    main()