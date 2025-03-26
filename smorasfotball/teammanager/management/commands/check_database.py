from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from teammanager.models import Team, Player, Match, MatchAppearance, UserProfile
from django.contrib.auth.models import User
import os
import shutil

class Command(BaseCommand):
    help = 'Checks if database has data and creates a backup if needed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create backup of the database',
        )
    
    def handle(self, *args, **options):
        # Check if there's data in the database
        team_count = Team.objects.count()
        player_count = Player.objects.count()
        match_count = Match.objects.count()
        appearance_count = MatchAppearance.objects.count()
        user_count = User.objects.count()
        profile_count = UserProfile.objects.count()
        
        # Display database statistics
        self.stdout.write('Database Contents:')
        self.stdout.write(f'- Teams: {team_count}')
        self.stdout.write(f'- Players: {player_count}')
        self.stdout.write(f'- Matches: {match_count}')
        self.stdout.write(f'- Match Appearances: {appearance_count}')
        self.stdout.write(f'- Users: {user_count}')
        self.stdout.write(f'- User Profiles: {profile_count}')
        
        has_data = team_count > 0 or player_count > 0 or match_count > 0 or user_count > 0
        
        if has_data:
            self.stdout.write(self.style.SUCCESS('Database contains data.'))
            
            # Create backup if requested
            if options['backup']:
                backup_dir = 'backup'
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                
                # Generate filename with timestamp
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.json')
                
                # Create backup using dumpdata
                self.stdout.write(f'Creating backup at {backup_file}...')
                call_command(
                    'dumpdata',
                    '--exclude', 'contenttypes',
                    '--exclude', 'auth.Permission',
                    '--indent', '4',
                    output=backup_file
                )
                self.stdout.write(self.style.SUCCESS(f'Backup created successfully at {backup_file}'))
                
                # Create a copy of the SQLite database file if it exists
                db_path = 'db.sqlite3'
                if os.path.exists(db_path):
                    db_backup = os.path.join(backup_dir, f'db_{timestamp}.sqlite3')
                    shutil.copy2(db_path, db_backup)
                    self.stdout.write(self.style.SUCCESS(f'SQLite database backed up to {db_backup}'))
        else:
            self.stdout.write(self.style.WARNING('Database is empty. No backup needed.'))