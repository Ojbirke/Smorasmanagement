#!/usr/bin/env python3
"""
Auto-Restore After Deployment

This script is designed to be run automatically after a deployment
to restore the database from Git backups.

Usage:
    python auto_restore_after_deploy.py

This script will:
1. Pull the latest backups from Git
2. Check for deployment backups
3. Restore the database from the backup if found
4. Start the application server
"""

import os
import sys
import json
import subprocess
import time
import shutil
from pathlib import Path

# Add Django project to path
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball')
sys.path.append(BASE_DIR)

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

def setup_git():
    """Configure git user if not already configured"""
    try:
        # Check if git user is configured
        subprocess.run(['git', 'config', 'user.name'], capture_output=True, text=True)
        subprocess.run(['git', 'config', 'user.email'], capture_output=True, text=True)
        
        # Set default git user if not configured
        subprocess.run(['git', 'config', 'user.name', 'Deployment Bot'])
        subprocess.run(['git', 'config', 'user.email', 'deployment@example.com'])
        
        return True
    except Exception as e:
        print(f"Error configuring git: {str(e)}")
        return False

def pull_from_git():
    """Pull the latest backups from Git"""
    print("Pulling latest backups from Git repository...")
    
    # Define deployment and backup directories outside of try blocks
    repo_root = Path(settings.BASE_DIR).parent
    deployment_dir = repo_root / 'deployment'
    
    # Create deployment dir if it doesn't exist
    os.makedirs(deployment_dir, exist_ok=True)
    
    backup_dir = deployment_dir / 'pre_git_pull_backup'
    os.makedirs(backup_dir, exist_ok=True)
    
    # First, backup any existing deployment files
    try:
        # Save existing deployment_db.json
        deployment_db_path = deployment_dir / 'deployment_db.json'
        if deployment_db_path.exists() and deployment_db_path.stat().st_size > 100:
            print(f"Backing up existing deployment_db.json (size: {deployment_db_path.stat().st_size} bytes)")
            
            # Check if it has content
            try:
                with open(deployment_db_path, 'r') as f:
                    data = json.load(f)
                    record_count = len(data)
                    
                    # Only save if it has meaningful content
                    if record_count > 0:
                        timestamp = time.strftime('%Y%m%d_%H%M%S')
                        backup_path = backup_dir / f"deployment_db_pre_pull_{timestamp}.json"
                        shutil.copy2(deployment_db_path, backup_path)
                        print(f"Deployment backup saved to {backup_path}")
            except Exception as e:
                print(f"Error reading deployment_db.json, not backing up: {str(e)}")
    except Exception as e:
        print(f"Warning: Failed to backup existing deployment files: {str(e)}")
    
    try:
        # Now pull the latest from the repository
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
        print("Git pull successful")
        
        # After pull, check if we need to restore our backup
        deployment_db_path = deployment_dir / 'deployment_db.json'
        should_restore = False
        
        if not deployment_db_path.exists():
            print("Git pull resulted in missing deployment_db.json, will restore from backup")
            should_restore = True
        elif deployment_db_path.stat().st_size < 100:
            print(f"Deployment backup is too small after pull ({deployment_db_path.stat().st_size} bytes), will restore from backup")
            should_restore = True
        else:
            # Verify content
            try:
                with open(deployment_db_path, 'r') as f:
                    data = json.load(f)
                    if len(data) == 0:
                        print("Deployment backup is empty after pull, will restore from backup")
                        should_restore = True
            except:
                print("Error reading deployment backup after pull, will restore from backup")
                should_restore = True
        
        if should_restore:
            # Find the most recent pre-pull backup
            backup_files = list(backup_dir.glob('deployment_db_pre_pull_*.json'))
            if backup_files:
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_backup = backup_files[0]
                
                # Check backup content
                try:
                    with open(latest_backup, 'r') as f:
                        data = json.load(f)
                        record_count = len(data)
                        
                        if record_count > 0:
                            print(f"Restoring deployment_db.json from pre-pull backup: {latest_backup}")
                            shutil.copy2(latest_backup, deployment_db_path)
                            
                            # Verify restoration
                            if deployment_db_path.exists() and deployment_db_path.stat().st_size > 100:
                                print("Pre-pull backup successfully restored")
                            else:
                                print("Failed to restore pre-pull backup")
                except Exception as e:
                    print(f"Error reading backup {latest_backup}, not restoring: {str(e)}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git pull failed: {str(e)}")
        return False
    except Exception as e:
        print(f"Error during Git pull: {str(e)}")
        return False

