#!/usr/bin/env python
"""
Reset and Populate Database

This script performs a comprehensive reset and population of the database:
1. Deletes all existing data
2. Creates teams
3. Creates players
4. Creates matches
5. Links players to teams via match appearances
6. Creates match sessions
7. Creates formation templates
8. Sets up user accounts

Usage:
    python reset_and_populate_db.py
"""
import os
import sys
import django
import random
import datetime

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from teammanager.models import (
    Team, Player, Match, MatchAppearance, 
    FormationTemplate, MatchSession, UserProfile,
    PlayingTime, PlayerSubstitution, Lineup
)

def reset_database():
    """Delete all existing data from database"""
    print("Resetting database...")
    
    # Delete in proper order to avoid constraint violations
    print("Deleting user profiles...")
    UserProfile.objects.all().delete()
    
    print("Deleting users (except superuser)...")
    User.objects.filter(is_superuser=False).delete()
    
    print("Deleting player substitutions...")
    PlayerSubstitution.objects.all().delete()
    
    print("Deleting playing times...")
    PlayingTime.objects.all().delete()
    
    print("Deleting match sessions...")
    MatchSession.objects.all().delete()
    
    print("Deleting lineups...")
    Lineup.objects.all().delete()
    
    print("Deleting match appearances...")
    MatchAppearance.objects.all().delete()
    
    print("Deleting matches...")
    Match.objects.all().delete()
    
    print("Deleting players...")
    Player.objects.all().delete()
    
    print("Deleting teams...")
    Team.objects.all().delete()
    
    print("Database reset complete\n")

def create_teams():
    """Create basic teams"""
    print("Creating teams...")
    team1 = Team.objects.create(
        name="Smørås G15", 
        description="Smørås G15 football team"
    )
    team2 = Team.objects.create(
        name="Smørås G16",
        description="Smørås G16 football team"
    )
    print(f"Created team: {team1}")
    print(f"Created team: {team2}")
    return team1, team2

def create_players():
    """Create player records"""
    print("\nCreating players...")
    player_data = [
        {"first_name": "Aksel", "last_name": "Tørvik-Pedersen"},
        {"first_name": "Anton", "last_name": "Ringwald von Mehren"},
        {"first_name": "Aron", "last_name": "Sølberg"},
        {"first_name": "Bastian", "last_name": "Hetland"},
        {"first_name": "Brage", "last_name": "Kalsvik Wiig"},
        {"first_name": "Eirik", "last_name": "Helgesen"},
        {"first_name": "Eldar", "last_name": "Broms"},
        {"first_name": "Filip August", "last_name": "Havre"},
        {"first_name": "Ishak", "last_name": "Bozkurt"},
        {"first_name": "Jonas", "last_name": "Sværen Langnes"},
        {"first_name": "Julijan", "last_name": "Laastad"},
        {"first_name": "Lars", "last_name": "Underdal Vik"},
        {"first_name": "Lukas", "last_name": "Stordal"},
        {"first_name": "Magnus", "last_name": "Lunde Dietz"},
        {"first_name": "Marcus H", "last_name": "Leknes"},
        {"first_name": "Markus", "last_name": "Birkeland"},
        {"first_name": "Martin", "last_name": "Remøy Øvsthus"},
        {"first_name": "Matheo", "last_name": "Brekke Nøttveit"},
        {"first_name": "Nikolai", "last_name": "Vikebø Gjerde"},
        {"first_name": "Noah", "last_name": "Selvik Nødtvedt"},
        {"first_name": "Oscar", "last_name": "Spence"},
        {"first_name": "Sverre", "last_name": "Oshaug Ingvaldsen"},
        {"first_name": "Ulrik", "last_name": "Gurvin Rekeland"},
    ]
    
    created_players = []
    for idx, player_info in enumerate(player_data, 1):
        player = Player.objects.create(
            first_name=player_info["first_name"],
            last_name=player_info["last_name"],
            position="",  # Set default position
            active=True,
            date_of_birth=None,  # Set default to None
            email="",
            phone=""
        )
        created_players.append(player)
        print(f"Created player: {player.first_name} {player.last_name}")
    
    return created_players

def create_formation_templates():
    """Create formation templates for different team sizes"""
    print("\nCreating formation templates...")
    
    # Dictionary of formations by team size
    formations = {
        "5er": ["2-2", "1-2-1", "1-1-2", "2-1-1"],
        "7er": ["2-3-1", "3-2-1", "3-1-2", "2-1-3", "2-2-2", "3-3", "2-4", "4-2"],
        "9er": ["3-2-3", "3-3-2", "3-4-1", "4-3-1"],
        "11er": ["4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2", "3-4-3"],
    }
    
    templates_created = 0
    
    # Create each formation
    for team_size, formation_list in formations.items():
        for formation in formation_list:
            # Calculate player count based on team size
            if team_size == "5er":
                player_count = 5
            elif team_size == "7er":
                player_count = 7
            elif team_size == "9er":
                player_count = 9
            elif team_size == "11er":
                player_count = 11
            else:
                player_count = 11
            
            # Check if formation already exists
            existing = FormationTemplate.objects.filter(
                name=f"{formation} ({team_size})"
            ).exists()
            
            if existing:
                print(f"Formation {formation} ({team_size}) already exists, skipping.")
                continue
            
            template = FormationTemplate.objects.create(
                name=f"{formation} ({team_size})",
                description=f"{formation} formation for {team_size} football",
                formation_structure=formation,
                player_count=player_count
            )
            templates_created += 1
            print(f"Created formation template: {template.name}")
    
    print(f"\nCreated {templates_created} new formation templates.")
    return templates_created

