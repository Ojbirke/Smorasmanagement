#!/usr/bin/env python3
"""
Team Inspector Utility

This script examines teams in the database and detects any inconsistencies
between the log reports and the actual database content.
"""

import os
import sys
import json
from collections import defaultdict
from pathlib import Path

# Add Django project to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball'))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')

try:
    import django
    django.setup()
    from django.conf import settings
    from django.contrib.auth.models import User
    from teammanager.models import Team, Player, Match, MatchAppearance
except ImportError:
    print("Error: Django could not be imported. Make sure Django is installed.")
    sys.exit(1)

def check_deployment_db_json():
    """Check the content of deployment_db.json"""
    print("\n=== Checking Deployment DB JSON ===")
    
    # Find the deployment_db.json file
    deployment_dir = Path(settings.BASE_DIR).parent / 'deployment'
    deployment_db = deployment_dir / 'deployment_db.json'
    
    if not deployment_db.exists():
        print(f"Error: {deployment_db} not found")
        return {}
    
    # Load and parse the JSON file
    try:
        with open(deployment_db, 'r') as f:
            content = f.read()
            data = json.loads(content)
        
        # Count model types
        model_counts = defaultdict(int)
        for item in data:
            model_counts[item.get('model', 'unknown')] += 1
        
        print(f"JSON file size: {len(content)} bytes")
        print(f"Total records: {len(data)}")
        print("\nModel counts:")
        for model, count in sorted(model_counts.items()):
            print(f"  - {model}: {count}")
        
        # Specifically look for team records
        team_records = [item for item in data if item.get('model') == 'teammanager.team']
        print(f"\nTeam records in JSON: {len(team_records)}")
        for team in team_records:
            print(f"  - {team.get('fields', {}).get('name')} (ID: {team.get('pk')})")
        
        return model_counts
    except Exception as e:
        print(f"Error parsing JSON: {str(e)}")
        return {}

def fix_deployment_json_if_needed():
    """Fix deployment JSON if team count is wrong"""
    print("\n=== Checking If Deployment JSON Needs Fixing ===")
    
    # Get current team count
    db_team_count = Team.objects.count()
    print(f"Current database team count: {db_team_count}")
    
    # Find the deployment_db.json file
    deployment_dir = Path(settings.BASE_DIR).parent / 'deployment'
    deployment_db = deployment_dir / 'deployment_db.json'
    
    if not deployment_db.exists():
        print(f"Error: {deployment_db} not found")
        return False
    
    # Create a fresh dumpdata backup
    import time
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    fresh_backup = deployment_dir / f'fresh_backup_{timestamp}.json'
    
    from django.core.management import call_command
    print(f"Creating fresh backup: {fresh_backup}")
    call_command('dumpdata', output=str(fresh_backup))
    
    # Check if the fresh backup exists and has content
    if not fresh_backup.exists() or fresh_backup.stat().st_size == 0:
        print(f"Error: Failed to create fresh backup at {fresh_backup}")
        return False
    
    # Parse the fresh backup
    try:
        with open(fresh_backup, 'r') as f:
            data = json.loads(f.read())
        
        # Count team records in fresh backup
        team_records = [item for item in data if item.get('model') == 'teammanager.team']
        print(f"Team records in fresh backup: {len(team_records)}")
        
        # If team counts don't match, use the fresh backup
        if len(team_records) != db_team_count:
            print(f"Warning: Team count mismatch between fresh backup ({len(team_records)}) and database ({db_team_count})")
            return False
        
        # Update the deployment_db.json file
        import shutil
        shutil.copy2(fresh_backup, deployment_db)
        print(f"✅ Updated deployment_db.json with fresh backup data")
        
        return True
    except Exception as e:
        print(f"Error processing fresh backup: {str(e)}")
        return False

def check_team_player_relationships():
    """Check relationships between teams and players"""
    print("\n=== Checking Team-Player Relationships ===")
    
    teams = Team.objects.all()
    print(f"Total teams in database: {teams.count()}")
    
    for team in teams:
        print(f"\nTeam: {team.name} (ID: {team.id})")
        
        # Check match count
        matches = Match.objects.filter(team=team)
        print(f"  Matches for this team: {matches.count()}")
        
        # For each match, get players who appeared
        player_set = set()
        for match in matches:
            appearances = MatchAppearance.objects.filter(match=match)
            for appearance in appearances:
                player_set.add(appearance.player)
        
        players = list(player_set)
        print(f"  Players who have appeared for this team: {len(players)}")
        for idx, player in enumerate(players, 1):
            print(f"  {idx}. {player.first_name} {player.last_name}")

def main():
    print("\n=== Team Inspector Utility ===\n")
    
    # Database configuration info
    print("Database Configuration:")
    print(f"  Engine: {settings.DATABASES['default']['ENGINE']}")
    print(f"  Name: {settings.DATABASES['default']['NAME']}")
    
    # Check current teams in database
    teams = Team.objects.all()
    print(f"\nDatabase contains {teams.count()} teams:")
    for team in teams:
        # Get matches for this team
        matches = Match.objects.filter(team=team)
        match_count = matches.count()
        
        # Calculate player count using a different approach
        player_ids = set()
        for match in matches:
            appearances = MatchAppearance.objects.filter(match=match)
            for appearance in appearances:
                if hasattr(appearance, 'player') and appearance.player:
                    player_ids.add(appearance.player.id)
        
        print(f"  - {team.name} (ID: {team.id}, Matches: {match_count}, Players: {len(player_ids)})")
    
    # Check the deployment_db.json file
    check_deployment_db_json()
    
    # Check team-player relationships
    check_team_player_relationships()
    
    # Fix deployment JSON if needed
    fix_deployment_json_if_needed()
    
    print("\n✅ Team inspection complete.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)