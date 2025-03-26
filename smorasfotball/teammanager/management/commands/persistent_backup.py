import os
import io
import sys
import shutil
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    help = 'Creates a database backup that persists across redeployments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            help='Optional custom name for the backup',
        )

    def handle(self, *args, **options):
        # Create standard backup directory
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create persistent backup directory (parent directory of the project)
        persistent_backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
        os.makedirs(persistent_backup_dir, exist_ok=True)
        
        custom_name = options.get('name')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        if custom_name:
            json_filename = f'backup_{custom_name}_{timestamp}.json'
            sqlite_filename = f'backup_{custom_name}_{timestamp}.sqlite3'
        else:
            json_filename = f'backup_{timestamp}.json'
            sqlite_filename = f'backup_{timestamp}.sqlite3'
        
        json_filepath = os.path.join(backup_dir, json_filename)
        persistent_json_filepath = os.path.join(persistent_backup_dir, json_filename)
        
        # Backup data as JSON
        try:
            # Use Django's dumpdata command to create JSON backup
            output = io.StringIO()
            original_stdout = sys.stdout
            sys.stdout = output
            call_command('dumpdata', '--exclude', 'auth.permission', '--exclude', 'contenttypes', 
                        '--exclude', 'admin.logentry', '--indent', '2', stdout=output)
            sys.stdout = original_stdout
            
            # Save to standard backup location
            with open(json_filepath, 'w') as f:
                f.write(output.getvalue())
            
            # Copy to persistent location
            with open(persistent_json_filepath, 'w') as f:
                f.write(output.getvalue())
            
            self.stdout.write(self.style.SUCCESS(f"JSON data backup created: {json_filename}"))
            
            # If using SQLite, also backup the database file
            if 'sqlite3' in settings.DATABASES['default']['ENGINE']:
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path):
                    sqlite_filepath = os.path.join(backup_dir, sqlite_filename)
                    persistent_sqlite_filepath = os.path.join(persistent_backup_dir, sqlite_filename)
                    
                    # Create a copy of the SQLite database in standard location
                    shutil.copy2(db_path, sqlite_filepath)
                    # Create a copy in persistent location
                    shutil.copy2(db_path, persistent_sqlite_filepath)
                    
                    self.stdout.write(self.style.SUCCESS(f"SQLite database backup created: {sqlite_filename}"))
        
        except Exception as e:
            raise CommandError(f"Error creating backup: {str(e)}")
        
        self.stdout.write(self.style.SUCCESS(f"Backups stored in persistent location: {persistent_backup_dir}"))
        self.stdout.write(self.style.SUCCESS(f"Remember to download the backup files for additional safety."))