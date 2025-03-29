from django.core.management.base import BaseCommand
from django.db import connection
from teammanager.models import Team, Player, Match, MatchAppearance, UserProfile
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = 'Checks if database has data and displays database information'
    
    def handle(self, *args, **options):
        # Get database connection info
        db_settings = connection.settings_dict
        db_engine = db_settings['ENGINE']
        db_name = db_settings.get('NAME', 'unknown')
        db_host = db_settings.get('HOST', 'localhost')
        
        # Check if using PostgreSQL
        is_postgres = 'postgresql' in db_engine
        
        # Check if there's data in the database
        team_count = Team.objects.count()
        player_count = Player.objects.count()
        match_count = Match.objects.count()
        appearance_count = MatchAppearance.objects.count()
        user_count = User.objects.count()
        profile_count = UserProfile.objects.count()
        
        # Display database information
        self.stdout.write('Database Information:')
        self.stdout.write(f'- Engine: {"PostgreSQL" if is_postgres else "SQLite"}')
        self.stdout.write(f'- Name: {db_name}')
        if is_postgres:
            self.stdout.write(f'- Host: {db_host}')
        
        # Display database statistics
        self.stdout.write('\nDatabase Contents:')
        self.stdout.write(f'- Teams: {team_count}')
        self.stdout.write(f'- Players: {player_count}')
        self.stdout.write(f'- Matches: {match_count}')
        self.stdout.write(f'- Match Appearances: {appearance_count}')
        self.stdout.write(f'- Users: {user_count}')
        self.stdout.write(f'- User Profiles: {profile_count}')
        
        has_data = team_count > 0 or player_count > 0 or match_count > 0 or user_count > 0
        
        if has_data:
            self.stdout.write(self.style.SUCCESS('\nDatabase contains data.'))
        else:
            self.stdout.write(self.style.WARNING('\nDatabase is empty.'))
            
        # Return statistics as a dictionary
        stats = {
            'teams': team_count,
            'players': player_count,
            'matches': match_count,
            'appearances': appearance_count,
            'users': user_count,
            'profiles': profile_count,
            'has_data': has_data,
            'is_postgres': is_postgres,
            'db_name': db_name,
            'db_host': db_host,
        }
        
        return stats