def check_deployment_backup():
    """Check if a deployment backup exists"""
    print("Checking for deployment backups...")
    
    # Define deployment directory
    repo_root = Path(settings.BASE_DIR).parent
    deployment_dir = repo_root / 'deployment'
    
    if not deployment_dir.exists():
        print(f"Deployment directory not found: {deployment_dir}")
        return None
    
    # Check for deployment_db.json
    deployment_db_path = deployment_dir / 'deployment_db.json'
    if deployment_db_path.exists():
        file_size = deployment_db_path.stat().st_size
        print(f"Found deployment_db.json, size: {file_size} bytes")
        
        if file_size < 100:
            print("Warning: Deployment backup is too small, might be corrupted")
            return None
        
        # Verify JSON content
        try:
            with open(deployment_db_path, 'r') as f:
                data = json.load(f)
                record_count = len(data)
                
                # Count important models
                teams = len([x for x in data if x.get('model') == 'teammanager.team'])
                players = len([x for x in data if x.get('model') == 'teammanager.player'])
                users = len([x for x in data if x.get('model') == 'auth.user'])
                
                print(f"Backup contains: {teams} teams, {players} players, {users} users")
                
                if record_count > 0:
                    return str(deployment_db_path)
                else:
                    print("Error: Backup file is empty (no records)")
                    return None
        except json.JSONDecodeError:
            print("Error: Invalid JSON in deployment backup")
            return None
        except Exception as e:
            print(f"Error reading backup: {str(e)}")
            return None
    else:
        print("deployment_db.json not found")
        
        # Look for other deployment backups
        json_backups = list(deployment_dir.glob('*.json'))
        if json_backups:
            # Sort by modification time, newest first
            json_backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            print(f"Found alternative backup: {json_backups[0].name}")
            return str(json_backups[0])
        else:
            print("No suitable backup files found")
            return None

def restore_backup(backup_path):
    """Restore the database from backup"""
    print(f"Restoring database from {backup_path}...")
    try:
        # Flush the database
        print("Flushing database...")
        call_command('flush', '--no-input')
        
        # Load data from backup
        print("Loading data from backup...")
        call_command('loaddata', backup_path)
        
        print("Restoration successful!")
        return True
    except Exception as e:
        print(f"Error restoring database: {str(e)}")
        return False

def mark_as_production():
    """Mark this instance as production"""
    print("Marking instance as production...")
    try:
        # Define deployment directory
        repo_root = Path(settings.BASE_DIR).parent
        deployment_dir = repo_root / 'deployment'
        os.makedirs(deployment_dir, exist_ok=True)
        
        # Create IS_PRODUCTION_ENVIRONMENT marker file
        marker_path = deployment_dir / 'IS_PRODUCTION_ENVIRONMENT'
        with open(marker_path, 'w') as f:
            f.write(f"This instance was marked as production on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print("Production marker created")
        return True
    except Exception as e:
        print(f"Error creating production marker: {str(e)}")
        return False

def main():
    print("Starting auto-restore process after deployment...")
    
    # Configure git
    if not setup_git():
        print("Warning: Git configuration failed")
    
    # Pull from git
    if not pull_from_git():
        print("Warning: Git pull failed, continuing with local files")
    
    # Check for deployment backup
    backup_path = check_deployment_backup()
    if backup_path:
        # Restore from backup
        if restore_backup(backup_path):
            print("Database successfully restored from Git backup")
            
            # Mark as production
            mark_as_production()
            
            print("Auto-restore completed successfully")
            return True
        else:
            print("Database restoration failed")
            return False
    else:
        print("No valid deployment backup found")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)