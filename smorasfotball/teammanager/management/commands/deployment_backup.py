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
        
        # Check if deployment directory exists and is writable
        if not os.path.exists(deployment_dir):
            os.makedirs(deployment_dir, exist_ok=True)
            self.stdout.write(f"Created deployment directory: {deployment_dir}")
        
        if not os.access(deployment_dir, os.W_OK):
            self.stdout.write(self.style.WARNING(f"Warning: Deployment directory {deployment_dir} is not writable!"))
            try:
                # Try to fix permissions
                os.chmod(deployment_dir, 0o755)
                self.stdout.write("Fixed permissions on deployment directory")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to fix permissions: {str(e)}"))
                
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
                
                # Set appropriate permissions
                os.chmod(backup_path, 0o644)
                os.chmod(latest_path, 0o644)
                
                # Verify the backup content
                self.verify_backup(backup_path)
                
                self.stdout.write(self.style.SUCCESS(f'JSON deployment backup created: {backup_filename}'))
                self.stdout.write(self.style.SUCCESS(f'Also linked as: deployment_db.json'))
                
                # Sync backup to repository for persistence across deployments
                try:
                    self.stdout.write("Syncing backup to repository for persistence...")
                    call_command('sync_backups_with_repo', push=True)
                    self.stdout.write(self.style.SUCCESS("Backup synced to repository"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Failed to sync to repository: {str(e)}"))
                    self.stdout.write(self.style.WARNING("Backup created locally but not synced to repository"))
                
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
                
                # Check if the source database is readable
                if not os.access(db_path, os.R_OK):
                    self.stdout.write(self.style.WARNING(f"Warning: Source database {db_path} is not readable!"))
                    try:
                        # Try to fix permissions
                        os.chmod(db_path, 0o644)
                        self.stdout.write("Fixed permissions on source database")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to fix permissions: {str(e)}"))
                
                # Create a direct copy of the SQLite database file
                shutil.copy2(db_path, backup_path)
                
                # Also create a link to the latest backup
                latest_path = os.path.join(deployment_dir, "deployment_db.sqlite")
                if os.path.exists(latest_path):
                    os.remove(latest_path)
                shutil.copy2(backup_path, latest_path)
                
                # Set appropriate permissions
                os.chmod(backup_path, 0o644)
                os.chmod(latest_path, 0o644)
                
                self.stdout.write(self.style.SUCCESS(f'SQLite deployment backup created: {backup_filename}'))
                self.stdout.write(self.style.SUCCESS(f'Also linked as: deployment_db.sqlite'))
                
                # Sync backup to repository for persistence across deployments
                try:
                    self.stdout.write("Syncing backup to repository for persistence...")
                    call_command('sync_backups_with_repo', push=True)
                    self.stdout.write(self.style.SUCCESS("Backup synced to repository"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Failed to sync to repository: {str(e)}"))
                    self.stdout.write(self.style.WARNING("Backup created locally but not synced to repository"))
                
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
        
        # List all available files for debugging
        self.stdout.write(self.style.WARNING("DEBUG: Listing all files in deployment directory:"))
        try:
            for file in os.listdir(deployment_dir):
                file_path = os.path.join(deployment_dir, file)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    self.stdout.write(f"  File: {file}, Size: {file_size} bytes")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error listing files: {str(e)}"))
            
        # Look for backup files with pattern matching to find production backups
        # This is a failsafe in case the main deployment_db files are missing
        backup_files = []
        try:
            for file in os.listdir(deployment_dir):
                if file.endswith('.sqlite') and ('production' in file or 'deployment' in file):
                    backup_files.append(os.path.join(deployment_dir, file))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error searching for backup files: {str(e)}"))
        
        if backup_files:
            self.stdout.write(self.style.SUCCESS(f"Found {len(backup_files)} additional backup files that could be used"))
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            self.stdout.write(f"Most recent backup: {backup_files[0]}")
        
        # Check directory permissions
        try:
            os.access(deployment_dir, os.W_OK)
            self.stdout.write(self.style.SUCCESS("Deployment directory is writable"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Deployment directory permission check error: {str(e)}"))
            
        # Now determine which backup format to use
        # Check file permissions and sizes to verify they are valid backups
        sqlite_is_valid = False
        json_is_valid = False
        
        if os.path.exists(sqlite_path):
            try:
                sqlite_size = os.path.getsize(sqlite_path)
                sqlite_is_valid = sqlite_size > 1000  # Basic size check
                self.stdout.write(self.style.SUCCESS(f'Found SQLite deployment backup: {sqlite_path}, Size: {sqlite_size} bytes'))
                
                # Check permissions
                if not os.access(sqlite_path, os.R_OK):
                    self.stdout.write(self.style.WARNING(f"WARNING: SQLite backup exists but is not readable"))
                    # Try to fix permissions
                    os.chmod(sqlite_path, 0o644)
                    self.stdout.write(self.style.SUCCESS("Fixed permissions on SQLite backup"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error checking SQLite backup: {str(e)}"))
                
        if os.path.exists(json_path):
            try:
                json_size = os.path.getsize(json_path)
                json_is_valid = json_size > 10  # Basic size check
                self.stdout.write(self.style.SUCCESS(f'Found JSON deployment backup: {json_path}, Size: {json_size} bytes'))
                
                # Check permissions
                if not os.access(json_path, os.R_OK):
                    self.stdout.write(self.style.WARNING(f"WARNING: JSON backup exists but is not readable"))
                    # Try to fix permissions
                    os.chmod(json_path, 0o644)
                    self.stdout.write(self.style.SUCCESS("Fixed permissions on JSON backup"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error checking JSON backup: {str(e)}"))
                
        # Use the valid backups in order of preference
        success = False
        
        # First try SQLite (preferred method)
        if sqlite_is_valid:
            try:
                self.stdout.write(self.style.SUCCESS('Using SQLite backup (preferred method)'))
                success = self.restore_sqlite_backup(sqlite_path)
                if success:
                    return True
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'SQLite restore attempt failed: {str(e)}'))
                # Continue to next method
        
        # Then try JSON backup
        if not success and json_is_valid:
            try:
                self.stdout.write(self.style.SUCCESS('Using JSON backup as fallback'))
                success = self.restore_json_backup(json_path)
                if success:
                    return True
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'JSON restore attempt failed: {str(e)}'))
                # Continue to next method
        
        # If standard backups fail, try additional backup files found
        if not success and backup_files:
            try:
                self.stdout.write(self.style.SUCCESS(f'Trying most recent backup file: {backup_files[0]}'))
                if backup_files[0].endswith('.sqlite'):
                    success = self.restore_sqlite_backup(backup_files[0])
                else:
                    success = self.restore_json_backup(backup_files[0])
                if success:
                    return True
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Additional backup restore attempt failed: {str(e)}'))
                # Continue to next method
                
        # If all else fails, recreate the deployment_db files by copying from backup directory
        if backup_files and not (sqlite_is_valid or json_is_valid):
            try:
                for backup_file in backup_files:
                    if backup_file.endswith('.sqlite'):
                        self.stdout.write(self.style.SUCCESS(f'Creating deployment_db.sqlite from {backup_file}'))
                        shutil.copy2(backup_file, sqlite_path)
                        os.chmod(sqlite_path, 0o644)
                        success = self.restore_sqlite_backup(sqlite_path)
                        if success:
                            return True
                        break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to create deployment_db files: {str(e)}'))
                
        if not success:
            self.stdout.write(self.style.ERROR("ALL RESTORATION METHODS FAILED!"))
            raise CommandError("No usable deployment backup found to restore from")
    
    def restore_sqlite_backup(self, backup_path):
        """Restore from SQLite backup file"""
        self.stdout.write(self.style.SUCCESS(f'STARTING SQLITE RESTORATION FROM: {backup_path}'))
        self.stdout.write(f'Backup file size: {os.path.getsize(backup_path)} bytes')
        self.stdout.write(f'Backup last modified: {os.path.getmtime(backup_path)}')
        
        try:
            # Get the current database path
            from django.db import connections
            db_path = connections['default'].settings_dict['NAME']
            
            if not os.path.exists(db_path):
                self.stdout.write(self.style.WARNING(f"Current database file not found, will create new one at: {db_path}"))
                # Make sure parent directory exists
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Close all database connections
            from django.db import connection
            connection.close()
            
            # Make multiple backups of the current database file just in case
            if os.path.exists(db_path):
                # Create a timestamped backup
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                temp_backup = f"{db_path}.{timestamp}.bak"
                shutil.copy2(db_path, temp_backup)
                self.stdout.write(f"Created timestamped backup of current database at: {temp_backup}")
                
                # Create a simple .bak file too
                simple_backup = f"{db_path}.bak"
                shutil.copy2(db_path, simple_backup)
                self.stdout.write(f"Created simple backup at: {simple_backup}")
            
            # Copy the backup file to the current database location with multiple retries
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    # Make sure there is adequate space
                    backup_size = os.path.getsize(backup_path)
                    self.stdout.write(f"Backup size: {backup_size} bytes")
                    
                    # First try to make a copy
                    shutil.copy2(backup_path, db_path)
                    
                    # Check if the copy succeeded by comparing file sizes
                    if os.path.exists(db_path):
                        copy_size = os.path.getsize(db_path)
                        if copy_size == backup_size:
                            self.stdout.write(self.style.SUCCESS(f"Database copy successful: {copy_size} bytes"))
                            success = True
                            break
                        else:
                            self.stdout.write(self.style.ERROR(f"Size mismatch after copy! Backup: {backup_size}, Copy: {copy_size} bytes"))
                    else:
                        self.stdout.write(self.style.ERROR("Copy failed - destination file doesn't exist"))
                        
                    # If copy failed, wait a bit and try again
                    self.stdout.write(f"Copy attempt {attempt+1} failed, retrying...")
                    import time
                    time.sleep(2)
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Copy attempt {attempt+1} error: {str(e)}"))
                    if attempt == max_retries - 1:
                        raise
                        
            if success:
                self.stdout.write(self.style.SUCCESS(f"Replaced database with backup from: {backup_path}"))
                
                # Record this restore in environment variables for diagnostic purposes
                os.environ['LAST_RESTORED_BACKUP'] = os.path.basename(backup_path) + " (Deployment Specific)"
                os.environ['LAST_RESTORE_TIME'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Create a log file of the restoration in the deployment directory
                log_path = os.path.join(os.path.dirname(os.path.dirname(backup_path)), "deployment", "restoration_log.txt")
                with open(log_path, 'a') as f:
                    f.write(f"{timezone.now()} - Restored from {os.path.basename(backup_path)}\n")
                
                # Try to set permissions on the new database file
                try:
                    os.chmod(db_path, 0o644)
                    self.stdout.write("Set permissions on new database file")
                except Exception as perm_error:
                    self.stdout.write(f"Warning: Could not set permissions on new database: {str(perm_error)}")
                
                return True
            else:
                raise CommandError(f"Failed to copy database after {max_retries} attempts")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'‼️ CRITICAL ERROR RESTORING FROM SQLITE DEPLOYMENT BACKUP: {str(e)}'))
            # Don't raise here - let the caller handle the failure
    
    def restore_json_backup(self, backup_path):
        """Restore from JSON backup file"""
        # Initialize temp_backup_path at the beginning to avoid unbound variable issues
        temp_backup_path = os.path.join(os.path.dirname(backup_path), "temp_deployment_restore.json")
        
        try:
            self.stdout.write(self.style.SUCCESS(f'STARTING JSON RESTORATION FROM: {backup_path}'))
            self.stdout.write(f'Backup file size: {os.path.getsize(backup_path)} bytes')
            self.stdout.write(f'Backup last modified: {os.path.getmtime(backup_path)}')
            
            # Verify the backup exists and is readable
            if not os.path.exists(backup_path):
                self.stdout.write(self.style.ERROR(f"JSON backup file not found at: {backup_path}"))
                return False
                
            if not os.access(backup_path, os.R_OK):
                self.stdout.write(self.style.WARNING(f"JSON backup file exists but is not readable"))
                # Try to fix permissions
                try:
                    os.chmod(backup_path, 0o644)
                    self.stdout.write(self.style.SUCCESS("Fixed permissions on JSON backup"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to fix permissions: {str(e)}"))
                    return False
            
            # Verify the backup content
            try:
                self.verify_backup(backup_path)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Backup verification failed: {str(e)}"))
                # If verification fails but the file exists, we'll try anyway
                self.stdout.write(self.style.WARNING("Attempting restoration despite verification failure"))
            
            # Create a temporary copy of the backup to modify if needed
            try:
                shutil.copy2(backup_path, temp_backup_path)
                self.stdout.write(self.style.SUCCESS(f"Created temporary copy at {temp_backup_path}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to create temporary copy: {str(e)}"))
                # Try to continue with the original file
                temp_backup_path = backup_path
            
            # Make sure the database connection is working
            try:
                from django.db import connection
                connection.ensure_connection()
                self.stdout.write(self.style.SUCCESS("Database connection is working"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Database connection error: {str(e)}"))
                # Try to reconnect
                try:
                    from django.db import connections
                    connections.close_all()
                    connection.ensure_connection()
                    self.stdout.write(self.style.SUCCESS("Reconnected to database"))
                except Exception as e2:
                    self.stdout.write(self.style.ERROR(f"Failed to reconnect to database: {str(e2)}"))
                    return False
            
            # Clear existing data (but keep structure)
            # We use reset_db instead of flush to avoid integrity errors
            self.stdout.write(self.style.SUCCESS("Clearing existing data..."))
            from django.db import connection
            if connection.vendor == 'sqlite':
                # For SQLite, we use a more aggressive approach
                with connection.cursor() as cursor:
                    try:
                        # Disable foreign key constraints temporarily
                        cursor.execute("PRAGMA foreign_keys = OFF;")
                        
                        # Get list of tables excluding django_migrations
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'django_migrations' AND name != 'sqlite_sequence';")
                        tables = [row[0] for row in cursor.fetchall()]
                        
                        # Clear all tables except migrations
                        for table in tables:
                            try:
                                cursor.execute(f"DELETE FROM {table};")
                                self.stdout.write(f"Cleared table: {table}")
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f"Error clearing table {table}: {str(e)}"))
                                
                        # Re-enable foreign key constraints
                        cursor.execute("PRAGMA foreign_keys = ON;")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error during table clearing: {str(e)}"))
                        # Continue anyway as loaddata might still work
            else:
                # For other databases, use flush
                try:
                    call_command('flush', '--no-input')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error during flush: {str(e)}"))
                    # Continue anyway
            
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