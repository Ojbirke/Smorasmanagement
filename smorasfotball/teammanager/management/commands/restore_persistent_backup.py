import os
import io
import sys
import shutil
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = 'Restores database from persistent backup'

    def add_arguments(self, parser):
        parser.add_argument(
            'filename',
            type=str,
            help='Backup filename to restore from'
        )

    def handle(self, *args, **options):
        filename = options['filename']
        
        # Check persistent backup directory
        persistent_backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
        backup_path = os.path.join(persistent_backup_dir, filename)
        
        if not os.path.exists(backup_path):
            raise CommandError(f"Backup file {filename} not found at {persistent_backup_dir}")
        
        try:
            if filename.endswith('.json'):
                # Restore from JSON backup
                self.stdout.write(self.style.WARNING(f"Restoring database from JSON backup: {filename}"))
                self.stdout.write(self.style.WARNING("This will OVERWRITE all existing data!"))
                self.stdout.write("")
                
                # Confirm with user
                confirmation = input("Are you sure you want to continue? [y/N]: ")
                if confirmation.lower() != 'y':
                    self.stdout.write(self.style.WARNING("Restoration cancelled."))
                    return
                
                # Clear existing data while preserving structure
                call_command('flush', '--no-input')
                
                # Load data from the backup
                call_command('loaddata', backup_path)
                
                self.stdout.write(self.style.SUCCESS(f"Database successfully restored from {filename}"))
            
            elif filename.endswith('.sqlite3') and 'sqlite3' in settings.DATABASES['default']['ENGINE']:
                # Restore from SQLite backup
                self.stdout.write(self.style.WARNING(f"Restoring database from SQLite backup: {filename}"))
                self.stdout.write(self.style.WARNING("This will OVERWRITE all existing data!"))
                self.stdout.write("")
                
                # Confirm with user
                confirmation = input("Are you sure you want to continue? [y/N]: ")
                if confirmation.lower() != 'y':
                    self.stdout.write(self.style.WARNING("Restoration cancelled."))
                    return
                
                # Get the current database path
                db_path = settings.DATABASES['default']['NAME']
                
                # Create a backup of current database just in case
                temp_backup = f"{db_path}.before_restore"
                shutil.copy2(db_path, temp_backup)
                self.stdout.write(self.style.SUCCESS(f"Created safety backup at {temp_backup}"))
                
                # Close database connections
                from django.db import connections
                connections.close_all()
                
                # Copy backup over current database
                shutil.copy2(backup_path, db_path)
                
                self.stdout.write(self.style.SUCCESS(f"Database successfully restored from {filename}"))
                self.stdout.write(self.style.SUCCESS("Please restart the application to apply changes."))
            
            else:
                raise CommandError(f"Unsupported backup file format: {filename}")
        
        except Exception as e:
            raise CommandError(f"Error restoring backup: {str(e)}")