#!/usr/bin/env python
"""
Force Deployment Restore Utility

This script forces restoration from deployment backups by directly copying
the database file from deployment backups to the active database.

Use this script as a last resort if the regular deployment restore process fails.
"""

import os
import sys
import shutil
import glob
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='Force restore from deployment backups')
    parser.add_argument('--dry-run', action='store_true',
                      help='Show what would be done without actually doing it')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Show detailed information')
    args = parser.parse_args()
    
    # Define paths
    deployment_dir = os.path.join(os.getcwd(), 'deployment')
    db_path = os.path.join(os.getcwd(), 'smorasfotball', 'db.sqlite3')
    
    print(f"Deployment directory: {deployment_dir}")
    print(f"Database path: {db_path}")
    
    # Check if deployment directory exists
    if not os.path.exists(deployment_dir):
        print(f"ERROR: Deployment directory not found at {deployment_dir}")
        return 1
    
    # List all backup files
    all_backups = []
    
    # Pattern 1: deployment_db.sqlite (primary backup)
    if os.path.exists(os.path.join(deployment_dir, 'deployment_db.sqlite')):
        backup = os.path.join(deployment_dir, 'deployment_db.sqlite')
        all_backups.append({
            'path': backup,
            'size': os.path.getsize(backup),
            'modified': os.path.getmtime(backup),
            'type': 'primary'
        })
    
    # Pattern 2: deployment_backup_*.sqlite (timestamped backups)
    for backup in glob.glob(os.path.join(deployment_dir, 'deployment_backup_*.sqlite')):
        all_backups.append({
            'path': backup,
            'size': os.path.getsize(backup),
            'modified': os.path.getmtime(backup),
            'type': 'timestamped'
        })
    
    # Pattern 3: deployment_backup_*.sqlite.*.bak (safety backups)
    for backup in glob.glob(os.path.join(deployment_dir, '*.sqlite.*.bak')):
        all_backups.append({
            'path': backup,
            'size': os.path.getsize(backup),
            'modified': os.path.getmtime(backup),
            'type': 'safety'
        })
    
    # Sort backups by modified time (newest first)
    all_backups.sort(key=lambda x: x['modified'], reverse=True)
    
    if not all_backups:
        print("ERROR: No deployment backups found!")
        return 1
    
    # Print backup information
    print(f"\nFound {len(all_backups)} backup files:")
    for i, backup in enumerate(all_backups):
        modified_time = datetime.fromtimestamp(backup['modified']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{i+1}. {os.path.basename(backup['path'])} - {backup['size']} bytes, modified: {modified_time} ({backup['type']})")
    
    # Select backup to use
    selected_backup = all_backups[0]  # Default to newest
    print(f"\nWill use the newest backup: {os.path.basename(selected_backup['path'])}")
    
    # Make a backup of the current database if it exists
    if os.path.exists(db_path) and not args.dry_run:
        backup_name = f"db.sqlite3.BEFORE_FORCE_RESTORE.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = os.path.join(os.path.dirname(db_path), backup_name)
        shutil.copy2(db_path, backup_path)
        print(f"Created backup of current database: {backup_name}")
    
    # Restore from the selected backup
    if args.dry_run:
        print(f"\nDRY RUN: Would restore from {os.path.basename(selected_backup['path'])} to {db_path}")
    else:
        try:
            # Make sure the database is closed by changing to a different directory
            os.chdir(os.path.dirname(os.path.dirname(db_path)))
            
            # Copy the backup file to the current database location
            print(f"\nRestoring from {os.path.basename(selected_backup['path'])} to {db_path}...")
            shutil.copy2(selected_backup['path'], db_path)
            
            # Update permissions
            os.chmod(db_path, 0o644)
            
            print(f"✅ Successfully restored database from deployment backup!")
            print(f"You should now run migrations to ensure the database schema is up to date:")
            print(f"cd smorasfotball && python manage.py migrate")
            
            return 0
        except Exception as e:
            print(f"ERROR during restoration: {str(e)}")
            return 1
    
if __name__ == "__main__":
    sys.exit(main())