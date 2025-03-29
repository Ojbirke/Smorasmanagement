#!/usr/bin/env python3
"""
Pre-Deployment Database Backup

This script creates a backup of the current database state before deployment.
It's intended to be run automatically by the pre_deploy.sh script.

The backup will be placed in the deployment directory so it can be
restored after deployment.
"""

import os
import sys
import subprocess
import datetime
import shutil
from pathlib import Path

# Add the project directory to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball'))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')

try:
    import django
    django.setup()
    from django.core.management import call_command
    from django.conf import settings
except ImportError:
    print("Error: Django could not be imported. Make sure Django is installed.")
    sys.exit(1)

def create_deployment_backup():
    """Create a backup for deployment restoration"""
    print("Creating pre-deployment database backup...")
    
    # Define deployment directory
    repo_root = Path(settings.BASE_DIR).parent
    deployment_dir = repo_root / 'deployment'
    
    # Create deployment dir if it doesn't exist
    os.makedirs(deployment_dir, exist_ok=True)
    
    # Create a timestamped backup filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"deployment_db_{timestamp}.json"
    backup_path = deployment_dir / backup_filename
    
    try:
        # Create backup using Django's dumpdata
        print(f"Backing up database to {backup_path}...")
        call_command('dumpdata', output=str(backup_path))
        
        # Also create a copy with standard name for deployment
        standard_backup = deployment_dir / 'deployment_db.json'
        shutil.copy2(backup_path, standard_backup)
        
        print(f"Database backup created: {backup_path}")
        print(f"Standard deployment backup updated: {standard_backup}")
        
        # Verify backup content
        try:
            backup_size = os.path.getsize(backup_path)
            print(f"Backup size: {backup_size} bytes")
            
            if backup_size < 100:
                print("WARNING: Backup file is suspiciously small, check content")
            
            # Count objects in the database for reference
            from django.contrib.auth.models import User
            from teammanager.models import Team, Player, Match
            
            teams = Team.objects.count()
            players = Player.objects.count()
            matches = Match.objects.count()
            users = User.objects.count()
            
            print(f"Current database contains: {teams} teams, {players} players, "
                  f"{matches} matches, {users} users")
            
            return True
        except Exception as e:
            print(f"Error verifying backup: {str(e)}")
            return False
    except Exception as e:
        print(f"Error creating deployment backup: {str(e)}")
        return False

def push_to_git():
    """Push database backup to git"""
    print("Pushing database backup to git repository...")
    try:
        repo_root = Path(settings.BASE_DIR).parent
        deployment_dir = repo_root / 'deployment'
        
        # Change to repo root
        os.chdir(repo_root)
        
        # Configure git if needed
        subprocess.run(['git', 'config', 'user.name', 'Deployment Bot'])
        subprocess.run(['git', 'config', 'user.email', 'deployment@example.com'])
        
        # Add deployment directory
        subprocess.run(['git', 'add', str(deployment_dir)], check=True)
        
        # Commit changes
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subprocess.run([
            'git', 'commit', '-m', 
            f'Pre-deployment database backup {timestamp}'
        ], check=True)
        
        # Push to origin
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        
        print("Database backup pushed to git")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {str(e)}")
        return False
    except Exception as e:
        print(f"Error pushing to git: {str(e)}")
        return False

if __name__ == "__main__":
    if create_deployment_backup():
        print("Pre-deployment backup created successfully")
        
        # Attempt to push to git, but don't fail if it doesn't work
        if push_to_git():
            print("Changes pushed to git repository")
        else:
            print("Warning: Failed to push to git, continuing deployment")
        
        sys.exit(0)
    else:
        print("Error creating pre-deployment backup")
        sys.exit(1)