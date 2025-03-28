import os
import shutil
import subprocess
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

class Command(BaseCommand):
    help = 'Synchronizes backups with Git repository to persist across deployments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--push',
            action='store_true',
            help='Push backups to repository',
        )
        
        parser.add_argument(
            '--pull',
            action='store_true',
            help='Pull backups from repository',
        )
        
        parser.add_argument(
            '--safe',
            action='store_true',
            help='Do not overwrite existing backups when pulling',
        )

    def handle(self, *args, **options):
        # Define directories
        repo_root = Path(settings.BASE_DIR).parent
        deployment_dir = repo_root / 'deployment'
        os.makedirs(deployment_dir, exist_ok=True)
        
        # Create .gitkeep in deployment directory to ensure it's tracked
        gitkeep_path = deployment_dir / '.gitkeep'
        if not gitkeep_path.exists():
            with open(gitkeep_path, 'w') as f:
                f.write('# This file ensures the deployment directory is tracked in Git\n')
        
        # Ensure git is configured
        self._configure_git()
        
        # Perform the requested operation
        if options['push']:
            self.push_backups(deployment_dir)
        elif options['pull']:
            self.pull_backups(deployment_dir, options['safe'])
        else:
            self.stdout.write(self.style.WARNING('No operation specified. Use --push or --pull'))
    
    def _configure_git(self):
        """Configure git user if not already configured"""
        try:
            # Check if git user is configured
            name_result = subprocess.run(['git', 'config', 'user.name'], 
                                       capture_output=True, text=True)
            
            if not name_result.stdout.strip():
                # Set default git user
                self.stdout.write("Configuring git user...")
                subprocess.run(['git', 'config', 'user.name', 'Deployment Bot'])
                subprocess.run(['git', 'config', 'user.email', 'deployment@example.com'])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error configuring git: {str(e)}"))
            
    def push_backups(self, deployment_dir):
        """Push backups to git repository"""
        self.stdout.write(self.style.SUCCESS('Pushing backups to repository...'))
        
        # Mark deployment files for git tracking
        sqlite_path = deployment_dir / 'deployment_db.sqlite'
        json_path = deployment_dir / 'deployment_db.json'
        backups_dir = deployment_dir / 'backups'
        
        # Check if we have backup files to sync
        sync_files = []
        if sqlite_path.exists():
            sync_files.append(sqlite_path)
        
        if json_path.exists():
            sync_files.append(json_path)
            
        # Add any other important files in the deployment directory
        sync_files.extend(deployment_dir.glob('IS_PRODUCTION_ENVIRONMENT'))
        
        # Add backup directory files if they exist
        if backups_dir.exists():
            for backup_file in backups_dir.glob('*.sqlite'):
                sync_files.append(backup_file)
            for backup_file in backups_dir.glob('*.json'):
                sync_files.append(backup_file)
        
        if not sync_files:
            self.stdout.write(self.style.WARNING('No backup files found to sync'))
            return
            
        try:
            # Add files to git
            self.stdout.write(f"Adding {len(sync_files)} files to git...")
            for file_path in sync_files:
                # Use relative paths for git commands
                rel_path = file_path.relative_to(Path(settings.BASE_DIR).parent)
                subprocess.run(['git', 'add', str(rel_path)])
                self.stdout.write(f"Added: {rel_path}")
            
            # Commit changes
            commit_message = f"Auto-sync deployment backups - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(['git', 'commit', '-m', commit_message])
            
            # Push changes
            subprocess.run(['git', 'push', 'origin', 'main'])
            
            self.stdout.write(self.style.SUCCESS('Successfully pushed backups to repository'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error pushing backups: {str(e)}'))
            raise CommandError(f'Failed to push backups: {str(e)}')
    
    def pull_backups(self, deployment_dir, safe=False):
        """Pull backups from git repository"""
        self.stdout.write(self.style.SUCCESS('Pulling backups from repository...'))
        
        try:
            # First, let's pull the latest from the repository
            self.stdout.write("Pulling latest changes from repository...")
            subprocess.run(['git', 'pull', 'origin', 'main'])
            
            # Check if we got the deployment files
            sqlite_path = deployment_dir / 'deployment_db.sqlite'
            json_path = deployment_dir / 'deployment_db.json'
            backups_dir = deployment_dir / 'backups'
            
            # Now we should have the latest backups
            if sqlite_path.exists():
                file_size = sqlite_path.stat().st_size
                if file_size > 1000:  # Basic size check
                    self.stdout.write(self.style.SUCCESS(
                        f'Found SQLite deployment backup: {sqlite_path}, Size: {file_size} bytes'))
                    
                    # Make sure the file is readable
                    if not os.access(sqlite_path, os.R_OK):
                        os.chmod(sqlite_path, 0o644)
                else:
                    self.stdout.write(self.style.WARNING(
                        f'SQLite backup seems too small ({file_size} bytes), might be corrupted'))
            else:
                self.stdout.write(self.style.WARNING('No SQLite deployment backup found'))
                
            if json_path.exists():
                file_size = json_path.stat().st_size
                if file_size > 10:  # Basic size check
                    self.stdout.write(self.style.SUCCESS(
                        f'Found JSON deployment backup: {json_path}, Size: {file_size} bytes'))
                    
                    # Make sure the file is readable
                    if not os.access(json_path, os.R_OK):
                        os.chmod(json_path, 0o644)
                else:
                    self.stdout.write(self.style.WARNING(
                        f'JSON backup seems too small ({file_size} bytes), might be corrupted'))
            else:
                self.stdout.write(self.style.WARNING('No JSON deployment backup found'))
            
            # Check for backup directory
            if backups_dir.exists():
                backup_count = len(list(backups_dir.glob('*.sqlite'))) + len(list(backups_dir.glob('*.json')))
                self.stdout.write(self.style.SUCCESS(f'Found {backup_count} additional backups in backup directory'))
            
            self.stdout.write(self.style.SUCCESS('Successfully pulled backups from repository'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error pulling backups: {str(e)}'))
            raise CommandError(f'Failed to pull backups: {str(e)}')