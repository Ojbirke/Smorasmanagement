#!/usr/bin/env python3
"""
Deployment Protection Script

This script is designed to be run immediately after a deployment to protect against
accidental database overwrites during development-to-production deployments.

It performs several checks:
1. Determines if this is a production environment
2. Checks the existing database for content
3. Verifies that any deployment backup has sufficient content before restoration
4. Prevents empty or low-content backups from overwriting production data

Usage:
    python deployment_protect.py

Run this script BEFORE auto_restore_after_deploy.py in the deployment process.
"""

import os
import sys
import json
import subprocess
import shutil
import time
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"deployment_protection_{time.strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    from django.contrib.auth.models import User
    from teammanager.models import Team, Player, Match
except ImportError:
    logger.error("Error: Django could not be imported. Make sure Django is installed.")
    sys.exit(1)

def is_production_environment():
    """Check if this is a production environment"""
    repo_root = Path(settings.BASE_DIR).parent
    marker_path = repo_root / 'deployment' / 'IS_PRODUCTION_ENVIRONMENT'
    return marker_path.exists()

def get_database_stats():
    """Get counts of key database objects"""
    return {
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
        'matches': Match.objects.count(),
        'users': User.objects.count(),
    }
    
def check_deployment_backup_content():
    """Check if the deployment backup has sufficient content"""
    repo_root = Path(settings.BASE_DIR).parent
    deployment_path = repo_root / 'deployment' / 'deployment_db.json'
    
    if not deployment_path.exists():
        logger.warning(f"Deployment backup not found at {deployment_path}")
        return False, {}
    
    try:
        with open(deployment_path, 'r') as f:
            data = json.load(f)
            
            # Count key entities
            backup_stats = {
                'teams': len([x for x in data if x.get('model') == 'teammanager.team']),
                'players': len([x for x in data if x.get('model') == 'teammanager.player']),
                'matches': len([x for x in data if x.get('model') == 'teammanager.match']),
                'users': len([x for x in data if x.get('model') == 'auth.user']),
                'total': len(data),
            }
            
            # Check for minimum content
            if backup_stats['teams'] < 1 or backup_stats['players'] < 5:
                logger.warning("Deployment backup has insufficient content")
                return False, backup_stats
            
            return True, backup_stats
    except Exception as e:
        logger.error(f"Error checking deployment backup: {str(e)}")
        return False, {}

def create_last_resort_backup():
    """Create a last-resort backup in case all else fails"""
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    backup_filename = f"last_resort_backup_{timestamp}.json"
    backup_path = os.path.join(settings.BASE_DIR, backup_filename)
    
    try:
        call_command('dumpdata', output=backup_path)
        logger.info(f"Created last-resort backup at {backup_path}")
        
        # Also copy to deployment directory
        repo_root = Path(settings.BASE_DIR).parent
        deployment_dir = repo_root / 'deployment'
        os.makedirs(deployment_dir, exist_ok=True)
        
        deployment_backup = deployment_dir / f"pre_auto_restore_{timestamp}.json"
        shutil.copy2(backup_path, deployment_backup)
        logger.info(f"Copied backup to deployment directory: {deployment_backup}")
        
        return backup_path
    except Exception as e:
        logger.error(f"Error creating last-resort backup: {str(e)}")
        return None

def protect_deployment_backup():
    """Create a copy of deployment backup to prevent loss"""
    repo_root = Path(settings.BASE_DIR).parent
    deployment_path = repo_root / 'deployment' / 'deployment_db.json'
    
    if not deployment_path.exists():
        logger.warning("No deployment backup to protect")
        return False
    
    try:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_path = repo_root / 'deployment' / f"protected_deployment_{timestamp}.json"
        shutil.copy2(deployment_path, backup_path)
        logger.info(f"Protected deployment backup: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Error protecting deployment backup: {str(e)}")
        return False

def main():
    logger.info("Starting deployment protection...")
    
    # Check if we're in production
    is_production = is_production_environment()
    if is_production:
        logger.info("This is a PRODUCTION environment - extra protection will be applied")
    else:
        logger.info("This is a DEVELOPMENT environment")
    
    # Get database stats
    db_stats = get_database_stats()
    logger.info(f"Current database contains: {db_stats['teams']} teams, {db_stats['players']} players, {db_stats['users']} users")
    
    # Check deployment backup
    backup_valid, backup_stats = check_deployment_backup_content()
    if backup_valid:
        logger.info(f"Deployment backup is valid. Contains: {backup_stats['teams']} teams, {backup_stats['players']} players")
    else:
        logger.warning(f"Deployment backup is invalid or insufficient: {backup_stats}")
    
    # Special handling for production
    if is_production:
        # Create last-resort backup
        last_resort_backup = create_last_resort_backup()
        
        # Protection logic for production: Don't allow a restore if it would result in data loss
        if db_stats['teams'] > 0 and db_stats['players'] > 0:
            # We have meaningful data in the database
            if not backup_valid or (backup_stats['teams'] < db_stats['teams'] or backup_stats['players'] < db_stats['players']):
                logger.warning("PROTECTION ACTIVATED: Deployment backup would result in data loss!")
                logger.warning("Creating a new deployment backup from the current database")
                
                # Make a backup of the current database and use it instead
                try:
                    # Backup the current deployment backup if it exists
                    protect_deployment_backup()
                    
                    # Create a new deployment backup
                    logger.info("Creating new deployment backup...")
                    call_command('deployment_backup')
                    logger.info("Successfully created new deployment backup from current database")
                    
                    # Set a marker to indicate protection was applied
                    marker_path = Path(settings.BASE_DIR).parent / 'deployment' / 'DEPLOYMENT_PROTECTED'
                    with open(marker_path, 'w') as f:
                        f.write(f"Deployment protection applied on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Current DB: {db_stats['teams']} teams, {db_stats['players']} players\n")
                        f.write(f"Backup stats: {backup_stats}\n")
                    
                    logger.info("Deployment protection complete")
                    return True
                except Exception as e:
                    logger.error(f"Failed to create new deployment backup: {str(e)}")
                    return False
    
    logger.info("Deployment protection checks complete")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)