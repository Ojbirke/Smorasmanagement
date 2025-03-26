from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.management import call_command
from django.contrib.auth.models import User
from teammanager.models import Team, Player, Match, MatchAppearance, UserProfile
from io import StringIO
import os
import glob
import shutil
from threading import Thread
import time
import json

def is_admin(user):
    """Check if user is an approved admin"""
    try:
        return user.profile.is_admin() and user.profile.is_approved()
    except:
        return False

@login_required
def database_overview(request):
    """Display database statistics and backup options"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access database management.")
        return redirect('dashboard')
    
    # Gather database statistics
    stats = {
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
        'matches': Match.objects.count(),
        'appearances': MatchAppearance.objects.count(),
        'users': User.objects.count(),
        'profiles': UserProfile.objects.count(),
    }
    
    # Check if backup directory exists and get list of backups
    backup_dir = os.path.join(os.getcwd(), 'backup')
    backup_exists = os.path.exists(backup_dir)
    
    backups = []
    if backup_exists:
        json_backups = glob.glob(os.path.join(backup_dir, '*.json'))
        sqlite_backups = glob.glob(os.path.join(backup_dir, '*.sqlite3'))
        
        for backup in sorted(json_backups + sqlite_backups, reverse=True):
            filename = os.path.basename(backup)
            size = os.path.getsize(backup) / (1024 * 1024)  # Convert to MB
            modified = timezone.datetime.fromtimestamp(os.path.getmtime(backup))
            backups.append({
                'filename': filename,
                'path': backup,
                'size': f"{size:.2f} MB",
                'date': modified,
                'type': 'JSON Data' if filename.endswith('.json') else 'SQLite Database'
            })
    
    return render(request, 'teammanager/database_overview.html', {
        'stats': stats,
        'backup_exists': backup_exists,
        'backups': backups,
        'has_data': any(count > 0 for count in stats.values())
    })

@login_required
def create_backup(request):
    """Create a database backup"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to create database backups.")
        return redirect('database-overview')
    
    if request.method != 'POST':
        return redirect('database-overview')
    
    # Create backup directory if it doesn't exist
    backup_dir = os.path.join(os.getcwd(), 'backup')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Generate filename with timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    
    # Create JSON backup (dumpdata)
    json_file = os.path.join(backup_dir, f'db_backup_{timestamp}.json')
    
    # Capture command output
    stdout = StringIO()
    
    try:
        call_command(
            'dumpdata',
            '--exclude', 'contenttypes',
            '--exclude', 'auth.Permission',
            '--indent', '4',
            stdout=stdout
        )
        
        # Write the output to file
        with open(json_file, 'w') as f:
            f.write(stdout.getvalue())
        
        # Create a copy of the SQLite database file if it exists
        db_path = os.path.join(os.getcwd(), 'db.sqlite3')
        if os.path.exists(db_path):
            db_backup = os.path.join(backup_dir, f'db_{timestamp}.sqlite3')
            shutil.copy2(db_path, db_backup)
            messages.success(request, f"Backup created successfully. Both JSON and SQLite backups were created.")
        else:
            messages.success(request, f"JSON backup created successfully. SQLite file not found.")
    
    except Exception as e:
        messages.error(request, f"Backup creation failed: {str(e)}")
    
    return redirect('database-overview')

@login_required
def restore_backup(request, filename):
    """Restore database from a backup file"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to restore database backups.")
        return redirect('database-overview')
    
    if request.method != 'POST':
        return redirect('database-overview')
    
    backup_dir = os.path.join(os.getcwd(), 'backup')
    backup_file = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_file):
        messages.error(request, f"Backup file not found: {filename}")
        return redirect('database-overview')
    
    # Perform the restore based on file extension
    try:
        if filename.endswith('.json'):
            # Restore from JSON (dumpdata) file
            # We run this in a background thread because it can take some time
            # and we want to return a response to the user quickly
            def restore_json_backup():
                try:
                    # Flush the database first (but keep the superuser)
                    call_command('flush', '--noinput')
                    # Load data from backup
                    call_command('loaddata', backup_file)
                except Exception as e:
                    print(f"Error restoring database: {str(e)}")
            
            Thread(target=restore_json_backup).start()
            messages.success(request, "Database restore from JSON initiated. This may take a few moments. You'll need to refresh the page in 15-30 seconds.")
        
        elif filename.endswith('.sqlite3'):
            # Restore from SQLite file (direct copy)
            db_path = os.path.join(os.getcwd(), 'db.sqlite3')
            
            # Create a backup of the current database before overwriting
            if os.path.exists(db_path):
                temp_backup = f'{db_path}.bak'
                shutil.copy2(db_path, temp_backup)
            
            # Copy the backup database over the current one
            def restore_sqlite_backup():
                # Add a short delay to ensure the response is sent
                time.sleep(2)
                try:
                    shutil.copy2(backup_file, db_path)
                except Exception as e:
                    print(f"Error restoring SQLite database: {str(e)}")
            
            Thread(target=restore_sqlite_backup).start()
            messages.success(request, "SQLite database restore initiated. The server will restart automatically. Please refresh the page in 15-30 seconds.")
        
        else:
            messages.error(request, "Unsupported backup file format. Please use .json or .sqlite3 files.")
    
    except Exception as e:
        messages.error(request, f"Error during restore: {str(e)}")
    
    return redirect('database-overview')

@login_required
def delete_backup(request, filename):
    """Delete a backup file"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to delete database backups.")
        return redirect('database-overview')
    
    if request.method != 'POST':
        return redirect('database-overview')
    
    backup_dir = os.path.join(os.getcwd(), 'backup')
    backup_file = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_file):
        messages.error(request, f"Backup file not found: {filename}")
    else:
        try:
            os.remove(backup_file)
            messages.success(request, f"Backup file deleted: {filename}")
        except Exception as e:
            messages.error(request, f"Error deleting backup file: {str(e)}")
    
    return redirect('database-overview')

@login_required
def download_backup(request, filename):
    """Show instructions for downloading a backup file"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to download database backups.")
        return redirect('database-overview')
    
    backup_dir = os.path.join(os.getcwd(), 'backup')
    backup_file = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_file):
        messages.error(request, f"Backup file not found: {filename}")
        return redirect('database-overview')
    
    # For simplicity, display instructions for manual download
    # In a production environment, you'd implement proper file serving
    return render(request, 'teammanager/download_backup.html', {
        'filename': filename,
        'filepath': backup_file
    })