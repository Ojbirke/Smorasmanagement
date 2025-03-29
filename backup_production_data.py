#!/usr/bin/env python3
"""
Backup Production Data

This script creates a backup of the current database and marks the environment as production.
Use it when you have made important changes in production that you want to preserve
across future deployments.

Usage:
    python backup_production_data.py
"""

import os
import sys
import time
from pathlib import Path

# Add Django project to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball'))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')

try:
    import django
    django.setup()
    from django.core.management import call_command
    from django.conf import settings
    from django.contrib.auth.models import User
    from teammanager.models import Team, Player, Match
except ImportError:
    print("Error: Django could not be imported. Make sure Django is installed.")
    sys.exit(1)

def count_database_objects():
    """Count objects in the current database"""
    return {
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
        'matches': Match.objects.count(),
        'users': User.objects.count(),
    }

def mark_as_production():
    """Mark this instance as production"""
    print("Marking instance as production...")
    
    # Define deployment directory
    repo_root = Path(settings.BASE_DIR).parent
    deployment_dir = repo_root / 'deployment'
    os.makedirs(deployment_dir, exist_ok=True)
    
    # Create IS_PRODUCTION_ENVIRONMENT marker file
    marker_path = deployment_dir / 'IS_PRODUCTION_ENVIRONMENT'
    with open(marker_path, 'w') as f:
        f.write(f"This instance was marked as production on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print("✅ Production marker created")
    return True

def create_backup():
    """Create a backup of the current database"""
    print("Creating backup of current database...")
    
    # Define deployment directory
    repo_root = Path(settings.BASE_DIR).parent
    deployment_dir = repo_root / 'deployment'
    os.makedirs(deployment_dir, exist_ok=True)
    
    # Create backup path
    backup_path = deployment_dir / 'deployment_db.json'
    
    try:
        # Create backup using Django's dumpdata
        print(f"Backing up database to {backup_path}...")
        call_command('dumpdata', output=str(backup_path))
        
        # Verify backup exists and has content
        if not os.path.exists(backup_path):
            print("❌ Error: Backup file not created!")
            return False
        
        backup_size = os.path.getsize(backup_path)
        if backup_size < 100:
            print(f"⚠️ Warning: Backup file is suspiciously small ({backup_size} bytes)!")
            return False
            
        print(f"✅ Backup created successfully! Size: {backup_size} bytes")
        
        # Also create a timestamp-marked backup for safety
        timestamp_backup = deployment_dir / f'deployment_db_{time.strftime("%Y%m%d_%H%M%S")}.json'
        os.system(f'cp "{backup_path}" "{timestamp_backup}"')
        print(f"✅ Additional timestamped backup created: {timestamp_backup}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error creating backup: {str(e)}")
        return False

def main():
    print("\n=== Production Data Backup Tool ===\n")
    
    # Count database objects
    db_state = count_database_objects()
    print("Current database state:")
    print(f"  Teams: {db_state['teams']}")
    print(f"  Players: {db_state['players']}")
    print(f"  Matches: {db_state['matches']}")
    print(f"  Users: {db_state['users']}")
    print("")
    
    # Check if database has content
    if db_state['teams'] == 0 and db_state['players'] == 0:
        print("⚠️ Warning: Database appears to be empty! Nothing to backup.")
        confirm = input("Continue anyway? (y/n): ")
        if confirm.lower() != 'y':
            print("Backup cancelled.")
            return False
    
    # Mark as production
    mark_as_production()
    
    # Create backup
    backup_success = create_backup()
    
    if backup_success:
        print("\n✅ PRODUCTION DATA BACKUP COMPLETE!")
        print("Your database has been backed up and this environment is marked as production.")
        print("Future deployments will preserve this data instead of overwriting it.")
        return True
    else:
        print("\n❌ PRODUCTION DATA BACKUP FAILED!")
        print("Something went wrong during the backup process.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)