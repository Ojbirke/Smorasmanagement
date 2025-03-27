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
        
        # Format of backup (json or sqlite)
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'sqlite'],
            default='json',
            help='Format of the backup (json or sqlite)',
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
        backup_format = options.get('format', 'json')
        self.create_deployment_backup(deployment_dir, options.get('name'), backup_format)
    
    def create_deployment_backup(self, deployment_dir, name=None, backup_format='json'):
        """Create a backup specifically for deployment use"""
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        name_suffix = f"_{name}" if name else ""
        
        if backup_format == 'json':
            # Define backup filename for JSON format
            backup_filename = f"deployment_backup{name_suffix}_{timestamp}.json"
            backup_path = os.path.join(deployment_dir, backup_filename)
            
            # Create JSON backup using dumpdata
            try:
                self.stdout.write(self.style.SUCCESS('Creating JSON deployment database backup...'))
                
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
                
                self.stdout.write(self.style.SUCCESS(f'JSON deployment backup created: {backup_filename}'))
                self.stdout.write(self.style.SUCCESS(f'Also linked as: deployment_db.json'))
                
                return backup_path
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating JSON deployment backup: {str(e)}'))
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                raise CommandError(f'Failed to create JSON deployment backup: {str(e)}')
                
        elif backup_format == 'sqlite':
            # Define backup filename for SQLite format
            backup_filename = f"deployment_backup{name_suffix}_{timestamp}.sqlite"
            backup_path = os.path.join(deployment_dir, backup_filename)
            
            try:
                self.stdout.write(self.style.SUCCESS('Creating SQLite deployment database backup...'))
                
                # Get the current database path from settings
                from django.db import connections
                db_path = connections['default'].settings_dict['NAME']
                
                if not os.path.exists(db_path):
                    raise CommandError(f"Database file not found at: {db_path}")
                
                # Create a direct copy of the SQLite database file
                shutil.copy2(db_path, backup_path)
                
                # Also create a link to the latest backup
                latest_path = os.path.join(deployment_dir, "deployment_db.sqlite")
                if os.path.exists(latest_path):
                    os.remove(latest_path)
                shutil.copy2(backup_path, latest_path)
                
                self.stdout.write(self.style.SUCCESS(f'SQLite deployment backup created: {backup_filename}'))
                self.stdout.write(self.style.SUCCESS(f'Also linked as: deployment_db.sqlite'))
                
                return backup_path
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating SQLite deployment backup: {str(e)}'))
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                raise CommandError(f'Failed to create SQLite deployment backup: {str(e)}')
        
        else:
            raise CommandError(f'Unsupported backup format: {backup_format}')
    
    def restore_deployment_backup(self, deployment_dir):
        """Restore from the latest deployment backup"""
        # Check for SQLite backup first (preferred)
        sqlite_path = os.path.join(deployment_dir, "deployment_db.sqlite")
        json_path = os.path.join(deployment_dir, "deployment_db.json")
        
        # Determine which backup format to use
        if os.path.exists(sqlite_path):
            self.stdout.write(self.style.SUCCESS('Found SQLite deployment backup'))
            return self.restore_sqlite_backup(sqlite_path)
        elif os.path.exists(json_path):
            self.stdout.write(self.style.SUCCESS('Found JSON deployment backup'))
            return self.restore_json_backup(json_path)
        else:
            raise CommandError("No deployment backup found to restore from (checked both .sqlite and .json)")
    
    def restore_sqlite_backup(self, backup_path):
        """Restore from SQLite backup file"""
        try:
            self.stdout.write(self.style.SUCCESS(f'Restoring from SQLite deployment backup: {backup_path}'))
            
            # Get the current database path
            from django.db import connections
            db_path = connections['default'].settings_dict['NAME']
            
            if not os.path.exists(db_path):
                self.stdout.write(self.style.WARNING(f"Current database file not found, will create new one at: {db_path}"))
            
            # Close all database connections
            from django.db import connection
            connection.close()
            
            # Back up the current database file just in case
            if os.path.exists(db_path):
                temp_backup = f"{db_path}.bak"
                shutil.copy2(db_path, temp_backup)
                self.stdout.write(f"Created temporary backup of current database at: {temp_backup}")
            
            # Copy the backup file to the current database location
            shutil.copy2(backup_path, db_path)
            self.stdout.write(self.style.SUCCESS(f"Replaced database with backup from: {backup_path}"))
            
            # Record this restore in environment variables for diagnostic purposes
            os.environ['LAST_RESTORED_BACKUP'] = os.path.basename(backup_path) + " (Deployment Specific)"
            os.environ['LAST_RESTORE_TIME'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error restoring from SQLite deployment backup: {str(e)}'))
            raise CommandError(f'Failed to restore from SQLite deployment backup: {str(e)}')
    
    def restore_json_backup(self, backup_path):
        """Restore from JSON backup file"""
        # Initialize temp_backup_path at the beginning to avoid unbound variable issues
        temp_backup_path = os.path.join(os.path.dirname(backup_path), "temp_deployment_restore.json")
        
        try:
            self.stdout.write(self.style.SUCCESS('Restoring from JSON deployment backup...'))
            
            # Verify the backup before restoring
            self.verify_backup(backup_path)
            
            # Create a temporary copy of the backup to modify if needed
            shutil.copy2(backup_path, temp_backup_path)
            
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
                                user_profile = UserProfile()
                                user_profile.user_id = user_id
                                
                                # Assign role and status if they exist in the profile data
                                if 'role' in profile_data:
                                    user_profile.role = profile_data['role']
                                elif 'is_player' in profile_data:
                                    # Handle legacy format
                                    user_profile.is_player = profile_data.get('is_player', False)
                                    user_profile.is_coach = profile_data.get('is_coach', False)
                                    user_profile.is_guardian = profile_data.get('is_guardian', False)
                                
                                # Handle status field
                                if 'status' in profile_data:
                                    user_profile.status = profile_data['status']
                                elif 'is_approved' in profile_data:
                                    # Handle legacy format
                                    user_profile.is_approved = profile_data.get('is_approved', False)
                                
                                user_profile.save()
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
                    call_command('loaddata', backup_path)
                except Exception as secondary_error:
                    self.stdout.write(self.style.ERROR(f'Fallback restore failed: {str(secondary_error)}'))
                    raise CommandError(f'Multiple restore attempts failed: {str(restore_error)}, then: {str(secondary_error)}')
            
            # Clean up the temporary file
            if os.path.exists(temp_backup_path):
                os.remove(temp_backup_path)
            
            self.stdout.write(self.style.SUCCESS('Database restored successfully from JSON deployment backup'))
            
            # Record this restore in environment variables for diagnostic purposes
            os.environ['LAST_RESTORED_BACKUP'] = os.path.basename(backup_path) + " (Deployment Specific)"
            os.environ['LAST_RESTORE_TIME'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return True
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error restoring from JSON deployment backup: {str(e)}'))
            # Clean up temporary file if it exists
            if os.path.exists(temp_backup_path):
                os.remove(temp_backup_path)
            raise CommandError(f'Failed to restore from JSON deployment backup: {str(e)}')
    
    def verify_backup(self, backup_path):
        """Verify the backup contains required data"""
        # Check if it's a SQLite or JSON backup
        if backup_path.endswith('.sqlite'):
            try:
                # For SQLite backups, we check if the file is a valid SQLite database
                import sqlite3
                
                # Try to connect to the SQLite file
                conn = sqlite3.connect(backup_path)
                cursor = conn.cursor()
                
                # Check if essential tables exist
                tables = []
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                for row in cursor.fetchall():
                    tables.append(row[0])
                
                # Check counts of essential tables
                user_count = 0
                player_count = 0
                team_count = 0
                match_count = 0
                
                if 'auth_user' in tables:
                    cursor.execute("SELECT COUNT(*) FROM auth_user;")
                    user_count = cursor.fetchone()[0]
                
                if 'teammanager_player' in tables:
                    cursor.execute("SELECT COUNT(*) FROM teammanager_player;")
                    player_count = cursor.fetchone()[0]
                    
                if 'teammanager_team' in tables:
                    cursor.execute("SELECT COUNT(*) FROM teammanager_team;")
                    team_count = cursor.fetchone()[0]
                    
                if 'teammanager_match' in tables:
                    cursor.execute("SELECT COUNT(*) FROM teammanager_match;")
                    match_count = cursor.fetchone()[0]
                
                conn.close()
                
                self.stdout.write(self.style.SUCCESS(f'SQLite backup contains:'))
                self.stdout.write(f'  - {user_count} users')
                self.stdout.write(f'  - {team_count} teams')
                self.stdout.write(f'  - {player_count} players')
                self.stdout.write(f'  - {match_count} matches')
                
                return True
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to verify SQLite backup: {str(e)}'))
                raise CommandError(f'Invalid SQLite backup file: {str(e)}')
                
        else:  # JSON backup
            try:
                with open(backup_path, 'r') as f:
                    backup_data = json.load(f)
                
                # Count essential objects
                user_count = len([item for item in backup_data if item['model'] == 'auth.user'])
                player_count = len([item for item in backup_data if item['model'] == 'teammanager.player'])
                team_count = len([item for item in backup_data if item['model'] == 'teammanager.team'])
                match_count = len([item for item in backup_data if item['model'] == 'teammanager.match'])
                
                self.stdout.write(self.style.SUCCESS(f'JSON backup contains:'))
                self.stdout.write(f'  - {user_count} users')
                self.stdout.write(f'  - {team_count} teams')
                self.stdout.write(f'  - {player_count} players')
                self.stdout.write(f'  - {match_count} matches')
                
                return True
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to verify JSON backup: {str(e)}'))
                raise CommandError(f'Invalid JSON backup file: {str(e)}')