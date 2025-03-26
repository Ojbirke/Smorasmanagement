from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
import os
import shutil
import glob

class Command(BaseCommand):
    help = 'Restores database from a backup'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            nargs='?',
            type=str,
            help='Path to the backup file (.json) to restore from. If not provided, will list available backups.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force restore without confirmation prompt',
        )
    
    def handle(self, *args, **options):
        backup_dir = 'backup'
        
        # Check if backup directory exists
        if not os.path.exists(backup_dir):
            raise CommandError(f"Backup directory '{backup_dir}' does not exist.")
        
        # If no backup file specified, list available backups
        if not options['backup_file']:
            json_backups = glob.glob(os.path.join(backup_dir, '*.json'))
            sqlite_backups = glob.glob(os.path.join(backup_dir, '*.sqlite3'))
            
            if not json_backups and not sqlite_backups:
                self.stdout.write(self.style.WARNING('No backups found in the backup directory.'))
                return
            
            self.stdout.write('Available JSON backups:')
            for i, backup in enumerate(sorted(json_backups), 1):
                self.stdout.write(f" {i}. {os.path.basename(backup)}")
            
            self.stdout.write('\nAvailable SQLite backups:')
            for i, backup in enumerate(sorted(sqlite_backups), 1):
                self.stdout.write(f" {i}. {os.path.basename(backup)}")
            
            self.stdout.write('\nTo restore, run:')
            self.stdout.write('  python manage.py restore_database backup/[filename]')
            return
        
        backup_file = options['backup_file']
        
        # Check if the backup file exists
        if not os.path.exists(backup_file):
            raise CommandError(f"Backup file '{backup_file}' does not exist.")
        
        # Get confirmation unless --force flag is used
        if not options['force']:
            confirm = input(f"This will overwrite your current database with data from '{backup_file}'. Are you sure? [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('Restore cancelled.'))
                return
        
        # Perform the restore based on file extension
        if backup_file.endswith('.json'):
            # Restore from JSON (dumpdata) file
            try:
                self.stdout.write(f'Restoring from {backup_file}...')
                # Flush the database first (but keep the superuser)
                call_command('flush', '--noinput')
                # Load data from backup
                call_command('loaddata', backup_file)
                self.stdout.write(self.style.SUCCESS('Database restored successfully from JSON backup.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error restoring database: {str(e)}'))
        
        elif backup_file.endswith('.sqlite3'):
            # Restore from SQLite file (direct copy)
            try:
                db_path = 'db.sqlite3'
                self.stdout.write(f'Restoring SQLite database from {backup_file}...')
                
                # Create a backup of the current database before overwriting
                if os.path.exists(db_path):
                    temp_backup = f'{db_path}.bak'
                    shutil.copy2(db_path, temp_backup)
                    self.stdout.write(f'Created temporary backup at {temp_backup}')
                
                # Copy the backup database over the current one
                shutil.copy2(backup_file, db_path)
                self.stdout.write(self.style.SUCCESS('SQLite database restored successfully.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error restoring database: {str(e)}'))
        
        else:
            raise CommandError(f"Unsupported backup file format. Please use .json or .sqlite3 files.")