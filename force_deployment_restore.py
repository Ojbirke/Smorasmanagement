#!/usr/bin/env python3
"""
Force Deployment Restore Utility

This script forces restoration from deployment backups by directly copying
the database file from deployment backups to the active database.

Use this script as a last resort if the regular deployment restore process fails.
"""

import os
import sys
import json
import shutil
import logging
import datetime
from pathlib import Path

# Configure logging
log_filename = f"deployment_restore_debug_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add Django project to path
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball')
sys.path.append(BASE_DIR)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')

try:
    import django
    django.setup()
    from django.conf import settings
except ImportError:
    logging.error("Error: Django could not be imported. Make sure Django is installed.")
    sys.exit(1)

def find_latest_db_backup():
    """Find the latest database backup file"""
    logging.info("Looking for database backup files")
    
    # Define deployment directory
    repo_root = Path(__file__).parent
    deployment_dir = repo_root / 'deployment'
    
    if not deployment_dir.exists():
        logging.error(f"Deployment directory not found: {deployment_dir}")
        return None
    
    # Look for SQLite deployment backup
    sqlite_backups = list(deployment_dir.glob('*.sqlite3'))
    if sqlite_backups:
        # Sort by modification time, newest first
        sqlite_backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_sqlite = sqlite_backups[0]
        logging.info(f"Found SQLite backup: {latest_sqlite}")
        return latest_sqlite
    
    # Look for JSON backup
    json_backups = list(deployment_dir.glob('*.json'))
    if json_backups:
        # Sort by modification time, newest first
        json_backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_json = json_backups[0]
        logging.info(f"Found JSON backup: {latest_json}")
        return latest_json
    
    logging.error("No database backup files found")
    return None

def backup_current_db():
    """Backup the current database file"""
    try:
        db_path = settings.DATABASES['default']['NAME']
        db_backup_path = f"{db_path}.backup.{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logging.info(f"Backing up current database from {db_path} to {db_backup_path}")
        
        # Only backup if the file exists
        if os.path.exists(db_path):
            shutil.copy2(db_path, db_backup_path)
            logging.info(f"Database backup created: {db_backup_path}")
            return db_backup_path
        else:
            logging.warning(f"Current database file doesn't exist: {db_path}")
            return None
    except Exception as e:
        logging.error(f"Error backing up database: {str(e)}")
        return None

def restore_sqlite_backup(backup_path, db_path):
    """Restore database from SQLite backup file"""
    try:
        logging.info(f"Copying SQLite backup from {backup_path} to {db_path}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Copy the backup file to the database location
        shutil.copy2(backup_path, db_path)
        
        logging.info("SQLite database restored successfully")
        return True
    except Exception as e:
        logging.error(f"Error restoring SQLite database: {str(e)}")
        return False

def restore_json_backup(backup_path):
    """Restore database from JSON backup file using Django loaddata"""
    try:
        # We need to use Django's loaddata to restore from JSON
        logging.info(f"Restoring from JSON backup: {backup_path}")
        
        # We need to call this as a shell command since we're potentially
        # executing from the script directly
        command = f"cd {BASE_DIR} && python manage.py flush --no-input && python manage.py loaddata {backup_path}"
        logging.info(f"Executing: {command}")
        
        return_code = os.system(command)
        if return_code == 0:
            logging.info("JSON database restored successfully")
            return True
        else:
            logging.error(f"Error restoring database. Return code: {return_code}")
            return False
    except Exception as e:
        logging.error(f"Error in restore_json_backup: {str(e)}")
        return False

def main():
    logging.info("Starting force_deployment_restore.py")
    print("Starting forced deployment restore process...")
    
    # Find the latest backup
    backup_path = find_latest_db_backup()
    if not backup_path:
        print("Error: No backup files found. Cannot restore.")
        logging.error("No backup files found. Cannot restore.")
        sys.exit(1)
        
    # Get database path from Django settings
    db_path = settings.DATABASES['default']['NAME']
    
    # Backup current database (if it exists)
    backup_current_db()
    
    # Restore based on file type
    if str(backup_path).endswith('.sqlite3'):
        print(f"Restoring from SQLite backup: {backup_path}")
        success = restore_sqlite_backup(backup_path, db_path)
    elif str(backup_path).endswith('.json'):
        print(f"Restoring from JSON backup: {backup_path}")
        success = restore_json_backup(backup_path)
    else:
        print(f"Error: Unknown backup file format: {backup_path}")
        logging.error(f"Unknown backup file format: {backup_path}")
        sys.exit(1)
    
    if success:
        print("Database restoration completed successfully!")
        logging.info("Database restoration completed successfully")
        return 0
    else:
        print("Error: Database restoration failed. Check the logs for details.")
        logging.error("Database restoration failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)