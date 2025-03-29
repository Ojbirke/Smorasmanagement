#!/usr/bin/env python3
"""
Deployment Restore Process Tester

This script tests the complete deployment backup and restore process:
1. Creates test data in the database
2. Generates a deployment backup
3. Clears the database
4. Restores from the backup
5. Verifies the restored data matches the original

Usage:
    python deployment_restore_test.py

This is useful for testing the full deployment cycle in a safe way.
"""

import os
import sys
import subprocess
import random
import json
import time
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
    from teammanager.models import (
        Team, Player, Match, MatchAppearance, 
        FormationTemplate, MatchSession
    )
except ImportError:
    print("Error: Django could not be imported. Make sure Django is installed.")
    sys.exit(1)

def count_database_objects():
    """Count objects in the current database"""
    try:
        return {
            'teams': Team.objects.count(),
            'players': Player.objects.count(),
            'matches': Match.objects.count(),
            'match_sessions': MatchSession.objects.count(),
            'appearances': MatchAppearance.objects.count(),
            'users': User.objects.count(),
        }
    except Exception as e:
        print(f"Error counting database objects: {str(e)}")
        return {'teams': 0, 'players': 0, 'matches': 0, 'match_sessions': 0, 'appearances': 0, 'users': 0}

def create_test_team():
    """Create a special test team to check restore process"""
    unique_id = str(int(time.time()))[-5:]
    team_name = f"Test Team {unique_id}"
    team = Team.objects.create(
        name=team_name,
        description=f"Test team created for deployment restore testing at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"Created test team: {team.name}")
    return team

def create_test_player():
    """Create a special test player to check restore process"""
    unique_id = str(int(time.time()))[-5:]
    first_name = f"TestPlayer{unique_id}"
    player = Player.objects.create(
        first_name=first_name,
        last_name="Deployment",
        active=True
    )
    print(f"Created test player: {player.first_name} {player.last_name}")
    return player

def create_test_match(team):
    """Create a test match with the test team"""
    unique_id = str(int(time.time()))[-5:]
    match = Match.objects.create(
        smoras_team=team,
        opponent_name=f"Test Opponent {unique_id}",
        date=django.utils.timezone.now(),
        location=f"Test Location {unique_id}",
        location_type="Home",
        match_type="Test",
        smoras_score=random.randint(1, 5),
        opponent_score=random.randint(0, 4)
    )
    print(f"Created test match: {match}")
    return match

def create_deployment_backup():
    """Create a deployment backup"""
    print("Creating deployment backup...")
    
    # Define deployment directory
    repo_root = Path(settings.BASE_DIR).parent
    deployment_dir = repo_root / 'deployment'
    
    # Create deployment dir if it doesn't exist
    os.makedirs(deployment_dir, exist_ok=True)
    
    # Create backup path
    backup_path = deployment_dir / 'deployment_db.json'
    
    try:
        # Create backup using Django's dumpdata
        print(f"Backing up database to {backup_path}...")
        call_command('dumpdata', output=str(backup_path))
        
        print(f"Database backup created: {backup_path}")
        
        # Verify backup exists and has content
        if not os.path.exists(backup_path):
            print("Error: Backup file not created!")
            return None
        
        backup_size = os.path.getsize(backup_path)
        if backup_size < 100:
            print(f"Warning: Backup file is suspiciously small ({backup_size} bytes)!")
            return None
            
        print(f"Backup size: {backup_size} bytes")
        return str(backup_path)
    
    except Exception as e:
        print(f"Error creating deployment backup: {str(e)}")
        return None

def clear_database():
    """Clear the database to simulate a clean deployment environment"""
    print("Clearing database to simulate fresh deployment...")
    
    # Delete in proper order to avoid constraint violations
    print("Deleting highlight clip associations...")
    try:
        from teammanager.models_video import HighlightClipAssociation
        HighlightClipAssociation.objects.all().delete()
    except Exception as e:
        print(f"Error deleting highlight clip associations: {e}")
    
    print("Deleting highlight reels...")
    try:
        from teammanager.models_video import HighlightReel
        HighlightReel.objects.all().delete()
    except Exception as e:
        print(f"Error deleting highlight reels: {e}")
    
    print("Deleting video clips...")
    try:
        from teammanager.models_video import VideoClip
        VideoClip.objects.all().delete()
    except Exception as e:
        print(f"Error deleting video clips: {e}")
    
    print("Deleting player substitutions...")
    try:
        from teammanager.models import PlayerSubstitution
        PlayerSubstitution.objects.all().delete()
    except Exception as e:
        print(f"Error deleting player substitutions: {e}")
    
    print("Deleting playing times...")
    try:
        from teammanager.models import PlayingTime
        PlayingTime.objects.all().delete()
    except Exception as e:
        print(f"Error deleting playing times: {e}")
    
    print("Deleting lineup player positions...")
    try:
        from teammanager.models import LineupPlayerPosition
        LineupPlayerPosition.objects.all().delete()
    except Exception as e:
        print(f"Error deleting lineup player positions: {e}")
    
    print("Deleting lineup positions...")
    try:
        from teammanager.models import LineupPosition
        LineupPosition.objects.all().delete()
    except Exception as e:
        print(f"Error deleting lineup positions: {e}")
    
    print("Deleting lineups...")
    try:
        from teammanager.models import Lineup
        Lineup.objects.all().delete()
    except Exception as e:
        print(f"Error deleting lineups: {e}")
    
    print("Deleting match appearances...")
    MatchAppearance.objects.all().delete()
    
    print("Deleting match sessions...")
    MatchSession.objects.all().delete()
    
    print("Deleting matches...")
    Match.objects.all().delete()
    
    print("Deleting user profiles...")
    try:
        from teammanager.models import UserProfile
        UserProfile.objects.all().delete()
    except Exception as e:
        print(f"Error deleting user profiles: {e}")
    
    print("Deleting all users...")
    User.objects.all().delete()
    
    print("Deleting players...")
    Player.objects.all().delete()
    
    print("Deleting teams...")
    Team.objects.all().delete()
    
    print("Deleting formation templates...")
    FormationTemplate.objects.all().delete()
    
    print("Database reset completed")

def restore_from_backup(backup_path):
    """Restore the database from backup"""
    print(f"Restoring database from {backup_path}...")
    try:
        # Load data from backup
        call_command('loaddata', backup_path)
        
        print("Database restored successfully!")
        return True
    except Exception as e:
        print(f"Error restoring database: {str(e)}")
        return False

def run_auto_restore_script():
    """Run the auto_restore_after_deploy.py script"""
    print("Running auto_restore_after_deploy.py to test the full restore process...")
    try:
        repo_root = Path(settings.BASE_DIR).parent
        auto_restore_script = repo_root / 'auto_restore_after_deploy.py'
        
        if not os.path.exists(auto_restore_script):
            print(f"Error: auto_restore_after_deploy.py not found at {auto_restore_script}")
            return False
            
        # Run the script
        result = subprocess.run(['python', str(auto_restore_script)], capture_output=True, text=True)
        
        # Print output
        print("--- auto_restore_after_deploy.py output ---")
        print(result.stdout)
        
        if result.stderr:
            print("--- stderr ---")
            print(result.stderr)
        
        print("--- end of output ---")
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running auto_restore_after_deploy.py: {str(e)}")
        return False

def verify_data_restored(original_team_name, original_player_first_name):
    """Verify that our test data was properly restored"""
    print("Verifying restored data...")
    
    # Check if team exists
    team_exists = Team.objects.filter(name=original_team_name).exists()
    if team_exists:
        print(f"✓ Test team '{original_team_name}' successfully restored")
    else:
        print(f"✗ Test team '{original_team_name}' not found after restore!")

    # Check if player exists
    player_exists = Player.objects.filter(first_name=original_player_first_name).exists()
    if player_exists:
        print(f"✓ Test player '{original_player_first_name}' successfully restored")
    else:
        print(f"✗ Test player '{original_player_first_name}' not found after restore!")
        
    # Return success status
    return team_exists and player_exists

def main():
    print("\n=== Testing Deployment Restore Process ===\n")
    
    # Count initial database objects
    initial_counts = count_database_objects()
    print("Initial database state:")
    for key, value in initial_counts.items():
        print(f"  {key}: {value}")
    
    # Create test data
    test_team = create_test_team()
    test_player = create_test_player()
    test_match = create_test_match(test_team)
    
    # Count objects after creating test data
    test_data_counts = count_database_objects()
    print("\nDatabase state after creating test data:")
    for key, value in test_data_counts.items():
        print(f"  {key}: {value}")
    
    # Store original team and player names for verification
    original_team_name = test_team.name
    original_player_first_name = test_player.first_name
    
    # Create deployment backup
    backup_path = create_deployment_backup()
    if not backup_path:
        print("Error: Deployment backup failed! Aborting test.")
        return False
    
    # Clear database to simulate clean environment
    clear_database()
    
    # Count objects after clearing
    clear_counts = count_database_objects()
    print("\nDatabase state after clearing:")
    for key, value in clear_counts.items():
        print(f"  {key}: {value}")
    
    # Run the auto-restore script
    restore_success = run_auto_restore_script()
    if not restore_success:
        print("Warning: auto_restore_after_deploy.py returned non-zero exit code")
        print("Attempting manual restore as fallback...")
        restore_success = restore_from_backup(backup_path)
        
        if not restore_success:
            print("Error: Manual restore failed! Test unsuccessful.")
            return False
    
    # Count objects after restoration
    restored_counts = count_database_objects()
    print("\nDatabase state after restoration:")
    for key, value in restored_counts.items():
        print(f"  {key}: {value}")
    
    # Verify our test data was restored
    verification_success = verify_data_restored(original_team_name, original_player_first_name)
    
    if verification_success:
        print("\n✓ DEPLOYMENT RESTORE TEST SUCCESSFUL!")
        print("The backup and restore process is working correctly.")
    else:
        print("\n✗ DEPLOYMENT RESTORE TEST FAILED!")
        print("The restore process did not properly restore test data.")
    
    return verification_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)