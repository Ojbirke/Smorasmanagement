#!/usr/bin/env python3
"""
Check player match stats for the Smørås Fotball application.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()

# Now import the models
from teammanager.models import Player, MatchAppearance, Team, Match
from django.db.models import Count, Sum, Q

def check_team_data():
    print("\n--- Teams in the database ---")
    teams = Team.objects.all().values('id', 'name')
    for team in teams:
        print(f"ID: {team['id']}, Name: {team['name']}")

def check_match_data():
    print("\n--- Matches in the database ---")
    matches = Match.objects.all().values('id', 'smoras_team__name', 'opponent_name', 'date')
    for match in matches:
        print(f"ID: {match['id']}, Team: {match['smoras_team__name']}, Opponent: {match['opponent_name']}, Date: {match['date']}")

def check_player_match_counts():
    print("\n--- Player match counts ---")
    players = Player.objects.annotate(
        matches_played=Count('match_appearances')
    ).order_by('-matches_played')
    
    for player in players:
        print(f"{player.first_name} {player.last_name}: {player.matches_played} matches")

def check_player_team_counts():
    print("\n--- Player match counts by team ---")
    players = Player.objects.all()[:10]  # Just check first 10 players
    
    for player in players:
        print(f"\n{player.first_name} {player.last_name}:")
        
        team_counts = MatchAppearance.objects.filter(player=player) \
            .values('team__name') \
            .annotate(team_matches=Count('match')) \
            .order_by('-team_matches')
        
        for team_count in team_counts:
            print(f"  {team_count['team__name']}: {team_count['team_matches']} matches")

def check_dashboard_api_data():
    print("\n--- Player data as returned by the player-stats API ---")
    
    # This replicates the logic from the player_stats view
    players = Player.objects.annotate(
        matches_played=Count('match_appearances'),
        total_goals=Sum('match_appearances__goals'),
        total_assists=Sum('match_appearances__assists')
    ).values('id', 'first_name', 'last_name', 'matches_played', 'total_goals', 'total_assists')

    # Create a list to store the enriched player data with team information
    enriched_players = []

    for player in players:
        # For each player, get the teams they've played for and the number of matches with each team
        player_teams = MatchAppearance.objects.filter(player_id=player['id']) \
            .values('team__name') \
            .annotate(team_matches=Count('match')) \
            .order_by('-team_matches')

        # Add team data to the player record
        player_with_teams = player.copy()
        player_with_teams['teams'] = list(player_teams)
        
        # Print the player data in a similar format to the JSON
        print(f"\n{player_with_teams['first_name']} {player_with_teams['last_name']}:")
        print(f"  Total matches: {player_with_teams['matches_played'] or 0}")
        print(f"  Total goals: {player_with_teams['total_goals'] or 0}")
        print(f"  Total assists: {player_with_teams['total_assists'] or 0}")
        print("  Teams:")
        for team in player_with_teams['teams']:
            print(f"    {team['team__name']}: {team['team_matches']} matches")

def main():
    print("Checking Smørås Fotball player stats database...")
    check_team_data()
    check_match_data()
    check_player_match_counts()
    check_player_team_counts()
    check_dashboard_api_data()

if __name__ == "__main__":
    main()