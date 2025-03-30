from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Team, Player, Match, MatchAppearance
import os

@login_required
@user_passes_test(lambda u: u.is_superuser)
def database_diagnostic_view(request):
    """
    View for diagnosing database connection and consistency issues.
    Only accessible to superusers.
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
    
    # Get model counts
    team_count = Team.objects.count()
    player_count = Player.objects.count()
    match_count = Match.objects.count()
    appearance_count = MatchAppearance.objects.count()
    
    # Get team information
    teams = Team.objects.all()
    
    # Get match information for each team
    team_matches = []
    for team in teams:
        team_info = {
            'id': team.id,
            'name': team.name,
            'match_count': team.matches.count(),
            'matches': team.matches.all()
        }
        team_matches.append(team_info)
    
    # Check for potential SQLite files
    sqlite_files = []
    deployment_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    if os.path.exists(deployment_dir):
        for file in os.listdir(deployment_dir):
            if file.endswith('.sqlite3'):
                sqlite_files.append(os.path.join(deployment_dir, file))
    
    context = {
        'db_info': db_info,
        'team_count': team_count,
        'player_count': player_count,
        'match_count': match_count,
        'appearance_count': appearance_count,
        'teams': teams,
        'team_matches': team_matches,
        'sqlite_files': sqlite_files
    }
    
    return render(request, 'teammanager/db_diagnostic.html', context)