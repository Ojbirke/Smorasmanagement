#!/usr/bin/env python
"""
Reset Deployment Backups Utility

This utility script helps reset the deployment backup environment for testing.
It will:
1. Delete all existing deployment backups
2. Create fresh deployment backups from the current development database

Use this ONLY in development to test deployment backup scenarios.
NEVER run this in production as it will delete your production backups!
"""

import os
import sys
import shutil
import glob
import argparse
from datetime import datetime
import subprocess

def main():
    parser = argparse.ArgumentParser(description='Reset deployment backups environment')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without actually doing it')
    parser.add_argument('--force', action='store_true',
                        help='Force operation without confirmation')
    parser.add_argument('--keep-backups', action='store_true',
                        help='Keep existing backups (skip deletion step)')
    args = parser.parse_args()
    
    print("=" * 50)
    print("DEPLOYMENT BACKUP RESET UTILITY")
    print("=" * 50)
    print(f"Current directory: {os.getcwd()}")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define paths
    deployment_dir = os.path.join(os.getcwd(), 'deployment')
    backup_dir = os.path.join(deployment_dir, 'backups')
    db_path = os.path.join(os.getcwd(), 'smorasfotball', 'db.sqlite3')
    
    # Check if required files exist
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        print("Cannot proceed without a database to backup.")
        return 1
    
    # Get confirmation unless force is specified
    if not args.force and not args.dry_run:
        print("\n⚠️  WARNING: This utility will reset all deployment backups.")
        print("This should ONLY be used in development to test deployment scenarios.")
        print("NEVER run this in production or you will lose all your deployment backups!\n")
        response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            print("Operation cancelled.")
            return 0
    
    # Create deployment directory if it doesn't exist
    if not os.path.exists(deployment_dir):
        if args.dry_run:
            print(f"Would create deployment directory: {deployment_dir}")
        else:
            os.makedirs(deployment_dir, exist_ok=True)
            print(f"Created deployment directory: {deployment_dir}")
    
    # Create backup directory
    if not os.path.exists(backup_dir):
        if args.dry_run:
            print(f"Would create backup directory: {backup_dir}")
        else:
            os.makedirs(backup_dir, exist_ok=True)
            print(f"Created backup directory: {backup_dir}")
    
    # Step 1: Delete existing deployment backups (if not keeping)
    if not args.keep_backups:
        print("\nStep 1: Removing existing deployment backups...")
        
        # Find all deployment backup files
        backup_files = []
        backup_files.extend(glob.glob(os.path.join(deployment_dir, 'deployment_db.*')))
        backup_files.extend(glob.glob(os.path.join(deployment_dir, '*.sqlite')))
        backup_files.extend(glob.glob(os.path.join(deployment_dir, '*.json')))
        backup_files.extend(glob.glob(os.path.join(backup_dir, '*')))
        
        # Remove marker files
        marker_files = [
            os.path.join(deployment_dir, 'IS_PRODUCTION_ENVIRONMENT'),
            os.path.join(deployment_dir, 'DEPLOYMENT_IN_PROGRESS')
        ]
        
        backup_files.extend([f for f in marker_files if os.path.exists(f)])
        
        if backup_files:
            print(f"Found {len(backup_files)} backup files to remove.")
            for f in backup_files:
                if args.dry_run:
                    print(f"Would remove: {f}")
                else:
                    try:
                        os.remove(f)
                        print(f"Removed: {f}")
                    except Exception as e:
                        print(f"Error removing {f}: {str(e)}")
        else:
            print("No existing backup files found.")
    else:
        print("Skipping backup deletion as --keep-backups was specified.")
    
    # Step 2: Create new deployment backups
    print("\nStep 2: Creating fresh deployment backups...")
    
    # Change to smorasfotball directory
    os.chdir('smorasfotball')
    
    # Create the SQLite backup
    print("Creating SQLite deployment backup...")
    cmd = ['python', 'manage.py', 'deployment_backup', '--format', 'sqlite']
    
    if args.dry_run:
        print(f"Would execute: {' '.join(cmd)}")
    else:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("SQLite deployment backup created successfully.")
                print(result.stdout)
            else:
                print("Error creating SQLite deployment backup:")
                print(result.stderr)
        except Exception as e:
            print(f"Exception during SQLite backup creation: {str(e)}")
    
    # Create the JSON backup for redundancy
    print("\nCreating JSON deployment backup for redundancy...")
    cmd = ['python', 'manage.py', 'deployment_backup', '--format', 'json']
    
    if args.dry_run:
        print(f"Would execute: {' '.join(cmd)}")
    else:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("JSON deployment backup created successfully.")
                print(result.stdout)
            else:
                print("Error creating JSON deployment backup:")
                print(result.stderr)
        except Exception as e:
            print(f"Exception during JSON backup creation: {str(e)}")
    
    # Verify the backups were created
    os.chdir('..')  # Go back to root directory
    
    sqlite_path = os.path.join(deployment_dir, 'deployment_db.sqlite')
    json_path = os.path.join(deployment_dir, 'deployment_db.json')
    
    print("\nVerifying backup files:")
    
    if os.path.exists(sqlite_path):
        file_size = os.path.getsize(sqlite_path)
        mod_time = datetime.fromtimestamp(os.path.getmtime(sqlite_path)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"SQLite backup: {sqlite_path}")
        print(f"  - Size: {file_size} bytes")
        print(f"  - Modified: {mod_time}")
    else:
        print("SQLite backup not found!")
    
    if os.path.exists(json_path):
        file_size = os.path.getsize(json_path)
        mod_time = datetime.fromtimestamp(os.path.getmtime(json_path)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"JSON backup: {json_path}")
        print(f"  - Size: {file_size} bytes")
        print(f"  - Modified: {mod_time}")
    else:
        print("JSON backup not found!")
    
    print("\nDeployment backup reset completed.")
    print("The deployment backup system is now ready for testing.")
    
    if args.dry_run:
        print("\nNOTE: This was a dry run. No actual changes were made.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())