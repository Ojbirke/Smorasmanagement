#!/usr/bin/env python
"""
Create match data script for Smørås Fotball

This script creates only match and match appearance data,
without touching users or profiles.
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

from teammanager.models import Team, Player, Match, MatchAppearance

def create_match_data():
    """
    Creates matches and match appearances only
    """
    # Get teams and players
    teams = Team.objects.all()
    if not teams:
        print("No teams found. Please run create_test_data first.")
        return
    
    team1 = Team.objects.get(name="Smørås G15")
    team2 = Team.objects.get(name="Smørås G16")
    
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

if __name__ == "__main__":
    create_match_data()