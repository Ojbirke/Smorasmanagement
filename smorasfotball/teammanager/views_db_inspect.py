from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from .models import Team, Player, Match, MatchAppearance
import os
import json
import datetime
import psycopg2
import urllib.parse

def db_inspect_view(request):
    """
    Public view for inspecting database connection and data.
    This is for debugging purposes only and should be removed in production.
    """
    # Get database connection information
    db_config = settings.DATABASES['default']
    
    # Sanitize the connection info (remove sensitive parts)
    db_info = {
        'ENGINE': db_config.get('ENGINE', 'Not specified'),
        'NAME': db_config.get('NAME', 'Not specified'),
        'USER': 'Hidden' if db_config.get('USER') else 'Not specified',
        'HOST': 'Hidden' if db_config.get('HOST') else 'Not specified',
        'CONN_MAX_AGE': db_config.get('CONN_MAX_AGE', 'Not specified'),
        'OPTIONS': 'Present' if db_config.get('OPTIONS') else 'Not specified',
        'is_postgres': 'postgresql' in db_config.get('ENGINE', ''),
        'is_sqlite': 'sqlite' in db_config.get('ENGINE', ''),
    }
    
    # Check for DATABASE_URL environment variable
    database_url = os.environ.get('DATABASE_URL', 'Not set')
    db_info['DATABASE_URL_SET'] = 'Yes (PostgreSQL)' if database_url and 'postgresql' in database_url else 'Yes (Other)' if database_url else 'No'
    
    # Direct PostgreSQL connection test
    db_connection_test = {}
    if database_url and 'postgresql' in database_url:
        try:
            parsed_url = urllib.parse.urlparse(database_url)
            db_connection_test['direct_connection'] = 'Attempted'
            
            # Parse connection parameters
            db_params = {
                'dbname': parsed_url.path[1:],
                'user': parsed_url.username,
                'password': parsed_url.password,
                'host': parsed_url.hostname,
                'port': parsed_url.port or 5432,
            }
            
            # Try to connect directly
            conn = psycopg2.connect(**db_params)
            cursor = conn.cursor()
            
            # Test a simple query
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
            table_list = [row[0] for row in cursor.fetchall()]
            
            # Check for specific tables
            cursor.execute("SELECT COUNT(*) FROM teammanager_team;")
            team_count_direct = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM teammanager_match;")
            match_count_direct = cursor.fetchone()[0]
            
            cursor.execute("SELECT * FROM teammanager_team LIMIT 10;")
            team_records = cursor.fetchall()
            
            # Get column names
            column_names = [desc[0] for desc in cursor.description]
            
            # Format team records
            formatted_teams = []
            for record in team_records:
                team_dict = dict(zip(column_names, record))
                formatted_teams.append(team_dict)
            
            db_connection_test['success'] = True
            db_connection_test['tables'] = table_list
            db_connection_test['team_count'] = team_count_direct
            db_connection_test['match_count'] = match_count_direct
            db_connection_test['team_sample'] = formatted_teams
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            db_connection_test['success'] = False
            db_connection_test['error'] = str(e)
    else:
        db_connection_test['direct_connection'] = 'Not attempted (no PostgreSQL DATABASE_URL)'
    
    # Get model counts through Django ORM
    try:
        team_count = Team.objects.count()
        player_count = Player.objects.count()
        match_count = Match.objects.count()
        appearance_count = MatchAppearance.objects.count()
        
        # Get team information
        teams = list(Team.objects.all().values('id', 'name', 'description', 'created_at'))
        
        # Convert datetime objects to strings for display
        for team in teams:
            if 'created_at' in team and team['created_at']:
                team['created_at'] = team['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        # Get match information
        matches = []
        for match in Match.objects.all():
            match_info = {
                'id': match.id,
                'date': match.date.strftime('%Y-%m-%d') if match.date else 'No date',
                'team_id': match.smoras_team_id,
                'opponent': match.opponent_name,
                'location': match.location,
                'score': f"{match.smoras_score}-{match.opponent_score}"
            }
            matches.append(match_info)
        
        orm_data = {
            'success': True,
            'team_count': team_count,
            'player_count': player_count,
            'match_count': match_count,
            'appearance_count': appearance_count,
            'teams': teams,
            'matches': matches
        }
    except Exception as e:
        orm_data = {
            'success': False,
            'error': str(e)
        }
    
    # Context for rendering
    context = {
        'db_info': db_info,
        'db_connection_test': db_connection_test,
        'orm_data': orm_data
    }
    
    return render(request, 'teammanager/db_inspect.html', context)