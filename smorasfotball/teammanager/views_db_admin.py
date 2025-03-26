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
    
    # Check for regular backup files
    backups = []
    if os.path.exists(backup_dir):
        backup_exists = True
        
        for filename in sorted(os.listdir(backup_dir), reverse=True):
            if filename.endswith('.json') or filename.endswith('.sqlite3'):
                file_path = os.path.join(backup_dir, filename)
                stat = os.stat(file_path)
                backups.append({
                    'filename': filename,
                    'type': 'JSON Data' if filename.endswith('.json') else 'SQLite Database',
                    'size': _format_file_size(stat.st_size),
                    'date': datetime.fromtimestamp(stat.st_mtime),
                    'persistent': False
                })
    else:
        backup_exists = False
    
    # Check for persistent backup files
    persistent_backups = []
    if os.path.exists(persistent_backup_dir):
        persistent_backup_exists = True
        
        for filename in sorted(os.listdir(persistent_backup_dir), reverse=True):
            if filename.endswith('.json') or filename.endswith('.sqlite3'):
                file_path = os.path.join(persistent_backup_dir, filename)
                stat = os.stat(file_path)
                persistent_backups.append({
                    'filename': filename,
                    'type': 'JSON Data (Persistent)' if filename.endswith('.json') else 'SQLite Database (Persistent)',
                    'size': _format_file_size(stat.st_size),
                    'date': datetime.fromtimestamp(stat.st_mtime),
                    'persistent': True
                })
    else:
        persistent_backup_exists = False
    
    context = {
        'stats': stats,
        'has_data': has_data,
        'backup_exists': backup_exists or persistent_backup_exists,
        'backups': backups,
        'persistent_backups': persistent_backups,
        'has_persistent_backups': len(persistent_backups) > 0,
        'is_admin': True  # Pass this for the template
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
    
    try:
        # Use the management command to create persistent backups
        output = io.StringIO()
        call_command('persistent_backup', stdout=output)
        
        # Extract messages from command output
        for line in output.getvalue().splitlines():
            if line.strip():
                if "success" in line.lower():
                    messages.success(request, line)
                else:
                    messages.info(request, line)
        
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
    
    # Check if it's a persistent backup
    is_persistent = request.POST.get('is_persistent', 'false') == 'true'
    
    if is_persistent:
        backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    else:
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    backup_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_path):
        messages.error(request, f"Backup file {filename} not found in {'persistent' if is_persistent else 'regular'} backup directory.")
        return redirect('database-overview')
    
    try:
        if filename.endswith('.json'):
            # Restore from JSON backup
            restore_json_backup(backup_path)
            messages.success(request, f"Database restored successfully from {filename}.")
        
        elif filename.endswith('.sqlite3') and 'sqlite3' in settings.DATABASES['default']['ENGINE']:
            # Restore from SQLite backup
            restore_sqlite_backup(backup_path)
            messages.success(request, f"Database restored successfully from {filename}.")
            messages.info(request, "The application will restart to apply changes.")
        
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
    
    # Check if it's a persistent backup
    is_persistent = request.POST.get('is_persistent', 'false') == 'true'
    
    if is_persistent:
        backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    else:
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    backup_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_path):
        messages.error(request, f"Backup file {filename} not found in {'persistent' if is_persistent else 'regular'} backup directory.")
        return redirect('database-overview')
    
    try:
        os.remove(backup_path)
        messages.success(request, f"Backup file {filename} deleted successfully from {'persistent' if is_persistent else 'regular'} backup directory.")
    except Exception as e:
        messages.error(request, f"Error deleting backup: {str(e)}")
    
    return redirect('database-overview')

@login_required
def download_backup(request, filename):
    """Show instructions for downloading a backup file"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Check if it's a persistent backup
    is_persistent = request.GET.get('persistent', 'false') == 'true'
    
    if is_persistent:
        backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
    else:
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    filepath = os.path.join(backup_dir, filename)
    
    if not os.path.exists(filepath):
        messages.error(request, f"Backup file {filename} not found in {'persistent' if is_persistent else 'regular'} backup directory.")
        return redirect('database-overview')
    
    context = {
        'filename': filename,
        'filepath': filepath,
        'is_admin': True,
        'is_persistent': is_persistent,
        'backup_location': 'Persistent' if is_persistent else 'Regular'
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
        
        # Extract messages from command output
        for line in output.getvalue().splitlines():
            if line.strip():
                if "error" in line.lower():
                    messages.error(request, line)
                else:
                    messages.info(request, line)
        
        messages.success(request, f"Backup cleanup completed. Kept the latest {keep} backup(s) of each type.")
    
    except Exception as e:
        messages.error(request, f"Error cleaning up backups: {str(e)}")
    
    return redirect('database-overview')