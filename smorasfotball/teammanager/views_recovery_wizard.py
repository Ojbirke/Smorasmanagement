from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.db import models
from django.http import JsonResponse
import os
import json
import glob
import shutil
import re
import time
import datetime
from pathlib import Path

from .models import Team, Player, Match, UserProfile
from .views_db_admin import is_admin, restore_json_backup, restore_sqlite_backup, _format_file_size

@login_required
def recovery_wizard_start(request):
    """Start the database recovery wizard"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get current database state
    stats = {
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
        'matches': Match.objects.count(),
        'profiles': UserProfile.objects.count(),
    }
    
    # Current state summary
    db_state = 'empty' if all(count == 0 for count in stats.values()) else 'has_data'
    
    # Get deployment directory
    deployment_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    persistent_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    # Initialize backup counts
    backup_counts = {
        'deployment': 0,
        'persistent': 0,
        'regular': 0,
        'git': False
    }
    
    # Check if git backups exist
    git_backup_file = os.path.join(deployment_dir, 'deployment_db.json')
    backup_counts['git'] = os.path.exists(git_backup_file) and os.path.getsize(git_backup_file) > 100
    
    # Count backups by type
    if os.path.exists(deployment_dir):
        backup_counts['deployment'] = len([f for f in os.listdir(deployment_dir) 
                                       if f.endswith('.json') or f.endswith('.sqlite3')])
    
    if os.path.exists(persistent_dir):
        backup_counts['persistent'] = len([f for f in os.listdir(persistent_dir) 
                                       if f.endswith('.json') or f.endswith('.sqlite3')])
    
    if os.path.exists(backup_dir):
        backup_counts['regular'] = len([f for f in os.listdir(backup_dir) 
                                     if f.endswith('.json') or f.endswith('.sqlite3')])
    
    # Check if app is in deployment mode
    is_deployment = os.path.exists(os.path.join(deployment_dir, 'deployment_db.json'))
    
    context = {
        'stats': stats,
        'db_state': db_state,
        'backup_counts': backup_counts,
        'is_deployment': is_deployment,
        'last_restored_backup': os.environ.get('LAST_RESTORED_BACKUP', 'Unknown'),
        'last_restore_time': os.environ.get('LAST_RESTORE_TIME', 'Unknown'),
    }
    
    return render(request, 'teammanager/recovery_wizard_start.html', context)

@login_required
def recovery_wizard_select_type(request):
    """Select the type of backup to recover from"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get deployment directory
    deployment_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    persistent_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    # Initialize backup info
    backup_types = []
    
    # Check for Git deployment backup
    git_backup_file = os.path.join(deployment_dir, 'deployment_db.json')
    if os.path.exists(git_backup_file) and os.path.getsize(git_backup_file) > 100:
        # Try to get record counts from the JSON file
        try:
            with open(git_backup_file, 'r') as f:
                data = json.load(f)
                teams = len([x for x in data if x.get('model') == 'teammanager.team'])
                players = len([x for x in data if x.get('model') == 'teammanager.player'])
                git_backup_info = {
                    'name': 'Git Deployment Backup',
                    'description': f'Contains {teams} teams and {players} players',
                    'id': 'git',
                    'icon': 'fa-code-branch',
                    'color': 'success',
                    'timestamp': datetime.datetime.fromtimestamp(os.path.getmtime(git_backup_file)),
                    'filename': os.path.basename(git_backup_file)
                }
                backup_types.append(git_backup_info)
        except:
            # If we can't read the file, still include it but without details
            git_backup_info = {
                'name': 'Git Deployment Backup',
                'description': 'Backup from Git deployment',
                'id': 'git',
                'icon': 'fa-code-branch',
                'color': 'success',
                'timestamp': datetime.datetime.fromtimestamp(os.path.getmtime(git_backup_file)),
                'filename': os.path.basename(git_backup_file)
            }
            backup_types.append(git_backup_info)
    
    # Check for deployment backups
    if os.path.exists(deployment_dir):
        json_files = [f for f in os.listdir(deployment_dir) if f.endswith('.json')]
        sqlite_files = [f for f in os.listdir(deployment_dir) if f.endswith('.sqlite3')]
        
        if json_files or sqlite_files:
            backup_types.append({
                'name': 'Deployment Backups',
                'description': f'{len(json_files)} JSON and {len(sqlite_files)} SQLite files',
                'id': 'deployment',
                'icon': 'fa-cloud-upload-alt',
                'color': 'primary',
                'count': len(json_files) + len(sqlite_files)
            })
    
    # Check for persistent backups
    if os.path.exists(persistent_dir):
        json_files = [f for f in os.listdir(persistent_dir) if f.endswith('.json')]
        sqlite_files = [f for f in os.listdir(persistent_dir) if f.endswith('.sqlite3')]
        
        if json_files or sqlite_files:
            backup_types.append({
                'name': 'Persistent Backups',
                'description': f'{len(json_files)} JSON and {len(sqlite_files)} SQLite files',
                'id': 'persistent',
                'icon': 'fa-database',
                'color': 'info',
                'count': len(json_files) + len(sqlite_files)
            })
    
    # Check for regular backups
    if os.path.exists(backup_dir):
        json_files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
        sqlite_files = [f for f in os.listdir(backup_dir) if f.endswith('.sqlite3')]
        
        if json_files or sqlite_files:
            backup_types.append({
                'name': 'Regular Backups',
                'description': f'{len(json_files)} JSON and {len(sqlite_files)} SQLite files',
                'id': 'regular',
                'icon': 'fa-save',
                'color': 'secondary',
                'count': len(json_files) + len(sqlite_files)
            })
    
    # Check for emergency restore option if no other options are available
    if not backup_types:
        backup_types.append({
            'name': 'Emergency Recovery',
            'description': 'Try to recreate the database from scratch',
            'id': 'emergency',
            'icon': 'fa-ambulance',
            'color': 'danger',
            'count': 0
        })
    
    context = {
        'backup_types': backup_types,
    }
    
    return render(request, 'teammanager/recovery_wizard_select_type.html', context)

