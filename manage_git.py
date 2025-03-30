#!/usr/bin/env python3
"""
Git Management Utility for Smørås Fotball

This script provides a comprehensive interface for managing Git operations
in the Smørås Fotball project, including:

1. Checking repository status
2. Creating database backups
3. Pushing changes to the remote repository
4. Pulling the latest changes from the remote repository
5. Setting up Git configuration
6. Handling credential management securely

Usage:
    python manage_git.py [command]

Commands:
    status      - Show current Git repository status
    backup      - Create a database backup and stage it for commit
    push        - Push local changes to the remote repository
    pull        - Pull changes from the remote repository
    setup       - Configure Git user and credentials
    all         - Run backup, push, and pull operations in sequence
    
If no command is provided, the script will show available commands and current status.
"""

import os
import sys
import time
import subprocess
import json
import argparse
from pathlib import Path

def run_command(command, cwd=None, verbose=True):
    """Run a shell command and return output"""
    if verbose:
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
        
        if verbose:
            print(f"Return code: {result.returncode}")
            if result.stdout and verbose:
                print("Output:")
                print(result.stdout)
            if result.returncode != 0 and result.stderr and verbose:
                print("Error output:")
                print(result.stderr)
                
        return result
    except Exception as e:
        if verbose:
            print(f"Error running command: {str(e)}")
        return None

def setup_django():
    """Set up Django environment"""
    # Add Django project to path
    BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball')
    sys.path.append(BASE_DIR)
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
    
    try:
        import django
        django.setup()
        from django.core.management import call_command
        from django.conf import settings
        return True, settings
    except ImportError as e:
        print(f"Error: Django could not be imported. {str(e)}")
        return False, None

def setup_git():
    """Configure git user if not already configured"""
    print("\n=== Configuring Git ===")
    
    # Check if git user is configured
    git_user = run_command(["git", "config", "user.name"])
    git_email = run_command(["git", "config", "user.email"])
    
    if git_user.returncode != 0 or not git_user.stdout.strip():
        print("Setting git user.name to 'Smørås Fotball Deployment'")
        run_command(["git", "config", "user.name", "Smørås Fotball Deployment"])
    else:
        print(f"Git user already configured: {git_user.stdout.strip()}")
    
    if git_email.returncode != 0 or not git_email.stdout.strip():
        print("Setting git user.email to 'deployment@example.com'")
        run_command(["git", "config", "user.email", "deployment@example.com"])
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

def get_git_status():
    """Get the current Git repository status"""
    print("\n=== Git Repository Status ===")
    
    # Check if git is initialized
    git_status = run_command(["git", "status"])
    if git_status.returncode != 0:
        print("Git repository not initialized or in detached state")
        return False
    
    # Get current branch
    git_branch = run_command(["git", "branch", "--show-current"])
    current_branch = git_branch.stdout.strip() if git_branch.returncode == 0 else "unknown"
    print(f"Current branch: {current_branch}")
    
    # Check for unpushed commits
    unpushed = run_command(["git", "log", "@{u}..", "--oneline"], verbose=False)
    if unpushed.returncode == 0 and unpushed.stdout.strip():
        commit_count = len(unpushed.stdout.strip().split('\n'))
        print(f"You have {commit_count} unpushed commit(s):")
        print(unpushed.stdout)
    elif unpushed.returncode == 0:
        print("All commits are pushed to the remote repository")
    
    # Check for unstaged changes
    unstaged = run_command(["git", "diff", "--name-status"], verbose=False)
    if unstaged.returncode == 0 and unstaged.stdout.strip():
        file_count = len(unstaged.stdout.strip().split('\n'))
        print(f"You have {file_count} unstaged changed file(s)")
    
    # Check for staged changes
    staged = run_command(["git", "diff", "--staged", "--name-status"], verbose=False)
    if staged.returncode == 0 and staged.stdout.strip():
        file_count = len(staged.stdout.strip().split('\n'))
        print(f"You have {file_count} staged changed file(s)")
    
    # Check for untracked files
    untracked = run_command(["git", "ls-files", "--others", "--exclude-standard"], verbose=False)
    if untracked.returncode == 0 and untracked.stdout.strip():
        file_count = len(untracked.stdout.strip().split('\n'))
        print(f"You have {file_count} untracked file(s)")
    
    return True

