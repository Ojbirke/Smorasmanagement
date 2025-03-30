from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Team, Player, Match, MatchAppearance
import os
import json
import datetime

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
    
    # Check for deployment backups
    deployment_backups = []
    if os.path.exists(deployment_dir):
        for file in os.listdir(deployment_dir):
            if file.endswith('.json') or file == 'deployment_db.json':
                backup_path = os.path.join(deployment_dir, file)
                try:
                    # Get file size and modification time
                    size = os.path.getsize(backup_path)
                    modified = datetime.datetime.fromtimestamp(os.path.getmtime(backup_path))
                    
                    # Try to read the file to check if it's valid JSON
                    with open(backup_path, 'r') as f:
                        try:
                            data = json.load(f)
                            record_count = len(data)
                            # Get model types in the backup
                            models = {}
                            for item in data:
                                model = item.get('model', 'unknown')
                                models[model] = models.get(model, 0) + 1
                        except json.JSONDecodeError:
                            record_count = 'Invalid JSON'
                            models = {}
                    
                    deployment_backups.append({
                        'path': backup_path,
                        'size': f"{size / 1024:.1f} KB",
                        'modified': modified,
                        'record_count': record_count,
                        'models': models
                    })
                except Exception as e:
                    deployment_backups.append({
                        'path': backup_path,
                        'error': str(e)
                    })
    
    context = {
        'db_info': db_info,
        'team_count': team_count,
        'player_count': player_count,
        'match_count': match_count,
        'appearance_count': appearance_count,
        'teams': teams,
        'team_matches': team_matches,
        'sqlite_files': sqlite_files,
        'deployment_backups': deployment_backups
    }
    
    return render(request, 'teammanager/db_diagnostic.html', context)