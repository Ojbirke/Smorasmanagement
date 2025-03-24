import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smorasfotball.settings")
django.setup()

from teammanager.models import Team, Player

def create_test_data():
    """
    Creates test data for the Smørås G2015 Fotball application.
    Includes teams and players with proper exception handling for duplicates.
    """
    # Define teams
    teams_data = [
        {"name": "Smørås G15", "description": "Smørås G15 team"},
        {"name": "Smørås G16", "description": "Smørås G16 team"},
    ]
    
    # Define players
    players_data = [
        {"first_name": "Aksel", "last_name": "Tørvik-Pedersen", "position": "Forward", "active": True},
        {"first_name": "Anton", "last_name": "Ringwald von Mehren", "position": "Midfielder", "active": True},
        {"first_name": "Aron", "last_name": "Sølberg", "position": "Defender", "active": True},
        {"first_name": "Bastian", "last_name": "Hetland", "position": "Midfielder", "active": True},
        {"first_name": "Brage", "last_name": "Kalsvik Wiig", "position": "Defender", "active": True},
        {"first_name": "Eirik", "last_name": "Helgesen", "position": "Forward", "active": True},
        {"first_name": "Eldar", "last_name": "Broms", "position": "Midfielder", "active": True},
        {"first_name": "Filip", "last_name": "August Havre", "position": "Defender", "active": True},
        {"first_name": "Ishak", "last_name": "Bozkurt", "position": "Forward", "active": True},
        {"first_name": "Jonas", "last_name": "Sværen Langnes", "position": "Midfielder", "active": True},
        {"first_name": "Julijan", "last_name": "Laastad", "position": "Defender", "active": True},
        {"first_name": "Lars", "last_name": "Underdal Vik", "position": "Midfielder", "active": True},
        {"first_name": "Lukas", "last_name": "Stordal", "position": "Forward", "active": True},
        {"first_name": "Magnus", "last_name": "Lunde Dietz", "position": "Defender", "active": True},
        {"first_name": "Marcus", "last_name": "H Leknes", "position": "Midfielder", "active": True},
        {"first_name": "Markus", "last_name": "Birkeland", "position": "Forward", "active": True},
        {"first_name": "Martin", "last_name": "Remøy Øvsthus", "position": "Midfielder", "active": True},
        {"first_name": "Matheo", "last_name": "Brekke Nøttveit", "position": "Defender", "active": True},
        {"first_name": "Nikolai", "last_name": "Vikebø Gjerde", "position": "Forward", "active": True},
        {"first_name": "Noah", "last_name": "Selvik Nødtvedt", "position": "Midfielder", "active": True},
        {"first_name": "Oscar", "last_name": "Spence", "position": "Defender", "active": True},
        {"first_name": "Sverre", "last_name": "Oshaug Ingvaldsen", "position": "Midfielder", "active": True},
        {"first_name": "Ulrik", "last_name": "Gurvin Rekeland", "position": "Forward", "active": True},
    ]
    
    # Clear existing data if script is run multiple times
    Team.objects.all().delete()
    Player.objects.all().delete()
    
    # Create teams
    created_teams = []
    for team_data in teams_data:
        team, created = Team.objects.get_or_create(
            name=team_data["name"],
            defaults={"description": team_data.get("description", "")}
        )
        created_teams.append(team)
        if created:
            print(f"Created team: {team.name}")
        else:
            print(f"Team already exists: {team.name}")
    
    # Create players
    for player_data in players_data:
        player, created = Player.objects.get_or_create(
            first_name=player_data["first_name"],
            last_name=player_data["last_name"],
            defaults={
                "position": player_data.get("position", ""),
                "active": player_data.get("active", True)
            }
        )
        if created:
            print(f"Created player: {player.first_name} {player.last_name}")
        else:
            print(f"Player already exists: {player.first_name} {player.last_name}")

    print(f"\nCreated or verified {len(created_teams)} teams and {len(players_data)} players")

if __name__ == "__main__":
    create_test_data()