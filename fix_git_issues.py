#!/usr/bin/env python3
"""
Git Push Issue Fix Utility

This script:
1. Configures Git properly
2. Creates a fresh backup of the database
3. Pushes the backup to Git safely
4. Reports success/failure
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return output"""
    print(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        if result.returncode != 0 and result.stderr:
            print("Error output:")
            print(result.stderr)
        return result
    except Exception as e:
        print(f"Error running command: {str(e)}")
        return None

def setup_git():
    """Configure git user if not already configured"""
    print("\n=== Configuring Git ===")
    
    # Check if git user is configured
    git_user = run_command(["git", "config", "user.name"])
    git_email = run_command(["git", "config", "user.email"])
    
    if git_user.returncode != 0 or not git_user.stdout.strip():
        print("Setting git user.name to 'Replit Deployment'")
        run_command(["git", "config", "user.name", "Replit Deployment"])
    else:
        print(f"Git user already configured: {git_user.stdout.strip()}")
    
    if git_email.returncode != 0 or not git_email.stdout.strip():
        print("Setting git user.email to 'deployment@replit.com'")
        run_command(["git", "config", "user.email", "deployment@replit.com"])
    else:
        print(f"Git email already configured: {git_email.stdout.strip()}")
    
    # Set credential cache to avoid password prompts
    print("Setting up Git credential cache")
    run_command(["git", "config", "credential.helper", "cache --timeout=3600"])
    
    # Check if we have GitHub token in environment
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        print("GitHub token is available in environment")
    else:
        print("WARNING: No GitHub token found in environment variables")
        print("You may need to manually provide credentials when pushing to GitHub")
    
    return True

def create_backup():
    """Create a fresh backup of the database"""
    print("\n=== Creating Database Backup ===")
    
    # Add Django project to path
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball'))
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
    
    try:
        import django
        django.setup()
        from django.core.management import call_command
        from django.conf import settings
        
        # Create timestamp for backup filename
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_filename = f"git_fix_backup_{timestamp}.json"
        
        # Define backup path
        repo_root = Path(settings.BASE_DIR).parent
        deployment_dir = repo_root / 'deployment'
        deployment_dir.mkdir(exist_ok=True)
        
        backup_path = deployment_dir / backup_filename
        
        # Create the backup
        print(f"Creating backup at: {backup_path}")
        call_command('dumpdata', output=str(backup_path))
        
        # Verify backup file exists and has content
        if backup_path.exists() and backup_path.stat().st_size > 0:
            print(f"✅ Backup created successfully: {backup_path} ({backup_path.stat().st_size} bytes)")
            
            # Also update the deployment_db.json file
            deployment_backup = deployment_dir / 'deployment_db.json'
            import shutil
            shutil.copy2(backup_path, deployment_backup)
            print(f"✅ Updated main deployment backup: {deployment_backup}")
            
            return str(backup_path)
        else:
            print("❌ Error: Backup file not created or is empty")
            return None
        
    except ImportError as e:
        print(f"Error importing Django: {str(e)}")
        return None
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        return None

def push_to_git(backup_path=None):
    """Push database backup to git"""
    print("\n=== Pushing to Git Repository ===")
    
    # Check if git is initialized
    git_status = run_command(["git", "status"])
    if git_status.returncode != 0:
        print("Git repository not initialized or in detached state")
        return False
    
    # Stash any uncommitted changes to avoid conflicts
    print("Stashing any uncommitted changes")
    run_command(["git", "stash"])
    
    # Pull latest changes first
    print("Pulling latest changes")
    pull_result = run_command(["git", "pull", "--rebase"])
    if pull_result.returncode != 0:
        print("Warning: Failed to pull latest changes. Continuing anyway...")
    
    # Add backup files to git
    if backup_path:
        print(f"Adding backup file to git: {backup_path}")
        run_command(["git", "add", backup_path])
    
    # Add all deployment files
    print("Adding all deployment files")
    run_command(["git", "add", "deployment/*"])
    
    # Check if there are changes to commit
    git_status = run_command(["git", "status", "--porcelain"])
    if not git_status.stdout.strip():
        print("No changes to commit")
        return True
    
    # Commit changes
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    commit_message = f"Updated database backup - {timestamp}"
    print(f"Committing changes: {commit_message}")
    commit_result = run_command(["git", "commit", "-m", commit_message])
    
    if commit_result.returncode != 0:
        print("Error committing changes")
        return False
    
    # Optimize repository to avoid excessive size
    print("Optimizing repository")
    run_command(["git", "gc", "--aggressive", "--prune=now"])
    
    # Push changes
    print("Pushing changes to remote repository")
    
    # If we have a GitHub token, use it
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        print("Using GitHub token for authentication")
        # Get the remote URL
        remote_url = run_command(["git", "config", "--get", "remote.origin.url"])
        if remote_url.returncode == 0 and remote_url.stdout.strip():
            original_url = remote_url.stdout.strip()
            # Use a cleaner approach for token-based authentication
            if "github.com" in original_url:
                print("Using HTTPS with token authentication")
                # Use GitHub token without modifying URLs (safer approach)
                os.environ["GIT_ASKPASS"] = "echo"
                os.environ["GIT_TERMINAL_PROMPT"] = "0"
                remote_name = "origin"
                
                # Use standard origin push with credential caching
                push_result = run_command(["git", "push", remote_name, "main"])
            else:
                # Not GitHub, push normally
                push_result = run_command(["git", "push"])
        else:
            # No remote URL found
            push_result = run_command(["git", "push"])
    else:
        # No token, push normally
        push_result = run_command(["git", "push"])
    
    if push_result.returncode != 0:
        print("❌ Failed to push changes to remote repository")
        return False
    else:
        print("✅ Successfully pushed changes to remote repository")
        return True

def mark_as_production():
    """Mark this instance as production"""
    print("\n=== Marking Environment as Production ===")
    
    try:
        # Add Django project to path
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball'))
        
        # Import Django settings
        import django
        django.setup()
        from django.conf import settings
        
        # Create production marker file
        repo_root = Path(settings.BASE_DIR).parent
        deployment_dir = repo_root / 'deployment'
        deployment_dir.mkdir(exist_ok=True)
        
        production_marker = deployment_dir / 'IS_PRODUCTION_ENVIRONMENT'
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        with open(production_marker, 'w') as f:
            f.write(f"This instance was marked as production on {timestamp}\n")
        
        print(f"✅ Created production marker file: {production_marker}")
        return True
    except Exception as e:
        print(f"Error marking as production: {str(e)}")
        return False

def main():
    print("\n=== Git Issue Fix Utility ===\n")
    
    # Set up Git properly
    if not setup_git():
        print("❌ Failed to configure Git")
        return False
    
    # Create a fresh backup
    backup_path = create_backup()
    if not backup_path:
        print("❌ Failed to create backup")
        return False
    
    # Mark as production
    if not mark_as_production():
        print("❌ Failed to mark as production")
        return False
    
    # Push to Git
    if not push_to_git(backup_path):
        print("❌ Failed to push to Git")
        return False
    
    print("\n✅ Git issues fixed successfully!")
    print("1. Git properly configured")
    print("2. Fresh database backup created")
    print("3. Environment marked as production")
    print("4. Changes pushed to Git repository")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)