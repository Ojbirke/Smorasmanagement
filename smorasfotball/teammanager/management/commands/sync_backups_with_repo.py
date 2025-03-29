import os
import shutil
import subprocess
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from backup_config import get_backup_path, get_backup_git_repo

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
        
        parser.add_argument(
            '--use-main-repo',
            action='store_true',
            help='Use main code repository instead of separate backup repo',
        )
        
        parser.add_argument(
            '--backup-repo',
            help='Specify custom backup repository URL',
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
        
        # Check if user wants to use a dedicated backup repository
        self.use_backup_repo = False
        self.backup_repo_url = None
        self.backup_branch = 'main'
        
        # Load backup repo settings from config
        git_config = get_backup_git_repo()
        if git_config and git_config.get('enabled', False) and not options['use_main_repo']:
            self.use_backup_repo = True
            self.backup_repo_url = options['backup_repo'] or git_config.get('repository')
            self.backup_branch = git_config.get('branch', 'main')
            
            if not self.backup_repo_url:
                self.stdout.write(self.style.ERROR('No backup repository URL configured. Using main repository.'))
                self.use_backup_repo = False
            else:
                self.stdout.write(self.style.SUCCESS(f'Using dedicated backup repository: {self.backup_repo_url}'))
        
        # Ensure git is configured
        self._configure_git()
        
        # Get external backup path
        self.external_backup_dir = get_backup_path()
        self.stdout.write(f"Using external backup directory: {self.external_backup_dir}")
        
        # Perform the requested operation
        if options['push']:
            if self.use_backup_repo:
                self.push_to_backup_repo(deployment_dir)
            else:
                self.push_backups(deployment_dir)
        elif options['pull']:
            if self.use_backup_repo:
                self.pull_from_backup_repo(deployment_dir, options['safe'])
            else:
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
        """Push backups to main git repository"""
        self.stdout.write(self.style.SUCCESS('Pushing backups to main repository...'))
        
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
        """Pull backups from main git repository"""
        self.stdout.write(self.style.SUCCESS('Pulling backups from main repository...'))
        
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
    
    def push_to_backup_repo(self, deployment_dir):
        """Push backups to a dedicated backup repository"""
        self.stdout.write(self.style.SUCCESS(f'Pushing backups to dedicated repository: {self.backup_repo_url}'))
        
        # Create a local clone of the backup repository if needed
        backup_clone_dir = os.path.join(self.external_backup_dir, 'backup_repo')
        
        try:
            # Ensure backup dir exists
            os.makedirs(self.external_backup_dir, exist_ok=True)
            
            # Check if we already have the backup repo cloned
            if not os.path.exists(backup_clone_dir):
                self.stdout.write(f"Cloning backup repository to {backup_clone_dir}...")
                
                # Clone the repository
                clone_cmd = [
                    'git', 'clone', 
                    self.backup_repo_url, 
                    backup_clone_dir
                ]
                
                result = subprocess.run(clone_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.stdout.write(self.style.ERROR(f"Failed to clone backup repository: {result.stderr}"))
                    raise CommandError("Failed to clone backup repository")
            else:
                # Repository already exists, just pull latest changes
                self.stdout.write("Updating existing backup repository clone...")
                pull_cmd = ['git', 'pull', 'origin', self.backup_branch]
                
                # Run git command in the backup repo directory
                result = subprocess.run(pull_cmd, cwd=backup_clone_dir, capture_output=True, text=True)
                if result.returncode != 0:
                    self.stdout.write(self.style.WARNING(f"Failed to pull latest backup repo changes: {result.stderr}"))
                    # Continue anyway as we'll overwrite with new backups
            
            # Collect backup files to copy
            backup_files = []
            
            # Latest deployment backups
            deployment_sqlite = os.path.join(deployment_dir, 'deployment_db.sqlite')
            deployment_json = os.path.join(deployment_dir, 'deployment_db.json')
            
            if os.path.exists(deployment_sqlite):
                backup_files.append(deployment_sqlite)
            
            if os.path.exists(deployment_json):
                backup_files.append(deployment_json)
            
            # PostgreSQL backups from external backup dir
            for filename in os.listdir(self.external_backup_dir):
                if filename.startswith('backup_postgres_') and (filename.endswith('.json') or filename.endswith('.sql')):
                    backup_files.append(os.path.join(self.external_backup_dir, filename))
            
            # Copy to the backup repo directory
            self.stdout.write(f"Copying {len(backup_files)} backup files to repository...")
            
            # Ensure the backups directory exists in the repo
            backups_dir = os.path.join(backup_clone_dir, 'backups')
            os.makedirs(backups_dir, exist_ok=True)
            
            # Copy files
            for backup_file in backup_files:
                filename = os.path.basename(backup_file)
                dest_path = os.path.join(backups_dir, filename)
                shutil.copy2(backup_file, dest_path)
                self.stdout.write(f"Copied {filename} to backup repository")
            
            # Commit and push changes
            self.stdout.write("Committing and pushing backup files...")
            
            # Add all files
            add_cmd = ['git', 'add', '-A']
            subprocess.run(add_cmd, cwd=backup_clone_dir)
            
            # Commit
            commit_message = f"Auto-sync database backups - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            commit_cmd = ['git', 'commit', '-m', commit_message]
            commit_result = subprocess.run(commit_cmd, cwd=backup_clone_dir, capture_output=True, text=True)
            
            if "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
                self.stdout.write(self.style.SUCCESS("No changes to commit in backup repository"))
                return
            
            # Push
            push_cmd = ['git', 'push', 'origin', self.backup_branch]
            push_result = subprocess.run(push_cmd, cwd=backup_clone_dir, capture_output=True, text=True)
            
            if push_result.returncode != 0:
                self.stdout.write(self.style.ERROR(f"Failed to push to backup repository: {push_result.stderr}"))
                raise CommandError("Failed to push to backup repository")
            
            self.stdout.write(self.style.SUCCESS('Successfully pushed backups to dedicated repository'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error pushing to backup repository: {str(e)}'))
            raise CommandError(f'Failed to push to backup repository: {str(e)}')
    
    def pull_from_backup_repo(self, deployment_dir, safe=False):
        """Pull backups from dedicated backup repository"""
        self.stdout.write(self.style.SUCCESS(f'Pulling backups from dedicated repository: {self.backup_repo_url}'))
        
        # Path to local clone of backup repository
        backup_clone_dir = os.path.join(self.external_backup_dir, 'backup_repo')
        
        try:
            # Check if backup repo is already cloned
            if not os.path.exists(backup_clone_dir):
                self.stdout.write(f"Cloning backup repository to {backup_clone_dir}...")
                
                # Clone the repository
                clone_cmd = [
                    'git', 'clone', 
                    self.backup_repo_url, 
                    backup_clone_dir
                ]
                
                result = subprocess.run(clone_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.stdout.write(self.style.ERROR(f"Failed to clone backup repository: {result.stderr}"))
                    raise CommandError("Failed to clone backup repository")
            else:
                # Pull latest changes
                self.stdout.write("Pulling latest changes from backup repository...")
                pull_cmd = ['git', 'pull', 'origin', self.backup_branch]
                
                result = subprocess.run(pull_cmd, cwd=backup_clone_dir, capture_output=True, text=True)
                if result.returncode != 0:
                    self.stdout.write(self.style.ERROR(f"Failed to pull from backup repository: {result.stderr}"))
                    raise CommandError("Failed to pull from backup repository")
            
            # Check if backups exist in the repository
            backups_dir = os.path.join(backup_clone_dir, 'backups')
            if not os.path.exists(backups_dir):
                self.stdout.write(self.style.WARNING("No backups directory found in backup repository"))
                return
            
            # Find the most recent backups
            latest_json = None
            latest_sql = None
            latest_sqlite = None
            
            for filename in os.listdir(backups_dir):
                file_path = os.path.join(backups_dir, filename)
                
                if filename.endswith('.json') and (not latest_json or os.path.getmtime(file_path) > os.path.getmtime(latest_json)):
                    latest_json = file_path
                    
                if filename.endswith('.sql') and (not latest_sql or os.path.getmtime(file_path) > os.path.getmtime(latest_sql)):
                    latest_sql = file_path
                    
                if filename.endswith('.sqlite') and (not latest_sqlite or os.path.getmtime(file_path) > os.path.getmtime(latest_sqlite)):
                    latest_sqlite = file_path
            
            # Copy backups to appropriate locations
            if latest_json:
                self.stdout.write(f"Found latest JSON backup: {os.path.basename(latest_json)}")
                
                # Copy to deployment directory
                dest_path = os.path.join(deployment_dir, 'deployment_db.json')
                if not safe or not os.path.exists(dest_path):
                    shutil.copy2(latest_json, dest_path)
                    self.stdout.write(f"Copied to deployment directory: {dest_path}")
                
                # Copy to external backup directory
                dest_path = os.path.join(self.external_backup_dir, os.path.basename(latest_json))
                if not os.path.exists(dest_path):
                    shutil.copy2(latest_json, dest_path)
                    self.stdout.write(f"Copied to external backup directory: {dest_path}")
            else:
                self.stdout.write(self.style.WARNING("No JSON backups found in repository"))
            
            if latest_sql:
                self.stdout.write(f"Found latest SQL backup: {os.path.basename(latest_sql)}")
                
                # Copy to external backup directory
                dest_path = os.path.join(self.external_backup_dir, os.path.basename(latest_sql))
                if not os.path.exists(dest_path):
                    shutil.copy2(latest_sql, dest_path)
                    self.stdout.write(f"Copied to external backup directory: {dest_path}")
            
            if latest_sqlite:
                self.stdout.write(f"Found latest SQLite backup: {os.path.basename(latest_sqlite)}")
                
                # Copy to deployment directory
                dest_path = os.path.join(deployment_dir, 'deployment_db.sqlite')
                if not safe or not os.path.exists(dest_path):
                    shutil.copy2(latest_sqlite, dest_path)
                    self.stdout.write(f"Copied to deployment directory: {dest_path}")
            
            self.stdout.write(self.style.SUCCESS('Successfully pulled backups from dedicated repository'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error pulling from backup repository: {str(e)}'))
            raise CommandError(f'Failed to pull from backup repository: {str(e)}')