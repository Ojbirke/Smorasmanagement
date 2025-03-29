import os
import sys
import datetime
import subprocess
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils.translation import gettext_lazy as _
from backup_config import (
    load_config, save_config, get_backup_path, 
    set_backup_path, configure_git_backup
)

class Command(BaseCommand):
    help = 'Configure backup locations and settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show-config',
            action='store_true',
            help='Display current backup configuration',
        )
        
        parser.add_argument(
            '--set-backup-path',
            dest='backup_path',
            help='Set the primary backup directory path',
        )
        
        parser.add_argument(
            '--test-backup-dir',
            action='store_true',
            help='Test if the backup directory is writable',
        )
        
        # Git backup configuration
        parser.add_argument(
            '--enable-git',
            action='store_true',
            help='Enable Git repository backup',
        )
        
        parser.add_argument(
            '--disable-git',
            action='store_true',
            help='Disable Git repository backup',
        )
        
        parser.add_argument(
            '--git-repo',
            help='Set Git repository URL for backups',
        )
        
        parser.add_argument(
            '--git-branch',
            help='Set Git repository branch for backups',
        )
        
        parser.add_argument(
            '--git-username',
            help='Set Git username for authentication',
        )
        
        # Location management
        parser.add_argument(
            '--add-location',
            help='Add a secondary backup location (format: name:path)',
        )
        
        parser.add_argument(
            '--remove-location',
            help='Remove a secondary backup location by name',
        )
        
        # PostgreSQL testing
        parser.add_argument(
            '--test-postgres',
            action='store_true',
            help='Test PostgreSQL connection and backup capabilities',
        )

    def handle(self, *args, **options):
        # Show current configuration
        if options['show_config']:
            self.show_configuration()
            return
            
        # Test backup directory
        if options['test_backup_dir']:
            self.test_backup_directory()
            return
        
        # Test PostgreSQL
        if options.get('test_postgres', False):
            self.test_postgres_backup()
            return
            
        # Set backup path
        if options['backup_path']:
            self.set_backup_path(options['backup_path'])
        
        # Add location
        if options.get('add_location'):
            self.add_backup_location(options['add_location'])
            
        # Remove location
        if options.get('remove_location'):
            self.remove_backup_location(options['remove_location'])
            
        # Configure Git backup
        git_options_present = any([
            options['enable_git'], 
            options['disable_git'],
            options['git_repo'],
            options['git_branch'],
            options['git_username']
        ])
        
        if git_options_present:
            enabled = options['enable_git'] if options['enable_git'] else not options['disable_git']
            self.configure_git(
                enabled=enabled,
                repo=options['git_repo'],
                branch=options['git_branch'],
                username=options['git_username']
            )
            
        # If no options were provided, show help
        if not any([
            options['show_config'], 
            options['test_backup_dir'],
            options.get('test_postgres', False),
            options['backup_path'],
            options.get('add_location'),
            options.get('remove_location'),
            git_options_present
        ]):
            self.stdout.write(self.style.WARNING('No options specified. Use --help to see available options.'))
        
    def show_configuration(self):
        """Display current backup configuration"""
        config = load_config()
        
        self.stdout.write(self.style.SUCCESS('=== BACKUP CONFIGURATION ==='))
        
        # Main backup directory
        backup_dir = config.get('backup_directory', 'Not configured')
        self.stdout.write(f'Primary Backup Directory: {backup_dir}')
        
        # Check if directory exists and is writable
        if os.path.exists(backup_dir):
            if os.access(backup_dir, os.W_OK):
                self.stdout.write(self.style.SUCCESS('  ✓ Directory exists and is writable'))
            else:
                self.stdout.write(self.style.ERROR('  ✗ Directory exists but is not writable'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠ Directory does not exist'))
            
        # Secondary backup locations
        self.stdout.write('\nSecondary Backup Locations:')
        secondary_locations = config.get('backup_locations', [])
        for i, location in enumerate(secondary_locations, 1):
            status = '✓ Enabled' if location.get('enabled', True) else '✗ Disabled'
            path = location.get('path', 'Not specified')
            name = location.get('name', f'Location {i}')
            max_backups = location.get('max_backups', 'Not specified')
            
            self.stdout.write(f'  {name}: {path} [{status}, Max backups: {max_backups}]')
            
        # Git backup configuration
        self.stdout.write('\nGit Backup Repository:')
        git_config = config.get('git_backup', {})
        if git_config.get('enabled', False):
            repo = git_config.get('repository', 'Not specified')
            branch = git_config.get('branch', 'main')
            username = git_config.get('username', 'Not specified')
            
            self.stdout.write(self.style.SUCCESS('  ✓ Git backup is enabled'))
            self.stdout.write(f'  Repository: {repo}')
            self.stdout.write(f'  Branch: {branch}')
            self.stdout.write(f'  Username: {username}')
            
            # Check if GITHUB_TOKEN is set
            if 'GITHUB_TOKEN' in os.environ:
                self.stdout.write(self.style.SUCCESS('  ✓ GitHub token is available in environment'))
            else:
                self.stdout.write(self.style.WARNING('  ⚠ No GitHub token found in environment - set GITHUB_TOKEN if needed'))
        else:
            self.stdout.write(self.style.WARNING('  ✗ Git backup is disabled'))
            
    def test_backup_directory(self):
        """Test if the backup directory is writable"""
        backup_dir = get_backup_path()
        
        self.stdout.write(f'Testing backup directory: {backup_dir}')
        
        # Check if directory exists
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created backup directory: {backup_dir}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to create backup directory: {e}'))
                return
                
        # Check if directory is writable by creating a test file
        test_file = os.path.join(backup_dir, 'test_write.txt')
        try:
            with open(test_file, 'w') as f:
                f.write('Test backup system write access')
            
            self.stdout.write(self.style.SUCCESS('  ✓ Successfully wrote test file'))
            
            # Clean up test file
            os.remove(test_file)
            self.stdout.write(self.style.SUCCESS('  ✓ Successfully removed test file'))
            
            self.stdout.write(self.style.SUCCESS('  ✓ Backup directory is writable'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Failed to write to backup directory: {e}'))
            
    def set_backup_path(self, path):
        """Set the primary backup path"""
        # Convert to absolute path if relative
        if not os.path.isabs(path):
            base_dir = Path(os.getcwd())
            abs_path = os.path.abspath(os.path.join(base_dir, path))
            self.stdout.write(f'Converting relative path to absolute: {abs_path}')
            path = abs_path
            
        # Try to create the directory if it doesn't exist
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f'Created backup directory: {path}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to create backup directory: {e}'))
                return
                
        # Check if directory is writable
        if not os.access(path, os.W_OK):
            self.stdout.write(self.style.ERROR(f'Directory is not writable: {path}'))
            return
            
        # Save the configuration
        if set_backup_path(path):
            self.stdout.write(self.style.SUCCESS(f'Backup path set to: {path}'))
        else:
            self.stdout.write(self.style.ERROR('Failed to save backup configuration'))
            
    def configure_git(self, enabled=True, repo=None, branch=None, username=None):
        """Configure Git backup settings"""
        if configure_git_backup(enabled, repo, branch, username):
            status = 'enabled' if enabled else 'disabled'
            self.stdout.write(self.style.SUCCESS(f'Git backup {status} successfully'))
            
            # Show updated settings
            if enabled:
                config = load_config()
                git_config = config.get('git_backup', {})
                self.stdout.write(f'  Repository: {git_config.get("repository", "Not specified")}')
                self.stdout.write(f'  Branch: {git_config.get("branch", "main")}')
                self.stdout.write(f'  Username: {git_config.get("username", "Not specified")}')
        else:
            self.stdout.write(self.style.ERROR('Failed to save Git backup configuration'))
            
    def add_backup_location(self, location_spec):
        """Add a secondary backup location"""
        # Parse location spec (name:path)
        parts = location_spec.split(':', 1)
        if len(parts) != 2:
            self.stdout.write(self.style.ERROR(
                'Invalid location format. Use "name:path"'
            ))
            return False
            
        name, path = parts
        config = load_config()
        
        # Initialize backup_locations if not present
        if 'backup_locations' not in config:
            config['backup_locations'] = []
            
        # Check if location already exists
        for location in config['backup_locations']:
            if location.get('name') == name:
                self.stdout.write(self.style.WARNING(
                    f'Location "{name}" already exists, updating configuration'
                ))
                location['path'] = path
                location['enabled'] = True
                save_config(config)
                return True
                
        # Add new location
        config['backup_locations'].append({
            'name': name,
            'path': path,
            'enabled': True,
            'max_backups': 5
        })
        
        save_config(config)
        self.stdout.write(self.style.SUCCESS(
            f'Added backup location "{name}" with path "{path}"'
        ))
        return True
        
    def remove_backup_location(self, name):
        """Remove a secondary backup location"""
        config = load_config()
        
        if 'backup_locations' not in config or not config['backup_locations']:
            self.stdout.write(self.style.WARNING('No backup locations configured'))
            return False
            
        # Find location by name
        for i, location in enumerate(config['backup_locations']):
            if location.get('name') == name:
                # Remove it
                del config['backup_locations'][i]
                save_config(config)
                self.stdout.write(self.style.SUCCESS(
                    f'Removed backup location "{name}"'
                ))
                return True
                
        # Not found
        self.stdout.write(self.style.ERROR(
            f'No backup location found with name "{name}"'
        ))
        return False
        
    def test_postgres_backup(self):
        """Test PostgreSQL connection and backup capabilities"""
        from django.conf import settings
        import os
        import datetime
        import subprocess
        
        self.stdout.write(self.style.SUCCESS('=== POSTGRESQL BACKUP TEST ==='))
        
        # Check if PostgreSQL is configured
        db_settings = settings.DATABASES.get('default', {})
        db_engine = db_settings.get('ENGINE', '')
        
        if 'postgresql' not in db_engine:
            self.stdout.write(self.style.ERROR(
                f'PostgreSQL is not configured. Current engine: {db_engine}'
            ))
            return False
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ PostgreSQL is configured: {db_engine}'))
        
        # Check DATABASE_URL environment variable
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            self.stdout.write(self.style.WARNING(
                'DATABASE_URL environment variable is not set. '
                'This may affect pg_dump backup capabilities.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('✓ DATABASE_URL environment variable is set'))
        
        # Check if DATABASE environment variables are set
        pg_env_vars = ['PGDATABASE', 'PGUSER', 'PGPASSWORD', 'PGHOST', 'PGPORT']
        pg_env_set = all(var in os.environ for var in pg_env_vars)
        
        if pg_env_set:
            self.stdout.write(self.style.SUCCESS('✓ All PostgreSQL environment variables are set'))
        else:
            missing = [var for var in pg_env_vars if var not in os.environ]
            self.stdout.write(self.style.WARNING(
                f'Some PostgreSQL environment variables are missing: {", ".join(missing)}'
            ))
        
        # Try to connect to database
        try:
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute('SELECT version();')
            version = cursor.fetchone()[0]
            cursor.close()
            
            self.stdout.write(self.style.SUCCESS(f'✓ Connected to PostgreSQL: {version}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Failed to connect to PostgreSQL: {e}'))
            return False
        
        # Check for pg_dump
        try:
            pg_dump_result = subprocess.run(['pg_dump', '--version'], 
                                          capture_output=True, text=True)
            
            if pg_dump_result.returncode == 0:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ pg_dump is available: {pg_dump_result.stdout.strip()}'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'✗ pg_dump returned an error: {pg_dump_result.stderr}'
                ))
        except (subprocess.SubprocessError, FileNotFoundError):
            self.stdout.write(self.style.WARNING(
                '✗ pg_dump is not available. SQL backups will not be created.'
            ))
        
        # Create a test backup file
        self.stdout.write('\nCreating test backup file:')
        
        try:
            # Use django dumpdata for a JSON backup
            backup_dir = get_backup_path()
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            test_file = os.path.join(backup_dir, f'test_backup_{timestamp}.json')
            
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(test_file), exist_ok=True)
            
            # Create backup
            from django.core.management import call_command
            call_command('dumpdata', 
                       '--exclude=contenttypes', 
                       '--exclude=auth.permission',
                       '--indent=2', 
                       output=test_file)
            
            if os.path.exists(test_file):
                file_size = os.path.getsize(test_file)
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Test backup created successfully: {test_file} ({file_size} bytes)'
                ))
                
                # Cleanup
                os.remove(test_file)
                self.stdout.write(self.style.SUCCESS(f'✓ Test backup deleted after verification'))
            else:
                self.stdout.write(self.style.ERROR('✗ Failed to create test backup'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error during test backup creation: {e}'))
            return False
        
        self.stdout.write(self.style.SUCCESS('\n✓ PostgreSQL backup test completed successfully'))