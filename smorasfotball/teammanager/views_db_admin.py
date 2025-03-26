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
    
    # Get backup directory
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Check for backup files
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
                })
    else:
        backup_exists = False
    
    context = {
        'stats': stats,
        'has_data': has_data,
        'backup_exists': backup_exists,
        'backups': backups,
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
    
    # Create backup directory if it doesn't exist
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    
    # Backup data as JSON
    try:
        json_filename = f'backup_{timestamp}.json'
        json_filepath = os.path.join(backup_dir, json_filename)
        
        # Use Django's dumpdata command to create JSON backup
        output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = output
        call_command('dumpdata', '--exclude', 'auth.permission', '--exclude', 'contenttypes', 
                    '--exclude', 'admin.logentry', '--indent', '2', stdout=output)
        sys.stdout = original_stdout
        
        with open(json_filepath, 'w') as f:
            f.write(output.getvalue())
        
        messages.success(request, f"JSON data backup created successfully.")
        
        # If using SQLite, also backup the database file
        if 'sqlite3' in settings.DATABASES['default']['ENGINE']:
            db_path = settings.DATABASES['default']['NAME']
            if os.path.exists(db_path):
                sqlite_filename = f'backup_{timestamp}.sqlite3'
                sqlite_filepath = os.path.join(backup_dir, sqlite_filename)
                
                # Create a copy of the SQLite database
                shutil.copy2(db_path, sqlite_filepath)
                messages.success(request, f"SQLite database backup created successfully.")
    
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
    
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_path):
        messages.error(request, f"Backup file {filename} not found.")
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
    
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_path):
        messages.error(request, f"Backup file {filename} not found.")
        return redirect('database-overview')
    
    try:
        os.remove(backup_path)
        messages.success(request, f"Backup file {filename} deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting backup: {str(e)}")
    
    return redirect('database-overview')

@login_required
def download_backup(request, filename):
    """Show instructions for downloading a backup file"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    filepath = os.path.join(backup_dir, filename)
    
    if not os.path.exists(filepath):
        messages.error(request, f"Backup file {filename} not found.")
        return redirect('database-overview')
    
    context = {
        'filename': filename,
        'filepath': filepath,
        'is_admin': True
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