def create_backup():
    """Create a backup of the database"""
    print("\n=== Creating Database Backup ===")
    
    # Set up Django
    success, settings = setup_django()
    if not success:
        return None
    
    try:
        from django.core.management import call_command
        
        # Create timestamp for backup filename
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_filename = f"git_backup_{timestamp}.json"
        
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
            
            # Stage both files for commit
            run_command(["git", "add", str(backup_path)])
            run_command(["git", "add", str(deployment_backup)])
            
            print("✅ Backup files staged for commit")
            
            return str(backup_path)
        else:
            print("❌ Error: Backup file not created or is empty")
            return None
        
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        return None

def commit_changes(message=None):
    """Commit staged changes to the repository"""
    print("\n=== Committing Changes ===")
    
    # Check if there are staged changes to commit
    git_status = run_command(["git", "status", "--porcelain"])
    
    if not git_status.stdout.strip():
        print("No changes to commit")
        return True
    
    # Commit changes
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    if not message:
        message = f"Database backup update - {timestamp}"
        
    print(f"Committing changes: {message}")
    commit_result = run_command(["git", "commit", "-m", message])
    
    if commit_result.returncode != 0:
        print("❌ Error committing changes")
        return False
    
    print("✅ Changes committed successfully")
    return True

def push_to_git():
    """Push changes to the remote repository"""
    print("\n=== Pushing to Remote Repository ===")
    
    # Check if there are commits to push
    unpushed = run_command(["git", "log", "@{u}..", "--oneline"], verbose=False)
    if unpushed.returncode != 0:
        print("❌ Error checking for unpushed commits")
        return False
    
    if not unpushed.stdout.strip():
        print("No commits to push")
        return True
    
    # Pull with rebase before pushing to avoid conflicts
    print("Pulling latest changes with rebase")
    pull_result = run_command(["git", "pull", "--rebase"])
    if pull_result.returncode != 0:
        print("⚠️ Warning: Failed to pull latest changes, attempting push anyway...")
    
    # Push changes
    print("Pushing changes to remote repository")
    
    # If we have a GitHub token, use it
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        print("Using GitHub token for authentication")
        # Configure environment for token authentication
        os.environ["GIT_ASKPASS"] = "echo"
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
    
    # Perform the push
    push_result = run_command(["git", "push"])
    
    if push_result.returncode != 0:
        print("❌ Failed to push changes to remote repository")
        return False
    else:
        print("✅ Successfully pushed changes to remote repository")
        return True

def pull_from_git():
    """Pull changes from the remote repository"""
    print("\n=== Pulling from Remote Repository ===")
    
    # First, stash any uncommitted changes
    print("Stashing any uncommitted changes")
    stash_result = run_command(["git", "stash"])
    stashed = stash_result.returncode == 0 and "No local changes to save" not in stash_result.stdout
    
    # Pull the latest changes
    print("Pulling latest changes")
    pull_result = run_command(["git", "pull"])
    
    pull_success = pull_result.returncode == 0
    
    # Pop the stash if we stashed changes
    if stashed:
        print("Restoring uncommitted changes")
        run_command(["git", "stash", "pop"])
    
    if pull_success:
        print("✅ Successfully pulled changes from remote repository")
    else:
        print("❌ Failed to pull changes from remote repository")
    
    return pull_success

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Git Management Utility for Smørås Fotball")
    parser.add_argument('command', nargs='?', default='status',
                        choices=['status', 'backup', 'push', 'pull', 'setup', 'all'],
                        help='Command to execute (default: status)')
    parser.add_argument('--message', '-m', help='Commit message for backup operation')
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    
    print("\n=== Smørås Fotball Git Management Utility ===\n")
    
    if args.command == 'status':
        get_git_status()
    
    elif args.command == 'setup':
        setup_git()
    
    elif args.command == 'backup':
        backup_path = create_backup()
        if backup_path:
            commit_changes(args.message)
            get_git_status()
    
    elif args.command == 'push':
        push_to_git()
    
    elif args.command == 'pull':
        pull_from_git()
    
    elif args.command == 'all':
        # Run all operations in sequence
        setup_git()
        backup_path = create_backup()
        if backup_path:
            commit_changes(args.message)
        push_to_git()
        pull_from_git()
        get_git_status()
    
    print("\n=== Operation Completed ===")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())