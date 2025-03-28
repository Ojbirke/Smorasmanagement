#!/usr/bin/env python3
"""
Test Backup Sync Script

This script tests the GitHub-based backup sync approach by creating a backup
and then pushing it to the repository via the sync_backups_with_repo command.
"""

import os
import sys
import django
import subprocess
from datetime import datetime

def main():
    """Test the backup sync process"""
    print("=" * 60)
    print("TESTING GITHUB-BASED BACKUP SYNC SYSTEM")
    print("=" * 60)
    print(f"Current time: {datetime.now()}")
    
    # Setup Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'smorasfotball'))
    
    try:
        django.setup()
    except Exception as e:
        print(f"Error setting up Django: {str(e)}")
        return False
    
    # Create a test backup
    print("\nStep 1: Creating test backup...")
    try:
        result = subprocess.run(
            ['python', 'smorasfotball/manage.py', 'deployment_backup', '--name', 'test_sync', '--format', 'sqlite'],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"Error creating backup: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running deployment_backup command: {str(e)}")
        return False
    
    # Verify backup file exists
    deployment_dir = os.path.join(os.path.dirname(__file__), 'deployment')
    sqlite_path = os.path.join(deployment_dir, 'deployment_db.sqlite')
    if not os.path.exists(sqlite_path):
        print(f"Error: Backup file not created at {sqlite_path}")
        return False
    
    print(f"Backup created successfully: {sqlite_path}")
    print(f"Backup size: {os.path.getsize(sqlite_path)} bytes")
    
    # Store modification time for comparison
    mod_time_before = os.path.getmtime(sqlite_path)
    print(f"Backup modification time: {datetime.fromtimestamp(mod_time_before)}")
    
    # Push backup to repo
    print("\nStep 2: Pushing backup to repository...")
    try:
        result = subprocess.run(
            ['python', 'smorasfotball/manage.py', 'sync_backups_with_repo', '--push'],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"Error pushing to repository: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running sync_backups_with_repo command: {str(e)}")
        return False
    
    # Simulate redeployment by renaming backup file
    print("\nStep 3: Simulating redeployment (renaming backup file)...")
    try:
        if os.path.exists(sqlite_path):
            temp_backup = f"{sqlite_path}.temp"
            os.rename(sqlite_path, temp_backup)
            print(f"Renamed backup to {temp_backup}")
        else:
            print(f"Warning: Backup file not found at {sqlite_path}")
    except Exception as e:
        print(f"Error renaming backup file: {str(e)}")
        return False
    
    # Pull backup from repo
    print("\nStep 4: Pulling backup from repository...")
    try:
        result = subprocess.run(
            ['python', 'smorasfotball/manage.py', 'sync_backups_with_repo', '--pull'],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"Error pulling from repository: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running sync_backups_with_repo command: {str(e)}")
        return False
    
    # Verify backup file was restored
    if not os.path.exists(sqlite_path):
        print(f"Error: Backup file not restored at {sqlite_path}")
        return False
    
    mod_time_after = os.path.getmtime(sqlite_path)
    print(f"Restored backup modification time: {datetime.fromtimestamp(mod_time_after)}")
    
    # Cleanup
    print("\nStep 5: Cleaning up test files...")
    try:
        if os.path.exists(temp_backup):
            os.remove(temp_backup)
            print(f"Removed temporary backup: {temp_backup}")
    except Exception as e:
        print(f"Error cleaning up temporary files: {str(e)}")
    
    # Final verification
    print("\nTest Results:")
    if os.path.exists(sqlite_path):
        print("✅ SUCCESS: The GitHub-based backup sync system is working!")
        print(f"✅ Backup file exists: {sqlite_path}")
        print(f"✅ Backup size: {os.path.getsize(sqlite_path)} bytes")
        return True
    else:
        print("❌ FAILURE: The backup sync system is not working properly.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)