@login_required
def recovery_wizard_select_backup(request, backup_type):
    """Select specific backup file to recover from"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get directories based on type
    deployment_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    persistent_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    # For Git backup, we don't need to select a file, so redirect to confirmation
    if backup_type == 'git':
        git_backup_file = os.path.join(deployment_dir, 'deployment_db.json')
        if os.path.exists(git_backup_file):
            return redirect('recovery-wizard-confirm', 
                            backup_type=backup_type, 
                            filename=os.path.basename(git_backup_file))
        else:
            messages.error(request, "Git deployment backup not found.")
            return redirect('recovery-wizard-start')
    
    # For emergency recovery, go straight to confirmation
    if backup_type == 'emergency':
        return redirect('recovery-wizard-confirm', 
                        backup_type=backup_type, 
                        filename='emergency_recovery')
    
    # Determine which directory to use
    if backup_type == 'deployment':
        current_dir = deployment_dir
        title = "Select Deployment Backup"
    elif backup_type == 'persistent':
        current_dir = persistent_dir
        title = "Select Persistent Backup"
    else:  # regular
        current_dir = backup_dir
        title = "Select Regular Backup"
    
    # Get list of backup files
    backup_files = []
    
    if os.path.exists(current_dir):
        for filename in os.listdir(current_dir):
            if filename.endswith('.json') or filename.endswith('.sqlite3'):
                file_path = os.path.join(current_dir, filename)
                stat = os.stat(file_path)
                
                # Get file metadata
                file_type = 'JSON Data' if filename.endswith('.json') else 'SQLite Database'
                file_size = _format_file_size(stat.st_size)
                file_date = datetime.datetime.fromtimestamp(stat.st_mtime)
                
                # For JSON files, try to get record counts
                record_counts = {}
                if filename.endswith('.json') and stat.st_size > 100:
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            record_counts = {
                                'teams': len([x for x in data if x.get('model') == 'teammanager.team']),
                                'players': len([x for x in data if x.get('model') == 'teammanager.player']),
                                'matches': len([x for x in data if x.get('model') == 'teammanager.match']),
                                'total': len(data)
                            }
                    except:
                        # If we can't read the file, just continue
                        pass
                
                backup_files.append({
                    'filename': filename,
                    'type': file_type,
                    'size': file_size,
                    'date': file_date,
                    'record_counts': record_counts
                })
        
        # Sort by date, newest first
        backup_files.sort(key=lambda x: x['date'], reverse=True)
    
    context = {
        'backup_type': backup_type,
        'title': title,
        'backup_files': backup_files,
    }
    
    return render(request, 'teammanager/recovery_wizard_select_backup.html', context)

@login_required
def recovery_wizard_confirm(request, backup_type, filename):
    """Confirm database recovery"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get current database state
    stats = {
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
        'matches': Match.objects.count(),
        'profiles': UserProfile.objects.count(),
    }
    
    # For emergency recovery
    if backup_type == 'emergency':
        context = {
            'backup_type': backup_type,
            'filename': 'emergency_recovery',
            'stats': stats,
            'emergency': True
        }
        return render(request, 'teammanager/recovery_wizard_confirm.html', context)
    
    # Get backup file info
    deployment_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    persistent_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    # Determine which directory to use
    if backup_type == 'git':
        current_dir = deployment_dir
        file_path = os.path.join(current_dir, filename)
        is_git = True
    elif backup_type == 'deployment':
        current_dir = deployment_dir
        file_path = os.path.join(current_dir, filename)
        is_git = False
    elif backup_type == 'persistent':
        current_dir = persistent_dir
        file_path = os.path.join(current_dir, filename)
        is_git = False
    else:  # regular
        current_dir = backup_dir
        file_path = os.path.join(current_dir, filename)
        is_git = False
    
    if not os.path.exists(file_path):
        messages.error(request, f"Backup file not found: {filename}")
        return redirect('recovery-wizard-start')
    
    # Get file metadata
    stat = os.stat(file_path)
    file_type = 'JSON Data' if filename.endswith('.json') else 'SQLite Database'
    file_size = _format_file_size(stat.st_size)
    file_date = datetime.datetime.fromtimestamp(stat.st_mtime)
    
    # For JSON files, try to get record counts
    record_counts = {}
    if filename.endswith('.json') and stat.st_size > 100:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                record_counts = {
                    'teams': len([x for x in data if x.get('model') == 'teammanager.team']),
                    'players': len([x for x in data if x.get('model') == 'teammanager.player']),
                    'matches': len([x for x in data if x.get('model') == 'teammanager.match']),
                    'total': len(data)
                }
        except:
            # If we can't read the file, just continue
            pass
    
    backup_info = {
        'filename': filename,
        'type': file_type,
        'size': file_size,
        'date': file_date,
        'record_counts': record_counts,
        'is_git': is_git
    }
    
    context = {
        'backup_type': backup_type,
        'filename': filename,
        'backup_info': backup_info,
        'stats': stats,
    }
    
    return render(request, 'teammanager/recovery_wizard_confirm.html', context)

