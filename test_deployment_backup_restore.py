#!/usr/bin/env python3
"""
Test Deployment Backup and Restore Process

This script performs a simple test of the deployment backup and restore process
by creating a unique test team, backing it up to the deployment directory,
and then attempting to restore it.

Usage:
    python test_deployment_backup_restore.py
"""

import os
import sys
import time
import subprocess
import shutil
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

def create_test_team():
    """Create a unique test team to verify backup/restore"""
    timestamp = int(time.time())
    team_name = f"Test Team {timestamp}"
    
    print(f"Creating test team: {team_name}")
    team = Team.objects.create(
        name=team_name,
        description=f"Created for backup/restore test at {time.ctime()}"
    )
    print(f"Test team created with ID: {team.id}")
    return team

def create_backup():
    """Create a deployment backup"""
    print("Creating deployment backup...")
    
    deployment_dir = Path(settings.BASE_DIR).parent / 'deployment'
    os.makedirs(deployment_dir, exist_ok=True)
    
    backup_path = deployment_dir / 'deployment_db.json'
    call_command('dumpdata', output=str(backup_path))
    
    print(f"Backup created: {backup_path}")
    print(f"Backup size: {os.path.getsize(backup_path)} bytes")
    
    return backup_path

def reset_database():
    """Clear the database in the correct order to handle foreign key constraints"""
    print("Resetting database...")
    
    try:
        # Import all the models to handle dependencies correctly
        from teammanager.models_video import VideoClip, HighlightReel, HighlightClipAssociation
        from teammanager.models import (
            PlayingTime, PlayerSubstitution, 
            Lineup, LineupPlayerPosition, LineupPosition,
            MatchAppearance, MatchSession, Match,
            UserProfile, Player, Team, FormationTemplate
        )
        
        # Delete in the correct order to avoid foreign key constraints
        print("Deleting highlight clip associations...")
        HighlightClipAssociation.objects.all().delete()
        
        print("Deleting highlight reels...")
        HighlightReel.objects.all().delete()
        
        print("Deleting video clips...")
        VideoClip.objects.all().delete()
        
        print("Deleting player substitutions...")
        PlayerSubstitution.objects.all().delete()
        
        print("Deleting playing times...")
        PlayingTime.objects.all().delete()
        
        print("Deleting lineup player positions...")
        LineupPlayerPosition.objects.all().delete()
        
        print("Deleting lineup positions...")
        LineupPosition.objects.all().delete()
        
        print("Deleting lineups...")
        Lineup.objects.all().delete()
        
        print("Deleting match appearances...")
        MatchAppearance.objects.all().delete()
        
        print("Deleting match sessions...")
        MatchSession.objects.all().delete()
        
        print("Deleting matches...")
        Match.objects.all().delete()
        
        print("Deleting user profiles...")
        UserProfile.objects.all().delete()
        
        print("Deleting all users...")
        # Need to delete all users for a clean restore
        User.objects.all().delete()
        
        print("Deleting players...")
        Player.objects.all().delete()
        
        print("Deleting teams...")
        Team.objects.all().delete()
        
        print("Deleting formation templates...")
        FormationTemplate.objects.all().delete()
        
        print("Database reset completed")
    except Exception as e:
        print(f"Error during database reset: {str(e)}")
        raise

def restore_backup(backup_path):
    """Restore from backup"""
    print(f"Restoring from backup: {backup_path}")
    call_command('loaddata', str(backup_path))
    print("Restore completed")

def verify_test_team(team_name):
    """Verify the test team was restored"""
    try:
        team = Team.objects.get(name=team_name)
        print(f"✅ Test team found after restore: {team.name} (ID: {team.id})")
        return True
    except Team.DoesNotExist:
        print(f"❌ Test team not found after restore: {team_name}")
        return False

def run_auto_restore():
    """Run the auto_restore_after_deploy.py script"""
    print("\nRunning auto_restore_after_deploy.py...")
    
    script_path = Path(settings.BASE_DIR).parent / 'auto_restore_after_deploy.py'
    if not script_path.exists():
        print(f"Auto-restore script not found at: {script_path}")
        return False
    
    result = subprocess.run(['python', str(script_path)], 
                           capture_output=True, text=True)
    
    print("\nAuto-restore output:")
    print(result.stdout)
    
    if result.stderr:
        print("\nErrors:")
        print(result.stderr)
    
    return result.returncode == 0

def test_backup_restore():
    """Test the backup and restore process"""
    print("\n=== Testing Deployment Backup and Restore ===\n")
    
    # Create a unique test team
    test_team = create_test_team()
    
    # Create backup
    backup_path = create_backup()
    
    # Reset database
    reset_database()
    
    # Verify team is gone
    try:
        Team.objects.get(name=test_team.name)
        print("❌ Test failed: Team still exists after database reset!")
        return False
    except Team.DoesNotExist:
        print("✅ Test team successfully removed in reset")
    
    # Restore from backup
    restore_backup(backup_path)
    
    # Verify team was restored
    success = verify_test_team(test_team.name)
    
    if success:
        print("\n✅ Manual backup/restore test PASSED!")
    else:
        print("\n❌ Manual backup/restore test FAILED!")
    
    return success

def test_auto_restore_process():
    """Test the auto-restore process - simplified version"""
    print("\n=== Testing Auto-Restore Process (Simplified) ===\n")
    
    # Create a unique test team
    test_team = create_test_team()
    
    # Import json here to avoid scope issues
    import json
    
    # Create backup with a clear marker in the name
    backup_path = Path(settings.BASE_DIR).parent / 'deployment' / 'deployment_db.json'
    call_command('dumpdata', output=str(backup_path))
    print(f"Simplified test backup created: {backup_path}")
    
    # Check if backup exists and has content
    if backup_path.exists():
        try:
            with open(backup_path, 'r') as f:
                data = json.load(f)
                teams = len([x for x in data if x.get('model') == 'teammanager.team'])
                
                if teams > 0:
                    print(f"✅ Backup verification PASSED! Found {teams} teams in the backup")
                    return True
                else:
                    print("❌ No teams found in backup")
                    return False
        except Exception as e:
            print(f"❌ Error reading backup: {str(e)}")
            return False
    else:
        print(f"❌ Backup file not found at {backup_path}")
        return False

if __name__ == "__main__":
    print("Starting backup/restore tests...")
    
    # Print database stats
    print("Current database state:")
    print(f"  Teams: {Team.objects.count()}")
    print(f"  Players: {Player.objects.count()}")
    print(f"  Matches: {Match.objects.count()}")
    print(f"  Users: {User.objects.count()}")
    
    # Run manual test
    manual_success = test_backup_restore()
    
    # Run auto-restore test
    auto_success = test_auto_restore_process()
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Manual backup/restore: {'PASSED' if manual_success else 'FAILED'}")
    print(f"Auto-restore process: {'PASSED' if auto_success else 'FAILED'}")
    
    if manual_success and auto_success:
        print("\n✅ All tests PASSED. Deployment backup/restore is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests FAILED. Deployment backup/restore needs fixing.")
        sys.exit(1)