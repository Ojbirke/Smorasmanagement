#!/usr/bin/env python3
"""
Check Teams Utility

This script checks the teams in the database and their associated matches.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('smorasfotball')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()

from teammanager.models import Team, Match, MatchAppearance

def check_teams():
    """Check the teams in the database"""
    teams = Team.objects.all()
    print(f"Found {len(teams)} teams in the database:")
    
    for team in teams:
        print(f"- {team.id}: {team.name}")
    
    return teams

def check_matches():
    """Check matches associated with each team"""
    teams = Team.objects.all()
    
    for team in teams:
        matches = Match.objects.filter(smoras_team=team)
        print(f"\nTeam: {team.name}")
        print(f"  Matches: {matches.count()}")
        
        for match in matches:
            print(f"  - Match #{match.id}: {team.name} vs {match.opponent_name} on {match.date}")
            
            # Count appearances for this match
            appearances = MatchAppearance.objects.filter(match=match)
            print(f"    Appearances: {appearances.count()}")

def check_dashboard_data():
    """Check player match count data as used in the dashboard"""
    from django.db.models import Count
    
    # This replicates the dashboard query to get player match counts by team
    player_match_counts = MatchAppearance.objects.values(
        'player__id', 
        'player__first_name', 
        'player__last_name', 
        'match__smoras_team__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Group by team to see which teams appear in the count
    teams_in_counts = set()
    for item in player_match_counts:
        team_name = item['match__smoras_team__name']
        teams_in_counts.add(team_name)
    
    print("\nTeams appearing in player match counts:")
    for team in teams_in_counts:
        print(f"- {team}")
    
    return teams_in_counts

def main():
    """Main function"""
    print("=== Checking Teams ===")
    teams = check_teams()
    
    print("\n=== Checking Matches ===")
    check_matches()
    
    print("\n=== Checking Dashboard Data ===")
    teams_in_counts = check_dashboard_data()
    
    # Compare with actual teams
    all_teams = set(team.name for team in teams)
    missing_teams = all_teams - teams_in_counts
    
    if missing_teams:
        print("\nMissing teams in dashboard data:")
        for team in missing_teams:
            print(f"- {team}")
        print("\nPossible issues:")
        print("1. These teams might not have any matches")
        print("2. These teams might not have player appearances in their matches")
    else:
        print("\nAll teams appear in the dashboard data.")

if __name__ == "__main__":
    main()