import os
import io
import sys
import shutil
import subprocess
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = 'Restores database from persistent backup and recreates superuser'

    def add_arguments(self, parser):
        parser.add_argument(
            'filename',
            type=str,
            help='Backup filename to restore from'
        )
        parser.add_argument(
            '--recreate-admin',
            action='store_true',
            help='Recreate admin user after restore'
        )

    def recreate_superuser(self):
        """Recreates the superuser account after database restoration"""
        self.stdout.write(self.style.WARNING("Attempting to recreate the superuser account..."))
        
        try:
            # Execute the recreate_superuser.py script from the project root
            script_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'recreate_superuser.py')
            
            # Only run if the script exists
            if os.path.exists(script_path):
                # Run the script using the same Python interpreter
                process = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True
                )
                
                if process.returncode == 0:
                    self.stdout.write(self.style.SUCCESS("Superuser was successfully recreated!"))
                    self.stdout.write(process.stdout)
                else:
                    self.stdout.write(self.style.ERROR("Failed to recreate superuser."))
                    self.stdout.write(self.style.ERROR(process.stderr))
            else:
                self.stdout.write(self.style.ERROR(f"Superuser recreation script not found at {script_path}"))
                self.stdout.write(self.style.WARNING("You will need to manually create a superuser with 'python manage.py createsuperuser'"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error recreating superuser: {str(e)}"))
            self.stdout.write(self.style.WARNING("You will need to manually create a superuser"))

    def handle(self, *args, **options):
        filename = options['filename']
        recreate_admin = options['recreate_admin']
        
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
                
                # Save admin user data before flush if needed
                admin_users = []
                if recreate_admin:
                    # Save admin data
                    from django.contrib.auth.models import User
                    admins = User.objects.filter(is_superuser=True)
                    for admin in admins:
                        admin_users.append({
                            'username': admin.username,
                            'email': admin.email,
                            'is_superuser': admin.is_superuser,
                            'is_staff': admin.is_staff
                        })
                
                # Clear existing data while preserving structure
                call_command('flush', '--no-input')
                
                # Load data from the backup
                call_command('loaddata', backup_path)
                
                self.stdout.write(self.style.SUCCESS(f"Database successfully restored from {filename}"))
                
                # Recreate superuser if requested
                if recreate_admin:
                    self.recreate_superuser()
            
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
                
                # Recreate superuser if requested
                if recreate_admin:
                    self.recreate_superuser()
            
            else:
                raise CommandError(f"Unsupported backup file format: {filename}")
        
        except Exception as e:
            raise CommandError(f"Error restoring backup: {str(e)}")