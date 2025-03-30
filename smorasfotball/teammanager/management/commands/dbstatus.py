from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings
import os
import sys
import subprocess


class Command(BaseCommand):
    help = 'Display current database connection information and statistics'

    def handle(self, *args, **options):
        # Print environment info
        self.stdout.write(self.style.SUCCESS('Database Status Report'))
        self.stdout.write('-' * 50)
        
        # Check DATABASE_URL environment variable
        db_url = os.environ.get('DATABASE_URL', 'Not set')
        masked_url = 'Not set'
        if db_url != 'Not set':
            parts = db_url.split('@')
            if len(parts) > 1:
                # Hide sensitive parts (password)
                auth = parts[0].split(':')
                if len(auth) > 2:
                    masked_url = f"{auth[0]}:****@{'*' * len(parts[1])}"
                else:
                    masked_url = f"{parts[0]}@{'*' * len(parts[1])}"
            else:
                masked_url = '*' * len(db_url)
        
        self.stdout.write(f"DATABASE_URL: {masked_url}")
        
        # Check if additional PostgreSQL environment variables are set
        pg_vars = ['PGDATABASE', 'PGUSER', 'PGHOST', 'PGPORT', 'PGPASSWORD']
        pg_info = {}
        for var in pg_vars:
            if var == 'PGPASSWORD' and os.environ.get(var):
                pg_info[var] = '****'
            else:
                pg_info[var] = os.environ.get(var, 'Not set')
        
        self.stdout.write(f"PostgreSQL Variables:")
        for var, value in pg_info.items():
            self.stdout.write(f"  {var}: {value}")
        
        # Get database engine information
        db_config = settings.DATABASES['default']
        engine = db_config.get('ENGINE', 'unknown')
        
        if 'sqlite' in engine.lower():
            db_type = 'SQLite'
            db_name = db_config.get('NAME', 'unknown')
            self.stdout.write(self.style.WARNING(f"Database Type: {db_type}"))
            self.stdout.write(f"Database Name: {db_name}")
        elif 'postgresql' in engine.lower():
            db_type = 'PostgreSQL'
            db_name = db_config.get('NAME', 'unknown')
            db_user = db_config.get('USER', 'unknown')
            db_host = db_config.get('HOST', 'unknown')
            db_port = db_config.get('PORT', 'unknown')
            
            self.stdout.write(self.style.SUCCESS(f"Database Type: {db_type}"))
            self.stdout.write(f"Database Name: {db_name}")
            self.stdout.write(f"Database User: {db_user}")
            self.stdout.write(f"Database Host: {db_host}")
            self.stdout.write(f"Database Port: {db_port}")
        else:
            self.stdout.write(self.style.ERROR(f"Unknown Database Type: {engine}"))
        
        # Test database connection
        self.stdout.write('-' * 50)
        self.stdout.write("Testing database connection...")
        
        try:
            connection = connections['default']
            connection.ensure_connection()
            if connection.is_usable():
                self.stdout.write(self.style.SUCCESS("Connection Status: Connected"))
            else:
                self.stdout.write(self.style.ERROR("Connection Status: Failed - Connection is not usable"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Connection Status: Failed - {str(e)}"))
        
        # Get database statistics
        self.stdout.write('-' * 50)
        self.stdout.write("Database Statistics:")
        
        try:
            from django.contrib.auth.models import User
            from teammanager.models import Team, Player, Match, MatchAppearance, UserProfile
            
            teams = Team.objects.count()
            players = Player.objects.count()
            matches = Match.objects.count()
            appearances = MatchAppearance.objects.count()
            users = User.objects.count()
            profiles = UserProfile.objects.count()
            
            self.stdout.write(f"Teams: {teams}")
            self.stdout.write(f"Players: {players}")
            self.stdout.write(f"Matches: {matches}")
            self.stdout.write(f"Match Appearances: {appearances}")
            self.stdout.write(f"Users: {users}")
            self.stdout.write(f"User Profiles: {profiles}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error getting statistics: {str(e)}"))
        
        # Check production markers
        self.stdout.write('-' * 50)
        self.stdout.write("Production Environment Check:")
        
        from pathlib import Path
        
        # Check for production markers
        base_dir = Path(settings.BASE_DIR).parent
        prod_marker = base_dir / 'deployment' / 'IS_PRODUCTION_ENVIRONMENT'
        perm_marker = base_dir / 'deployment' / 'PERMANENT_PRODUCTION_MARKER'
        
        if prod_marker.exists():
            self.stdout.write(self.style.SUCCESS("Production Marker: Found"))
            with open(prod_marker, 'r') as f:
                marker_content = f.read().strip()
                self.stdout.write(f"  {marker_content}")
        else:
            self.stdout.write(self.style.WARNING("Production Marker: Not Found"))
        
        if perm_marker.exists():
            self.stdout.write(self.style.SUCCESS("Permanent Production Marker: Found"))
        else:
            self.stdout.write(self.style.WARNING("Permanent Production Marker: Not Found"))
        
        # Final recommendation
        self.stdout.write('-' * 50)
        if 'sqlite' in engine.lower() and (prod_marker.exists() or perm_marker.exists()):
            self.stdout.write(self.style.ERROR(
                "RECOMMENDATION: This appears to be a production environment using SQLite.\n"
                "You should migrate to PostgreSQL by running:\n"
                "  python fix_production_postgres.py"
            ))
        elif 'postgresql' in engine.lower() and (prod_marker.exists() or perm_marker.exists()):
            self.stdout.write(self.style.SUCCESS(
                "RECOMMENDATION: This production environment is correctly using PostgreSQL."
            ))
        elif 'sqlite' in engine.lower():
            self.stdout.write(self.style.WARNING(
                "RECOMMENDATION: This development environment is using SQLite.\n"
                "This is fine for development, but production should use PostgreSQL."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "RECOMMENDATION: This environment is using PostgreSQL, which is recommended."
            ))