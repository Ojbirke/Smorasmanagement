#!/usr/bin/env python
"""
Create complete data set for Smørås Fotball

This script creates a complete data set for the Smørås Fotball application,
including teams, players, matches, match appearances, and formation templates.

It's designed to be run after a deployment to ensure all required data
is present in the PostgreSQL database.
"""
import os
import sys
import django
import datetime
import random

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()

from teammanager.models import Team, Player, Match, MatchAppearance, FormationTemplate
from django.contrib.auth.models import User
from teammanager.models import UserProfile

# Import the existing data creation functions
from create_test_data import create_test_data
from create_formations import create_formations

def create_matches():
    """
    Creates sample match data and populates match appearances
    to establish player-team relationships
    """
    # Get teams
    try:
        team1 = Team.objects.get(name="Smørås G15")
        team2 = Team.objects.get(name="Smørås G16")
    except Team.DoesNotExist:
        print("Teams not found. Please run create_test_data first.")
        return
    
    # Get all active players
    players = Player.objects.filter(active=True)
    if not players:
        print("No players found. Please run create_test_data first.")
        return
    
    # Create sample matches
    match_data = [
        {
            "smoras_team": team1,
            "opponent_name": "Fana IL",
            "date": datetime.datetime.now() - datetime.timedelta(days=14),
            "location": "Smørås stadion",
            "location_type": "Home",
            "match_type": "Series",
            "smoras_score": 3,
            "opponent_score": 1
        },
        {
            "smoras_team": team1,
            "opponent_name": "Åsane FK",
            "date": datetime.datetime.now() - datetime.timedelta(days=7),
            "location": "Åsane Arena",
            "location_type": "Away",
            "match_type": "Series",
            "smoras_score": 2,
            "opponent_score": 2
        },
        {
            "smoras_team": team2,
            "opponent_name": "Brann",
            "date": datetime.datetime.now() - datetime.timedelta(days=3),
            "location": "Smørås stadion",
            "location_type": "Home",
            "match_type": "Cup",
            "smoras_score": 4,
            "opponent_score": 0
        }
    ]
    
    # Clear existing matches
    Match.objects.all().delete()
    
    # Create the matches
    created_matches = []
    for match_info in match_data:
        match = Match.objects.create(**match_info)
        created_matches.append(match)
        print(f"Created match: {match}")
    
    # Create match appearances to establish player-team relationships
    MatchAppearance.objects.all().delete()
    
    for match in created_matches:
        # Determine which set of players to use based on the team
        team_players = players
        
        # Randomly select 11-16 players for this match
        match_players = random.sample(list(team_players), min(random.randint(11, 16), len(team_players)))
        
        # Create match appearances
        for player in match_players:
            # Use the match's team for the player
            player_team = match.smoras_team
            
            # Random stats
            minutes_played = random.randint(10, 70)
            goals = random.randint(0, 2) if random.random() > 0.7 else 0
            assists = random.randint(0, 2) if random.random() > 0.8 else 0
            yellow_cards = 1 if random.random() > 0.9 else 0
            red_card = yellow_cards > 0 and random.random() > 0.95
            
            appearance = MatchAppearance.objects.create(
                match=match,
                player=player,
                team=player_team,
                minutes_played=minutes_played,
                goals=goals,
                assists=assists,
                yellow_cards=yellow_cards,
                red_card=red_card
            )
            print(f"Created appearance: {player.first_name} {player.last_name} for {match} in team {player_team}")
    
    print(f"\nCreated {len(created_matches)} matches with player appearances")

def create_users():
    """
    Creates sample users with different roles (admin, coach, player)
    """
    # Delete existing user profiles to avoid unique constraint violations
    UserProfile.objects.filter(user__is_superuser=False).delete()
    
    # Clear existing non-superuser users
    User.objects.filter(is_superuser=False).delete()
    
    # Create users
    user_data = [
        {
            "username": "coach1",
            "password": "smoras2025",
            "email": "coach@example.com",
            "first_name": "Coach",
            "last_name": "Eksempel",
            "role": "Coach",
            "status": "Approved"
        },
        {
            "username": "player1",
            "password": "smoras2025",
            "email": "player@example.com",
            "first_name": "Spiller",
            "last_name": "Eksempel",
            "role": "Player",
            "status": "Approved",
            "player": Player.objects.filter(active=True).first()
        }
    ]
    
    for user_info in user_data:
        # Extract role, status, and player info
        role = user_info.pop("role", "Player")
        status = user_info.pop("status", "Pending")
        player = user_info.pop("player", None)
        
        # Check if user already exists
        username = user_info["username"]
        try:
            user = User.objects.get(username=username)
            print(f"User {username} already exists, updating...")
            
            # Update user fields
            for key, value in user_info.items():
                if key != "password":  # Skip password in updates
                    setattr(user, key, value)
            user.save()
            
            # Update or create profile
            try:
                profile = UserProfile.objects.get(user=user)
                profile.role = role
                profile.status = status
                profile.player = player
                profile.save()
                print(f"Updated profile for user: {username}")
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(
                    user=user,
                    role=role,
                    status=status,
                    player=player
                )
                print(f"Created profile for existing user: {username}")
                
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create_user(**user_info)
            
            # Create profile
            profile = UserProfile.objects.create(
                user=user,
                role=role,
                status=status,
                player=player
            )
            print(f"Created new user: {username} with role {role}")
    
    print("\nUser accounts created/updated:")
    print("Coach: username='coach1', password='smoras2025'")
    print("Player: username='player1', password='smoras2025'")

def main():
    """Main function to create all data"""
    print("Creating teams and players...")
    create_test_data()
    
    print("\nCreating formation templates...")
    create_formations()
    
    print("\nCreating matches and match appearances...")
    create_matches()
    
    print("\nCreating user accounts...")
    create_users()
    
    print("\nAll data creation complete!")

if __name__ == "__main__":
    main()