def create_matches(team1, team2):
    """Create matches and match appearances"""
    print("\nCreating matches...")
    
    # Create sample matches
    match_data = [
        {
            "smoras_team": team1,
            "opponent_name": "Fana IL",
            "date": timezone.now() - timezone.timedelta(days=14),
            "location": "Smørås stadion",
            "location_type": "Home",
            "match_type": "Series",
            "smoras_score": 3,
            "opponent_score": 1
        },
        {
            "smoras_team": team1,
            "opponent_name": "Åsane FK",
            "date": timezone.now() - timezone.timedelta(days=7),
            "location": "Åsane Arena",
            "location_type": "Away",
            "match_type": "Series",
            "smoras_score": 2,
            "opponent_score": 2
        },
        {
            "smoras_team": team2,
            "opponent_name": "Brann",
            "date": timezone.now() - timezone.timedelta(days=3),
            "location": "Smørås stadion",
            "location_type": "Home",
            "match_type": "Cup",
            "smoras_score": 4,
            "opponent_score": 0
        }
    ]
    
    # Create the matches
    created_matches = []
    for match_info in match_data:
        match = Match.objects.create(**match_info)
        created_matches.append(match)
        print(f"Created match: {match}")
    
    print("\nCreating match appearances...")
    
    # Get all players
    players = Player.objects.filter(active=True)
    
    # Create match appearances for each match
    for match in created_matches:
        # Randomly select 11-16 players for this match
        match_players = random.sample(list(players), min(random.randint(11, 16), len(players)))
        
        # Create match appearances
        for player in match_players:
            # Use the match's team
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
            print(f"Created appearance: {player.first_name} for {match} in {player_team}")
    
    print(f"\nCreated {len(created_matches)} matches with player appearances")
    return created_matches

def create_match_sessions(matches):
    """Create match sessions for existing matches"""
    print("\nCreating match sessions...")
    
    # Create match sessions
    created_sessions = []
    for match in matches:
        # Create a match session for each match
        session = MatchSession.objects.create(
            match=match,
            name=f"Game Day {random.randint(1, 5)}",
            periods=2,
            period_length=25,
            substitution_interval=5,
            is_active=False,
            current_period=1,
            elapsed_time=0,
            start_time=timezone.now() - timezone.timedelta(hours=random.randint(1, 5))
        )
        created_sessions.append(session)
        print(f"Created match session: {session.name} for match {match}")
    
    # Activate one random session
    if created_sessions:
        active_session = random.choice(created_sessions)
        active_session.is_active = True
        active_session.save()
        print(f"\nActivated session: {active_session.name} for match {active_session.match}")
    
    print(f"\nCreated {len(created_sessions)} match sessions")
    return created_sessions

def create_users():
    """Create users with different roles"""
    print("\nCreating users...")
    
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
    
    created_users = []
    for user_info in user_data:
        # Extract role, status, and player info
        role = user_info.pop("role", "Player")
        status = user_info.pop("status", "Pending")
        player = user_info.pop("player", None)
        username = user_info["username"]
        
        # Check if user already exists
        user, created = User.objects.get_or_create(
            username=username,
            defaults=user_info
        )
        
        if created:
            # Set password for new user (get_or_create doesn't handle this correctly)
            user.set_password(user_info["password"])
            user.save()
            print(f"Created user: {user.username} with role {role}")
        else:
            print(f"User {user.username} already exists, updating profile")
        
        # Get or create profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "role": role,
                "status": status,
                "player": player
            }
        )
        
        if profile_created:
            print(f"Created profile for {user.username}")
        else:
            # Update profile
            profile.role = role
            profile.status = status
            profile.player = player
            profile.save()
            print(f"Updated profile for {user.username}")
        
        created_users.append(user)
    
    print("\nUser accounts created/updated:")
    print("Coach: username='coach1', password='smoras2025'")
    print("Player: username='player1', password='smoras2025'")
    
    return created_users

def main():
    """Main function to reset and populate the database"""
    print("\n=== Starting database reset and population ===\n")
    
    # Reset database
    reset_database()
    
    # Create teams
    team1, team2 = create_teams()
    
    # Create players
    players = create_players()
    
    # Create formation templates
    create_formation_templates()
    
    # Create matches and link players to teams
    matches = create_matches(team1, team2)
    
    # Create match sessions
    create_match_sessions(matches)
    
    # Create users
    create_users()
    
    print("\n=== Database reset and population complete ===\n")
    print("You can now access the application with:")
    print("Admin: username='djadmin', password='superuser123'")
    print("Coach: username='coach1', password='smoras2025'")
    print("Player: username='player1', password='smoras2025'")

if __name__ == "__main__":
    main()