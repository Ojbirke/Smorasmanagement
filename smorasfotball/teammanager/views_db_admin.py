from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.management import call_command
from django.contrib.auth.models import User
from django.db import connections
from django.db.utils import OperationalError
from django.conf import settings
from .models import Team, Player, Match, MatchAppearance, UserProfile
import os
import io
import json
import sys
import shutil
import sqlite3
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path

def is_admin(user):
    """Check if user is an approved admin"""
    if not user.is_authenticated:
        return False
    try:
        return user.profile.is_admin() and user.profile.is_approved()
    except:
        return False

@login_required
def database_overview(request):
    """Display database statistics and backup options"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get database statistics
    stats = {
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
        'matches': Match.objects.count(),
        'appearances': MatchAppearance.objects.count(),
        'users': User.objects.count(),
        'profiles': UserProfile.objects.count()
    }
    
    has_data = any(count > 0 for count in stats.values())
    
    # Get regular backup directory
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Get persistent backup directory
    persistent_backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    os.makedirs(persistent_backup_dir, exist_ok=True)
    
    # Get deployment backup directory
    deployment_backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    os.makedirs(deployment_backup_dir, exist_ok=True)
    
    # Check for regular backup files
    backups = []
    
    # Helper function to categorize backups
    def categorize_backup(filename):
        if 'auto_startup' in filename:
            return 'auto_startup'
        elif 'auto_shutdown' in filename:
            return 'auto_shutdown'
        else:
            return 'manual'
    
    # Get the latest backup of each type in regular directory
    if os.path.exists(backup_dir):
        backup_exists = True
        
        # Organize backups by type and extension
        categorized_backups = {
            'auto_startup': {'json': [], 'sqlite3': []},
            'auto_shutdown': {'json': [], 'sqlite3': []},
            'manual': {'json': [], 'sqlite3': []}
        }
        
        # Collect all files and organize them
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json') or filename.endswith('.sqlite3'):
                extension = 'json' if filename.endswith('.json') else 'sqlite3'
                category = categorize_backup(filename)
                file_path = os.path.join(backup_dir, filename)
                stat = os.stat(file_path)
                
                categorized_backups[category][extension].append({
                    'filename': filename,
                    'path': file_path,
                    'stat': stat,
                    'date': datetime.fromtimestamp(stat.st_mtime)
                })
        
        # Sort each category by date (newest first) and take only the latest one
        for category in categorized_backups:
            for extension in categorized_backups[category]:
                if categorized_backups[category][extension]:
                    # Sort by date, newest first
                    categorized_backups[category][extension].sort(key=lambda x: x['date'], reverse=True)
                    # Add only the latest file to the final list
                    latest = categorized_backups[category][extension][0]
                    backups.append({
                        'filename': latest['filename'],
                        'type': 'JSON Data' if extension == 'json' else 'SQLite Database',
                        'size': _format_file_size(latest['stat'].st_size),
                        'date': latest['date'],
                        'persistent': False,
                        'category': category
                    })
    else:
        backup_exists = False
    
    # Check for persistent backup files
    persistent_backups = []
    if os.path.exists(persistent_backup_dir):
        persistent_backup_exists = True
        
        # Organize persistent backups by type and extension
        categorized_persistent_backups = {
            'auto_startup': {'json': [], 'sqlite3': []},
            'auto_shutdown': {'json': [], 'sqlite3': []},
            'manual': {'json': [], 'sqlite3': []}
        }
        
        # Collect all files and organize them
        for filename in os.listdir(persistent_backup_dir):
            if filename.endswith('.json') or filename.endswith('.sqlite3'):
                extension = 'json' if filename.endswith('.json') else 'sqlite3'
                category = categorize_backup(filename)
                file_path = os.path.join(persistent_backup_dir, filename)
                stat = os.stat(file_path)
                
                categorized_persistent_backups[category][extension].append({
                    'filename': filename,
                    'path': file_path,
                    'stat': stat,
                    'date': datetime.fromtimestamp(stat.st_mtime)
                })
        
        # Sort each category by date (newest first) and take only the latest one
        for category in categorized_persistent_backups:
            for extension in categorized_persistent_backups[category]:
                if categorized_persistent_backups[category][extension]:
                    # Sort by date, newest first
                    categorized_persistent_backups[category][extension].sort(key=lambda x: x['date'], reverse=True)
                    # Add only the latest file to the final list
                    latest = categorized_persistent_backups[category][extension][0]
                    persistent_backups.append({
                        'filename': latest['filename'],
                        'type': 'JSON Data (Persistent)' if extension == 'json' else 'SQLite Database (Persistent)',
                        'size': _format_file_size(latest['stat'].st_size),
                        'date': latest['date'],
                        'persistent': True,
                        'category': category
                    })
    else:
        persistent_backup_exists = False
    
    # Check for deployment-specific backups
    deployment_backups = []
    if os.path.exists(deployment_backup_dir):
        deployment_backup_exists = True
        
        # Collect deployment backup files
        for filename in os.listdir(deployment_backup_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(deployment_backup_dir, filename)
                stat = os.stat(file_path)
                
                deployment_backups.append({
                    'filename': filename,
                    'type': 'JSON Data (Deployment)',
                    'size': _format_file_size(stat.st_size),
                    'date': datetime.fromtimestamp(stat.st_mtime),
                    'deployment': True,
                    'category': 'deployment'
                })
        
        # Sort deployment backups by date (newest first)
        deployment_backups.sort(key=lambda x: x['date'], reverse=True)
    else:
        deployment_backup_exists = False
    
    context = {
        'stats': stats,
        'has_data': has_data,
        'backup_exists': backup_exists or persistent_backup_exists or deployment_backup_exists,
        'backups': backups,
        'persistent_backups': persistent_backups,
        'deployment_backups': deployment_backups,
        'has_persistent_backups': len(persistent_backups) > 0,
        'has_deployment_backups': len(deployment_backups) > 0,
        'is_admin': True,  # Pass this for the template
        'last_restored_backup': os.environ.get('LAST_RESTORED_BACKUP', 'Unknown'),
        'last_restore_time': os.environ.get('LAST_RESTORE_TIME', 'Unknown'),
        'is_deployment': os.path.exists(os.path.join(deployment_backup_dir, 'deployment_db.json'))
    }
    
    return render(request, 'teammanager/database_overview.html', context)

@login_required
def create_backup(request):
    """Create a database backup"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        return redirect('database-overview')
    
    # Check if we should create a deployment backup
    is_deployment_backup = request.POST.get('deployment_backup', 'false') == 'true'
    
    try:
        # Strip ANSI color codes pattern for all outputs
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        if is_deployment_backup:
            # Use the deployment_backup command
            output = io.StringIO()
            call_command('deployment_backup', stdout=output)
            
            # Extract messages from command output
            for line in output.getvalue().splitlines():
                if line.strip():
                    # Remove ANSI color codes
                    clean_line = ansi_escape.sub('', line)
                    if "success" in line.lower():
                        messages.success(request, clean_line)
                    else:
                        messages.info(request, clean_line)
            
            messages.success(request, "Deployment backup created successfully.")
            messages.info(request, "This backup will be used when deploying the application to production.")
        else:
            # Use the persistent_backup command for regular backups
            output = io.StringIO()
            call_command('persistent_backup', stdout=output)
            
            # Extract messages from command output
            for line in output.getvalue().splitlines():
                if line.strip():
                    # Remove ANSI color codes
                    clean_line = ansi_escape.sub('', line)
                    if "success" in line.lower():
                        messages.success(request, clean_line)
                    else:
                        messages.info(request, clean_line)
            
            messages.success(request, "Backup created successfully and stored in both regular and persistent locations.")
            messages.info(request, "The persistent backup will be available even after redeployments.")
    
    except Exception as e:
        messages.error(request, f"Error creating backup: {str(e)}")
    
    return redirect('database-overview')

