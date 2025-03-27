import os
import json
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone

class Command(BaseCommand):
    help = 'Creates a backup specifically for deployment environment'

    def add_arguments(self, parser):
        # Optional name for the backup
        parser.add_argument(
            '--name',
            type=str,
            help='Optional name to include in the backup filename',
        )
        
        # Option to restore from a deployment backup
        parser.add_argument(
            '--restore',
            action='store_true',
            help='Restore from the latest deployment backup',
        )

    def handle(self, *args, **options):
        # Define deployment directory
        deployment_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
        os.makedirs(deployment_dir, exist_ok=True)
        
        # If restore option is selected
        if options['restore']:
            self.restore_deployment_backup(deployment_dir)
            return
        
        # Otherwise, create a new backup
        self.create_deployment_backup(deployment_dir, options.get('name'))
    
    def create_deployment_backup(self, deployment_dir, name=None):
        """Create a backup specifically for deployment use"""
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        name_suffix = f"_{name}" if name else ""
        
        # Define backup filename
        backup_filename = f"deployment_backup{name_suffix}_{timestamp}.json"
        backup_path = os.path.join(deployment_dir, backup_filename)
        
        # Create JSON backup using dumpdata
        try:
            self.stdout.write(self.style.SUCCESS('Creating deployment database backup...'))
            
            with open(backup_path, 'w') as f:
                call_command(
                    'dumpdata',
                    exclude=['contenttypes', 'auth.permission'],
                    natural_foreign=True,
                    stdout=f
                )
            
            # Also create a symlink to the latest backup
            latest_path = os.path.join(deployment_dir, "deployment_db.json")
            if os.path.exists(latest_path):
                os.remove(latest_path)
            shutil.copy2(backup_path, latest_path)
            
            # Verify the backup content
            self.verify_backup(backup_path)
            
            self.stdout.write(self.style.SUCCESS(f'Deployment backup created: {backup_filename}'))
            self.stdout.write(self.style.SUCCESS(f'Also linked as: deployment_db.json'))
            
            return backup_path
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating deployment backup: {str(e)}'))
            if os.path.exists(backup_path):
                os.remove(backup_path)
            raise CommandError(f'Failed to create deployment backup: {str(e)}')
    
    def restore_deployment_backup(self, deployment_dir):
        """Restore from the latest deployment backup"""
        latest_path = os.path.join(deployment_dir, "deployment_db.json")
        
        if not os.path.exists(latest_path):
            raise CommandError("No deployment backup found to restore from")
        
        # Initialize temp_backup_path at the beginning to avoid unbound variable issues
        temp_backup_path = os.path.join(deployment_dir, "temp_deployment_restore.json")
        
        try:
            self.stdout.write(self.style.SUCCESS('Restoring from deployment backup...'))
            
            # Verify the backup before restoring
            self.verify_backup(latest_path)
            
            # Create a temporary copy of the backup to modify if needed
            shutil.copy2(latest_path, temp_backup_path)
            
            # Clear existing data (but keep structure)
            # We use reset_db instead of flush to avoid integrity errors
            from django.db import connection
            if connection.vendor == 'sqlite':
                # For SQLite, we use a more aggressive approach
                with connection.cursor() as cursor:
                    # Get list of tables excluding django_migrations
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'django_migrations' AND name != 'sqlite_sequence';")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Clear all tables except migrations
                    for table in tables:
                        try:
                            cursor.execute(f"DELETE FROM {table};")
                            self.stdout.write(f"Cleared table: {table}")
                        except Exception as e:
                            self.stdout.write(f"Error clearing table {table}: {str(e)}")
            else:
                # For other databases, use flush
                call_command('flush', '--no-input')
            
            # Let's modify the backup to avoid UserProfile conflicts
            try:
                with open(temp_backup_path, 'r') as f:
                    data = json.load(f)
                
                # Get a list of models that might need special handling
                user_profiles = [item for item in data if item['model'] == 'teammanager.userprofile']
                
                if user_profiles:
                    self.stdout.write(f"Found {len(user_profiles)} user profiles in backup")
                    
                    # Remove existing user profiles from the backup
                    # We'll handle them specially to avoid conflicts
                    data = [item for item in data if item['model'] != 'teammanager.userprofile']
                    
                    # Write the modified file
                    with open(temp_backup_path, 'w') as f:
                        json.dump(data, f)
                
                # Load the data (without user profiles)
                call_command('loaddata', temp_backup_path)
                
                # Now handle user profiles separately
                if user_profiles:
                    self.stdout.write("Handling user profiles separately...")
                    
                    # We need to recreate the user profiles manually
                    from django.contrib.auth.models import User
                    from teammanager.models import UserProfile
                    
                    # First, delete any existing profiles to avoid conflicts
                    UserProfile.objects.all().delete()
                    
                    # Recreate user profiles based on backup data
                    for profile in user_profiles:
                        try:
                            profile_data = profile['fields']
                            user_id = profile_data.get('user')
                            
                            # Check if user exists
                            if User.objects.filter(id=user_id).exists():
                                # Create user profile
                                UserProfile.objects.create(
                                    user_id=user_id,
                                    is_player=profile_data.get('is_player', False),
                                    is_coach=profile_data.get('is_coach', False),
                                    is_guardian=profile_data.get('is_guardian', False),
                                    is_approved=profile_data.get('is_approved', False)
                                )
                                self.stdout.write(f"Recreated user profile for User ID: {user_id}")
                            else:
                                self.stdout.write(self.style.WARNING(f"User ID {user_id} not found, skipping profile"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Error recreating profile: {str(e)}"))
                
            except Exception as e:
                # If we still get an error, try a fallback approach
                restore_error = e  # Store the error for later reference
                self.stdout.write(self.style.WARNING(f'Standard restore failed: {str(restore_error)}. Trying fallback method...'))
                
                # Make sure models are in sync
                call_command('migrate', '--run-syncdb')
                
                try:
                    # For a more aggressive approach with SQLite
                    from django.db import connection
                    if connection.vendor == 'sqlite':
                        # Reset the database completely
                        self.stdout.write("Resetting SQLite database completely...")
                        with connection.cursor() as cursor:
                            cursor.execute("PRAGMA foreign_keys = OFF;")
                            # Get all tables
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'django_migrations' AND name != 'sqlite_sequence';")
                            tables = [row[0] for row in cursor.fetchall()]
                            
                            # Drop all tables except migrations
                            for table in tables:
                                try:
                                    cursor.execute(f"DROP TABLE IF EXISTS {table};")
                                    self.stdout.write(f"Dropped table: {table}")
                                except Exception as table_error:
                                    self.stdout.write(f"Error dropping table {table}: {str(table_error)}")
                            
                            cursor.execute("PRAGMA foreign_keys = ON;")
                        
                        # Run migrations to recreate tables
                        call_command('migrate')
                    
                    # Try one more time with loaddata on the original backup
                    call_command('loaddata', latest_path)
                except Exception as secondary_error:
                    self.stdout.write(self.style.ERROR(f'Fallback restore failed: {str(secondary_error)}'))
                    raise CommandError(f'Multiple restore attempts failed: {str(restore_error)}, then: {str(secondary_error)}')
            
            # Clean up the temporary file
            if os.path.exists(temp_backup_path):
                os.remove(temp_backup_path)
            
            self.stdout.write(self.style.SUCCESS('Database restored successfully from deployment backup'))
            
            # Record this restore in environment variables for diagnostic purposes
            os.environ['LAST_RESTORED_BACKUP'] = "deployment_db.json (Deployment Specific)"
            os.environ['LAST_RESTORE_TIME'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return True
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error restoring from deployment backup: {str(e)}'))
            # Clean up temporary file if it exists
            if os.path.exists(temp_backup_path):
                os.remove(temp_backup_path)
            raise CommandError(f'Failed to restore from deployment backup: {str(e)}')
    
    def verify_backup(self, backup_path):
        """Verify the backup contains required data"""
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            # Count essential objects
            user_count = len([item for item in backup_data if item['model'] == 'auth.user'])
            player_count = len([item for item in backup_data if item['model'] == 'teammanager.player'])
            team_count = len([item for item in backup_data if item['model'] == 'teammanager.team'])
            match_count = len([item for item in backup_data if item['model'] == 'teammanager.match'])
            
            self.stdout.write(self.style.SUCCESS(f'Backup contains:'))
            self.stdout.write(f'  - {user_count} users')
            self.stdout.write(f'  - {team_count} teams')
            self.stdout.write(f'  - {player_count} players')
            self.stdout.write(f'  - {match_count} matches')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to verify backup: {str(e)}'))