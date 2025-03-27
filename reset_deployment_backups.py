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
import argparse
import glob
import subprocess
import shutil
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='Reset deployment backup environment for testing')
    parser.add_argument('--force', action='store_true', 
                        help='Force deletion of existing backups without confirmation')
    parser.add_argument('--create-only', action='store_true',
                        help='Only create new backups without deleting existing ones')
    args = parser.parse_args()
    
    # Check if the deployment directory exists
    deployment_dir = os.path.join(os.getcwd(), 'deployment')
    if not os.path.exists(deployment_dir):
        print(f"Creating deployment directory: {deployment_dir}")
        os.makedirs(deployment_dir)
    
    # Delete existing backups if not in create-only mode
    if not args.create_only:
        backup_files = glob.glob(os.path.join(deployment_dir, 'deployment_*.sqlite')) + \
                       glob.glob(os.path.join(deployment_dir, 'deployment_*.json')) + \
                       glob.glob(os.path.join(deployment_dir, 'deployment_db.*'))
        
        if backup_files:
            print(f"Found {len(backup_files)} existing deployment backups:")
            for f in backup_files:
                print(f"  - {os.path.basename(f)}")
            
            # Ask for confirmation unless forced
            if not args.force:
                confirm = input("WARNING: This will delete all deployment backups. Continue? (y/n): ")
                if confirm.lower() != 'y':
                    print("Operation cancelled.")
                    return
            
            # Delete the backup files
            for f in backup_files:
                try:
                    os.remove(f)
                    print(f"Deleted: {os.path.basename(f)}")
                except Exception as e:
                    print(f"Error deleting {f}: {str(e)}")
            
            print("All deployment backups have been deleted.")
        else:
            print("No existing deployment backups found.")
    
    # Create new deployment backups
    print("\nCreating new deployment backups from development database...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Move to the Django project directory
    os.chdir('smorasfotball')
    
    # Try to create SQLite backup
    print("Creating SQLite backup...")
    sqlite_result = subprocess.run(
        ['python', 'manage.py', 'deployment_backup', '--name', f'reset_{timestamp}', '--format', 'sqlite'],
        capture_output=True,
        text=True
    )
    
    if sqlite_result.returncode == 0:
        print("SQLite backup created successfully.")
        print(sqlite_result.stdout)
    else:
        print("Error creating SQLite backup:")
        print(sqlite_result.stderr)
    
    # Try to create JSON backup
    print("\nCreating JSON backup...")
    json_result = subprocess.run(
        ['python', 'manage.py', 'deployment_backup', '--name', f'reset_{timestamp}', '--format', 'json'],
        capture_output=True,
        text=True
    )
    
    if json_result.returncode == 0:
        print("JSON backup created successfully.")
        print(json_result.stdout)
    else:
        print("Error creating JSON backup:")
        print(json_result.stderr)
    
    # Verify the backups were created
    os.chdir('..')
    new_backups = glob.glob(os.path.join(deployment_dir, 'deployment_*.sqlite')) + \
                  glob.glob(os.path.join(deployment_dir, 'deployment_*.json')) + \
                  glob.glob(os.path.join(deployment_dir, 'deployment_db.*'))
    
    if new_backups:
        print("\nNew deployment backups:")
        for f in new_backups:
            print(f"  - {os.path.basename(f)}")
        print("\nBackup reset completed successfully!")
    else:
        print("\nWARNING: No new backups were found after creation attempts.")
    
    print("\nIMPORTANT: This utility is for development testing only.")
    print("When deploying to production, use the normal deployment process.")

if __name__ == "__main__":
    main()