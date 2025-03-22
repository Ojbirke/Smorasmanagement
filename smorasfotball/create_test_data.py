import os
import django
import json
import random
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smorasfotball.settings")
django.setup()

from teammanager.models import Team, Player, Match, MatchAppearance
from django.contrib.auth.models import User

def create_test_data():
    # Ensure we have an admin user
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin123")
        print("Created admin user")
    
    # Create teams
    team1 = Team.objects.create(name="Smørås G15", description="Boys under 15")
    team2 = Team.objects.create(name="Smørås G16", description="Boys under 16")
    print(f"Created teams: {team1.name}, {team2.name}")
    
    # Load player data from the attached asset file
    with open("../attached_assets/Pasted--players-id-1-first-name-Aksel-last-name-T-u00f8rvik-Pedersen-id-2-fir-1742683773082.txt", "r") as f:
        data = json.load(f)
    
    # Create players
    players = []
    for player_data in data["players"]:
        # Clean up names by removing extra spaces
        first_name = player_data["first_name"].strip()
        last_name = player_data["last_name"].strip() if player_data["last_name"] else None
        
        player = Player.objects.create(
            first_name=first_name,
            last_name=last_name,
            position=random.choice(["Forward", "Midfielder", "Defender", "Goalkeeper"]),
            active=True
        )
        players.append(player)
    
    print(f"Created {len(players)} players")
    
    # Create matches
    matches = []
    start_date = datetime.now() - timedelta(days=120)
    
    # Create 10 matches over the last 120 days
    for i in range(10):
        match_date = start_date + timedelta(days=i*12)
        
        # Alternate between teams
        team = team1 if i % 2 == 0 else team2
        
        # Create the match
        match = Match.objects.create(
            smoras_team=team,
            opponent_name=f"Opponent Club {i+1}",
            location_type=random.choice(["Home", "Away", "Neutral"]),
            date=match_date,
            location="Smørås Stadium" if i % 2 == 0 else "Away Stadium",
            match_type=random.choice(["Friendly", "League", "Cup"]),
            smoras_score=random.randint(0, 5),
            opponent_score=random.randint(0, 5)
        )
        matches.append(match)
        
        # Add random players to the match
        selected_players = random.sample(players, min(13, len(players)))
        for player in selected_players:
            minutes = random.randint(20, 90)
            goals = random.randint(0, 2) if random.random() < 0.3 else 0
            assists = random.randint(0, 2) if random.random() < 0.2 else 0
            yellow_cards = 1 if random.random() < 0.1 else 0
            red_card = True if random.random() < 0.05 else False
            
            MatchAppearance.objects.create(
                player=player,
                match=match,
                team=team,
                minutes_played=minutes,
                goals=goals,
                assists=assists,
                yellow_cards=yellow_cards,
                red_card=red_card
            )
    
    print(f"Created {len(matches)} matches with player appearances")
    
    return {
        "teams": [team1, team2],
        "players": players,
        "matches": matches
    }

if __name__ == "__main__":
    print("Creating test data...")
    create_test_data()
    print("Done!")