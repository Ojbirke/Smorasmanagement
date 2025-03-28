#!/usr/bin/env python3
"""
Database Content Count Script

Used to check the state of the database before/after backup/restore operations.
"""
import os
import sys
import django

# Add project path
sys.path.append('smorasfotball')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')

# Initialize Django
django.setup()

# Import models
from django.contrib.auth.models import User
from teammanager.models import Team, Player, Match

def check_db_counts():
    """Print counts of key models in the database"""
    user_count = User.objects.count()
    team_count = Team.objects.count()
    player_count = Player.objects.count()
    match_count = Match.objects.count()
    
    print(f"Database Content Counts:")
    print(f"Users: {user_count}")
    print(f"Teams: {team_count}")
    print(f"Players: {player_count}")
    print(f"Matches: {match_count}")
    
    # Show team names
    if team_count > 0:
        print("\nTeams:")
        for team in Team.objects.all():
            print(f"  - {team.name} (ID: {team.id})")
    
    return (user_count, team_count, player_count, match_count)

if __name__ == "__main__":
    print("Checking database counts...")
    check_db_counts()