@login_required
def recovery_wizard_execute(request):
    """Execute database recovery"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        return redirect('recovery-wizard-start')
    
    backup_type = request.POST.get('backup_type')
    filename = request.POST.get('filename')
    
    # Handle emergency recovery
    if backup_type == 'emergency':
        try:
            # Create a pre-recovery backup just in case
            from django.core.management import call_command
            call_command('persistent_backup', name='pre_emergency_recovery')
            messages.info(request, "Created a backup before emergency recovery.")
            
            # Set up superuser
            call_command('recreate_superuser')
            messages.success(request, "Recreated admin user (Username: djadmin, Password: superuser123)")
            
            # Recreate initial data
            call_command('createinitialdata')
            messages.success(request, "Recreated initial application data.")
            
            # Record recovery info
            os.environ['LAST_RESTORED_BACKUP'] = 'emergency_recovery'
            os.environ['LAST_RESTORE_TIME'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Redirect to success page
            return redirect('recovery-wizard-success')
            
        except Exception as e:
            messages.error(request, f"Emergency recovery failed: {str(e)}")
            return redirect('recovery-wizard-start')
    
    # Get backup file path
    deployment_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'deployment')
    persistent_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    # Determine which directory to use
    if backup_type == 'git':
        current_dir = deployment_dir
    elif backup_type == 'deployment':
        current_dir = deployment_dir
    elif backup_type == 'persistent':
        current_dir = persistent_dir
    else:  # regular
        current_dir = backup_dir
    
    file_path = os.path.join(current_dir, filename)
    
    if not os.path.exists(file_path):
        messages.error(request, f"Backup file not found: {filename}")
        return redirect('recovery-wizard-start')
    
    try:
        # Create a pre-restore backup
        from django.core.management import call_command
        call_command('persistent_backup', name='pre_wizard_restore')
        messages.info(request, "Created a backup before restoration.")
        
        # Perform the restore based on file type
        if filename.endswith('.json'):
            # Restore from JSON backup
            restore_json_backup(file_path)
            messages.success(request, f"Database restored successfully from {filename}.")
        
        elif filename.endswith('.sqlite3') and 'sqlite3' in settings.DATABASES['default']['ENGINE']:
            # Restore from SQLite backup
            restore_sqlite_backup(file_path)
            messages.success(request, f"Database restored successfully from {filename}.")
        
        else:
            messages.error(request, f"Unsupported backup file format: {filename}")
            return redirect('recovery-wizard-start')
        
        # Record this restore in environment variables for diagnostic purposes
        os.environ['LAST_RESTORED_BACKUP'] = filename
        os.environ['LAST_RESTORE_TIME'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Redirect to success page
        return redirect('recovery-wizard-success')
        
    except Exception as e:
        messages.error(request, f"Error restoring backup: {str(e)}")
        return redirect('recovery-wizard-start')

@login_required
def recovery_wizard_success(request):
    """Show recovery success page"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get current database state
    stats = {
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
        'matches': Match.objects.count(),
        'profiles': UserProfile.objects.count(),
    }
    
    context = {
        'stats': stats,
        'last_restored_backup': os.environ.get('LAST_RESTORED_BACKUP', 'Unknown'),
        'last_restore_time': os.environ.get('LAST_RESTORE_TIME', 'Unknown'),
    }
    
    return render(request, 'teammanager/recovery_wizard_success.html', context)