@login_required
def restore_backup(request, filename):
    """Restore database from a backup file"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        return redirect('database-overview')
    
    # Check if it's a deployment backup
    is_deployment = request.POST.get('is_deployment', 'false') == 'true'
    
    # Check if it's a persistent backup (if not deployment)
    is_persistent = request.POST.get('is_persistent', 'false') == 'true'
    
    if is_deployment:
        # Use deployment directory
        backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    elif is_persistent:
        backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    else:
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    backup_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_path):
        backup_type = 'deployment' if is_deployment else ('persistent' if is_persistent else 'regular')
        messages.error(request, f"Backup file {filename} not found in {backup_type} backup directory.")
        return redirect('database-overview')
    
    try:
        if filename.endswith('.json'):
            # Restore from JSON backup
            restore_json_backup(backup_path)
            messages.success(request, f"Database restored successfully from {filename}.")
            
            # Record this restore in environment variables for diagnostic purposes
            os.environ['LAST_RESTORED_BACKUP'] = filename
            os.environ['LAST_RESTORE_TIME'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            messages.info(request, f"Recorded restore information: {filename} at {os.environ['LAST_RESTORE_TIME']}")
        
        elif filename.endswith('.sqlite3') and 'sqlite3' in settings.DATABASES['default']['ENGINE']:
            # Restore from SQLite backup
            restore_sqlite_backup(backup_path)
            messages.success(request, f"Database restored successfully from {filename}.")
            messages.info(request, "The application will restart to apply changes.")
            
            # Record this restore in environment variables for diagnostic purposes
            os.environ['LAST_RESTORED_BACKUP'] = filename
            os.environ['LAST_RESTORE_TIME'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            messages.info(request, f"Recorded restore information: {filename} at {os.environ['LAST_RESTORE_TIME']}")
        
        else:
            messages.error(request, f"Unsupported backup file format: {filename}")
    
    except Exception as e:
        messages.error(request, f"Error restoring backup: {str(e)}")
    
    return redirect('database-overview')

@login_required
def delete_backup(request, filename):
    """Delete a backup file"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        return redirect('database-overview')
    
    # Check if it's a deployment backup
    is_deployment = request.POST.get('is_deployment', 'false') == 'true'
    
    # Check if it's a persistent backup (if not deployment)
    is_persistent = request.POST.get('is_persistent', 'false') == 'true'
    
    if is_deployment:
        backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    elif is_persistent:
        backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    else:
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    backup_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_path):
        backup_type = 'deployment' if is_deployment else ('persistent' if is_persistent else 'regular')
        messages.error(request, f"Backup file {filename} not found in {backup_type} backup directory.")
        return redirect('database-overview')
    
    # Don't allow deletion of the special deployment_db.json file
    if is_deployment and filename == 'deployment_db.json':
        messages.error(request, f"Cannot delete the active deployment backup file. This is used during deployment.")
        return redirect('database-overview')
    
    try:
        os.remove(backup_path)
        backup_type = 'deployment' if is_deployment else ('persistent' if is_persistent else 'regular')
        messages.success(request, f"Backup file {filename} deleted successfully from {backup_type} backup directory.")
    except Exception as e:
        messages.error(request, f"Error deleting backup: {str(e)}")
    
    return redirect('database-overview')

