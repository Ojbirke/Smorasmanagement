#!/usr/bin/env python3
"""
Check Team Count Utility

This script checks the number of teams in the database and optionally adds a missing team.
"""

import os
import sys

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

def check_team_count():
    """Check the number of teams in the database"""
    teams = Team.objects.all()
    team_count = teams.count()
    
    print(f"Current team count: {team_count}")
    print("\nExisting teams:")
    for team in teams:
        print(f"- {team.name} (ID: {team.id})")
    
    return team_count

def add_second_team():
    """Add a second team if needed"""
    # Check if we already have a Maserati team
    maserati_team = Team.objects.filter(name__icontains="Maserati").first()
    if maserati_team:
        print(f"Maserati team already exists: {maserati_team.name}")
        return maserati_team
    
    # Check for any existing teams to avoid duplication
    existing_team = Team.objects.first()
    if not existing_team:
        print("Error: No existing team found. Cannot determine team naming pattern.")
        return None
    
    # Create second team based on existing team's naming pattern
    if "Ferrari" in existing_team.name:
        # If the existing team has Ferrari in the name, create a Maserati team
        team_name = existing_team.name.replace("Ferrari", "Maserati")
    else:
        # Otherwise, just append " Maserati" to the existing club name
        base_name = existing_team.name.split(" ")[0]  # Get club name (e.g., "Smørås")
        team_name = f"{base_name} Maserati"
    
    print(f"Creating new team: {team_name}")
    new_team = Team.objects.create(name=team_name)
    print(f"Team created with ID: {new_team.id}")
    
    return new_team

def main():
    print("\n=== Team Count Check Utility ===\n")
    
    # Check current team count
    team_count = check_team_count()
    
    # If there's only one team, offer to add a second
    if team_count < 2:
        print("\nDetected only one team in the database.")
        choice = input("Would you like to add a second team? (y/n): ")
        
        if choice.lower() == 'y':
            new_team = add_second_team()
            if new_team:
                print("\nNew team count:")
                check_team_count()
                
                # Create a backup after adding the team
                print("\nCreating a backup of the updated database...")
                try:
                    from backup_production_data import create_backup, mark_as_production
                    backup_path = create_backup()
                    mark_as_production()
                    print(f"Backup created at: {backup_path}")
                    print("Environment marked as production")
                except Exception as e:
                    print(f"Error creating backup: {str(e)}")
        else:
            print("No changes made to the database.")
    else:
        print("\nDatabase already has the expected team count.")

if __name__ == "__main__":
    main()