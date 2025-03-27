import os
import io
import sys
import shutil
import glob
import re
import time
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    help = 'Creates a database backup that persists across redeployments, keeping only the two latest backups of each type'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            help='Optional custom name for the backup',
        )

    def clean_old_backups(self, backup_dir, prefix, keep=2):
        """
        Clean old backups, keeping only the specified number of most recent ones for a given prefix
        """
        # List all backup files of this type
        json_pattern = os.path.join(backup_dir, f'backup_{prefix}_*.json')
        sqlite_pattern = os.path.join(backup_dir, f'backup_{prefix}_*.sqlite3')
        
        # Get list of files for each type
        json_files = glob.glob(json_pattern)
        sqlite_files = glob.glob(sqlite_pattern)
        
        # Sort files by modification time (newest first)
        json_files.sort(key=os.path.getmtime, reverse=True)
        sqlite_files.sort(key=os.path.getmtime, reverse=True)
        
        # Remove excess JSON files (keeping the newest 'keep' files)
        for file_path in json_files[keep:]:
            try:
                os.remove(file_path)
                self.stdout.write(f"Removed old JSON backup: {os.path.basename(file_path)}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not remove {file_path}: {str(e)}"))
        
        # Remove excess SQLite files
        for file_path in sqlite_files[keep:]:
            try:
                os.remove(file_path)
                self.stdout.write(f"Removed old SQLite backup: {os.path.basename(file_path)}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not remove {file_path}: {str(e)}"))

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
                    
                    # Set the same timestamp on both the JSON and SQLite files to keep them in sync
                    # This ensures they appear with the same timestamp in the UI
                    current_time = time.time()
                    os.utime(sqlite_filepath, (current_time, current_time))
                    os.utime(persistent_sqlite_filepath, (current_time, current_time))
                    os.utime(json_filepath, (current_time, current_time))
                    os.utime(persistent_json_filepath, (current_time, current_time))
                    
                    self.stdout.write(self.style.SUCCESS(f"SQLite database backup created: {sqlite_filename}"))
            
            # Clean up old backups
            if custom_name and (custom_name == 'auto_startup' or custom_name == 'auto_shutdown'):
                # For auto backups, keep only the latest 2
                self.clean_old_backups(persistent_backup_dir, custom_name, keep=2)
            else:
                # For manual backups, clean up excess files keeping the latest 3
                # We need to use a different approach since they don't have a prefix
                self.stdout.write("Cleaning up manual backups, keeping the latest 3...")
                
                # Get all manual backup files (those that don't have auto_startup or auto_shutdown in the name)
                all_json_files = glob.glob(os.path.join(persistent_backup_dir, 'backup_*.json'))
                manual_json_files = [f for f in all_json_files if 'auto_startup' not in f and 'auto_shutdown' not in f]
                
                all_sqlite_files = glob.glob(os.path.join(persistent_backup_dir, 'backup_*.sqlite3'))
                manual_sqlite_files = [f for f in all_sqlite_files if 'auto_startup' not in f and 'auto_shutdown' not in f]
                
                # Sort files by modification time (newest first)
                manual_json_files.sort(key=os.path.getmtime, reverse=True)
                manual_sqlite_files.sort(key=os.path.getmtime, reverse=True)
                
                # Remove excess JSON files (keeping the newest 3 files)
                for file_path in manual_json_files[3:]:
                    try:
                        os.remove(file_path)
                        self.stdout.write(f"Removed old manual JSON backup: {os.path.basename(file_path)}")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Could not remove {file_path}: {str(e)}"))
                
                # Remove excess SQLite files
                for file_path in manual_sqlite_files[3:]:
                    try:
                        os.remove(file_path)
                        self.stdout.write(f"Removed old manual SQLite backup: {os.path.basename(file_path)}")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Could not remove {file_path}: {str(e)}"))
                
                self.stdout.write("Manual backup cleanup completed")
        
        except Exception as e:
            raise CommandError(f"Error creating backup: {str(e)}")
        
        self.stdout.write(self.style.SUCCESS(f"Backups stored in persistent location: {persistent_backup_dir}"))
        self.stdout.write(self.style.SUCCESS(f"Remember to download the backup files for additional safety."))