@login_required
def push_to_git(request):
    """Push database backups to Git repository"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        return redirect('database-overview')
    
    try:
        # First, create a fresh deployment backup
        messages.info(request, "Creating a fresh deployment backup...")
        output = io.StringIO()
        call_command('deployment_backup', stdout=output)
        
        # Process output for backup messages
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        for line in output.getvalue().splitlines():
            if line.strip():
                # Remove ANSI color codes
                clean_line = ansi_escape.sub('', line)
                messages.info(request, clean_line)
        
        # Check if the deployment backup was created
        deployment_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
        deployment_db_path = os.path.join(deployment_dir, 'deployment_db.json')
        
        if os.path.exists(deployment_db_path):
            file_size = os.path.getsize(deployment_db_path)
            messages.success(request, f"Deployment backup created successfully: deployment_db.json ({file_size} bytes)")
            
            # Verify the backup contents
            try:
                with open(deployment_db_path, 'r') as f:
                    data = json.load(f)
                    record_count = len(data)
                    
                    # Count important model types
                    teams = len([x for x in data if x.get('model') == 'teammanager.team'])
                    players = len([x for x in data if x.get('model') == 'teammanager.player'])
                    users = len([x for x in data if x.get('model') == 'auth.user'])
                    
                    messages.info(request, f"Backup contains: {teams} teams, {players} players, {users} users, {record_count} total records")
            except Exception as e:
                messages.warning(request, f"Could not verify backup contents: {str(e)}")
        else:
            messages.warning(request, "Deployment backup file was not created. The Git push may not contain your latest data.")
        
        # Now execute the sync_backups_with_repo command with the push option
        messages.info(request, "Pushing backups to Git repository...")
        output = io.StringIO()
        call_command('sync_backups_with_repo', push=True, stdout=output)
        
        # Process output for git messages
        output_lines = output.getvalue().splitlines()
        for line in output_lines:
            if line.strip():
                # Remove ANSI color codes
                clean_line = ansi_escape.sub('', line)
                messages.info(request, f"Git output: {clean_line}")
        
        # Try to find important information about the push
        added_files = []
        for line in output_lines:
            if "Added:" in line:
                added_file = line.split("Added:")[-1].strip()
                added_files.append(added_file)
        
        if added_files:
            messages.success(request, f"Successfully added {len(added_files)} files to Git")
            messages.info(request, f"Files: {', '.join(added_files)}")
        
        success_found = any("success" in line.lower() for line in output_lines)
        if success_found:
            messages.success(request, "Database backups have been successfully pushed to Git repository.")
            messages.info(request, "These backups will be available even after redeployments.")
        else:
            messages.info(request, "Git push operation completed, but no explicit success message was found in the output.")
    
    except Exception as e:
        messages.error(request, f"Error pushing backups to Git: {str(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            tb = ''.join(traceback.format_tb(e.__traceback__))
            messages.error(request, f"Traceback: {tb}")
    
    return redirect('database-overview')

@login_required
def pull_from_git(request):
    """Pull database backups from Git repository"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        return redirect('database-overview')
    
    # First, create a backup of the current database as a safety precaution
    try:
        messages.info(request, "Creating safety backup before Git pull operation...")
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        safety_backup_name = f"pre_git_restore_{timestamp}"
        output = io.StringIO()
        call_command('persistent_backup', name=safety_backup_name, stdout=output)
        messages.success(request, f"Safety backup created: {safety_backup_name}")
    except Exception as e:
        messages.warning(request, f"Could not create safety backup: {str(e)}")
    
    try:
        # Execute the sync_backups_with_repo command with the pull option
        messages.info(request, "Pulling latest backups from Git repository...")
        output = io.StringIO()
        call_command('sync_backups_with_repo', pull=True, stdout=output)
        
        # Process output for user messages
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        output_lines = output.getvalue().splitlines()
        for line in output_lines:
            if line.strip():
                # Remove ANSI color codes
                clean_line = ansi_escape.sub('', line)
                messages.info(request, f"Git output: {clean_line}")
        
        success_found = any("success" in line.lower() for line in output_lines)
        
        # Find the latest deployment backup
        deployment_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
        messages.info(request, f"Checking deployment directory: {deployment_dir}")
        
        if os.path.exists(deployment_dir):
            # List all files in the deployment directory for debugging
            file_list = os.listdir(deployment_dir)
            messages.info(request, f"Files in deployment directory: {', '.join(file_list)}")
            
            # Look for deployment_db.json and other backups
            deployment_db_path = os.path.join(deployment_dir, 'deployment_db.json')
            
            if os.path.exists(deployment_db_path):
                file_size = os.path.getsize(deployment_db_path)
                messages.info(request, f"Found deployment_db.json (Size: {file_size} bytes)")
                
                if file_size > 100:  # Basic check to ensure it's not empty
                    # Verify the file content
                    try:
                        with open(deployment_db_path, 'r') as f:
                            data = json.load(f)
                            record_count = len(data)
                            messages.info(request, f"JSON backup contains {record_count} records")
                            
                            # Show counts of important model types
                            teams = len([x for x in data if x.get('model') == 'teammanager.team'])
                            players = len([x for x in data if x.get('model') == 'teammanager.player'])
                            users = len([x for x in data if x.get('model') == 'auth.user'])
                            
                            messages.info(request, f"Contents: {teams} teams, {players} players, {users} users")
                            
                            if record_count > 0:
                                # Automatically restore from the pulled backup
                                try:
                                    messages.info(request, "Starting database restoration from Git backup...")
                                    restore_json_backup(deployment_db_path)
                                    messages.success(request, "Database successfully restored from Git backup.")
                                    
                                    # Record this restore in environment variables for diagnostic purposes
                                    os.environ['LAST_RESTORED_BACKUP'] = 'deployment_db.json (from Git)'
                                    os.environ['LAST_RESTORE_TIME'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                                    messages.info(request, f"Recorded restore information: deployment_db.json at {os.environ['LAST_RESTORE_TIME']}")
                                except Exception as e:
                                    messages.error(request, f"Error during database restoration: {str(e)}")
                                    if hasattr(e, '__traceback__'):
                                        import traceback
                                        tb = ''.join(traceback.format_tb(e.__traceback__))
                                        messages.error(request, f"Traceback: {tb}")
                            else:
                                messages.error(request, "The backup file is empty or has no records. No restoration performed.")
                        
                    except json.JSONDecodeError as e:
                        messages.error(request, f"The JSON backup file is invalid: {str(e)}")
                    except Exception as e:
                        messages.error(request, f"Error reading backup file: {str(e)}")
                else:
                    messages.error(request, f"The backup file is too small ({file_size} bytes) and appears to be empty or corrupted.")
            else:
                messages.warning(request, "No deployment_db.json found in the deployment directory.")
                
                # Look for any other JSON backups
                json_backups = [f for f in file_list if f.endswith('.json') and 'deployment' in f]
                if json_backups:
                    messages.info(request, f"Found alternative backups: {', '.join(json_backups)}")
                    # Use the most recent one
                    json_backups.sort(key=lambda x: os.path.getmtime(os.path.join(deployment_dir, x)), reverse=True)
                    alt_backup = os.path.join(deployment_dir, json_backups[0])
                    
                    messages.info(request, f"Attempting to restore from alternative backup: {json_backups[0]}")
                    try:
                        restore_json_backup(alt_backup)
                        messages.success(request, f"Database restored from alternative backup: {json_backups[0]}")
                    except Exception as e:
                        messages.error(request, f"Error restoring from alternative backup: {str(e)}")
                else:
                    messages.error(request, "No suitable JSON backups found in the deployment directory.")
        else:
            messages.error(request, f"Deployment directory not found: {deployment_dir}")
    
    except Exception as e:
        messages.error(request, f"Error during Git pull operation: {str(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            tb = ''.join(traceback.format_tb(e.__traceback__))
            messages.error(request, f"Traceback: {tb}")
    
    return redirect('database-overview')

@login_required
def download_backup(request, filename):
    """Show instructions for downloading a backup file"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Check if it's a deployment backup
    is_deployment = request.GET.get('deployment', 'false') == 'true'
    
    # Check if it's a persistent backup (if not deployment)
    is_persistent = request.GET.get('persistent', 'false') == 'true'
    
    if is_deployment:
        backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    elif is_persistent:
        backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    else:
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    filepath = os.path.join(backup_dir, filename)
    
    if not os.path.exists(filepath):
        backup_type = 'deployment' if is_deployment else ('persistent' if is_persistent else 'regular')
        messages.error(request, f"Backup file {filename} not found in {backup_type} backup directory.")
        return redirect('database-overview')
    
    # Check backup contents for verification
    backup_info = {}
    if filename.endswith('.json'):
        try:
            with open(filepath, 'r') as f:
                backup_data = json.load(f)
                
                # Count users and other important objects
                user_count = len([item for item in backup_data if item['model'] == 'auth.user'])
                player_count = len([item for item in backup_data if item['model'] == 'teammanager.player'])
                team_count = len([item for item in backup_data if item['model'] == 'teammanager.team'])
                match_count = len([item for item in backup_data if item['model'] == 'teammanager.match'])
                profile_count = len([item for item in backup_data if item['model'] == 'teammanager.userprofile'])
                
                backup_info = {
                    'user_count': user_count,
                    'player_count': player_count,
                    'team_count': team_count,
                    'match_count': match_count,
                    'profile_count': profile_count,
                    'has_users': user_count > 0
                }
        except Exception as e:
            backup_info = {'error': str(e)}
    
    if is_deployment:
        backup_location = 'Deployment'
    elif is_persistent:
        backup_location = 'Persistent'
    else:
        backup_location = 'Regular'
    
    context = {
        'filename': filename,
        'filepath': filepath,
        'is_admin': True,
        'is_persistent': is_persistent,
        'is_deployment': is_deployment,
        'backup_location': backup_location,
        'backup_info': backup_info
    }
    
    return render(request, 'teammanager/download_backup.html', context)

# Helper functions

def _format_file_size(size_in_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024 or unit == 'GB':
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024

def restore_json_backup(backup_path):
    """Restore database from JSON backup file"""
    # Clear existing data while preserving structure
    call_command('flush', '--no-input')
    
    # Load data from the backup
    call_command('loaddata', backup_path)

def restore_sqlite_backup(backup_path):
    """Restore database from SQLite backup file"""
    db_path = settings.DATABASES['default']['NAME']
    
    # Close all database connections
    connections.close_all()
    
    # Create a backup of the current database first
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    current_backup = os.path.join(os.path.dirname(backup_path), f'pre_restore_{timestamp}.sqlite3')
    
    try:
        # Backup current database
        if os.path.exists(db_path):
            shutil.copy2(db_path, current_backup)
        
        # Restore from backup
        shutil.copy2(backup_path, db_path)
    except Exception as e:
        # If restore fails, try to restore from the pre-restore backup
        if os.path.exists(current_backup):
            shutil.copy2(current_backup, db_path)
        raise e

@login_required
def cleanup_backups(request):
    """Clean up excess backup files to save space"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        return redirect('database-overview')
    
    keep = int(request.POST.get('keep', '1'))
    if keep < 1:
        keep = 1
    
    try:
        # Call the cleanup_backups management command to handle the cleanup
        output = io.StringIO()
        call_command('cleanup_backups', keep=keep, force_cleanup=True, stdout=output)
        
        # Strip ANSI color codes pattern
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        # Extract messages from command output
        for line in output.getvalue().splitlines():
            if line.strip():
                # Remove ANSI color codes
                clean_line = ansi_escape.sub('', line)
                if "error" in line.lower():
                    messages.error(request, clean_line)
                else:
                    messages.info(request, clean_line)
        
        messages.success(request, f"Backup cleanup completed. Kept the latest {keep} backup(s) of each type.")
    
    except Exception as e:
        messages.error(request, f"Error cleaning up backups: {str(e)}")
    
    return redirect('database-overview')