import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.translation import gettext as _
from backup_config import (
    load_config, save_config, get_backup_path, 
    set_backup_path, configure_git_backup, get_backup_git_repo
)

@staff_member_required
def backup_config_view(request):
    """Admin view for backup configuration"""
    config = load_config()
    backup_directory = get_backup_path()
    git_config = get_backup_git_repo() or {}
    
    # Get configuration from loaded config
    context = {
        'backup_directory': backup_directory,
        'backup_dir_writable': os.access(backup_directory, os.W_OK) if os.path.exists(backup_directory) else False,
        'git_backup_enabled': git_config.get('enabled', False),
        'git_repo': git_config.get('repository', ''),
        'git_branch': git_config.get('branch', 'main'),
        'git_username': git_config.get('username', ''),
        'backup_locations': config.get('backup_locations', []),
    }
    
    if request.method == 'POST':
        if 'test' in request.POST:
            # Test backup directories
            if not os.path.exists(backup_directory):
                try:
                    os.makedirs(backup_directory, exist_ok=True)
                    messages.success(request, _('Created backup directory: {}').format(backup_directory))
                except Exception as e:
                    messages.error(request, _('Failed to create backup directory: {}').format(str(e)))
            
            # Test write access
            if os.path.exists(backup_directory):
                if os.access(backup_directory, os.W_OK):
                    messages.success(request, _('Backup directory is writable: {}').format(backup_directory))
                    
                    # Try to create a test file
                    test_file = os.path.join(backup_directory, 'test_write.tmp')
                    try:
                        with open(test_file, 'w') as f:
                            f.write('Test backup directory write access')
                        os.remove(test_file)
                        messages.success(request, _('Successfully wrote and removed test file'))
                    except Exception as e:
                        messages.error(request, _('Failed to write test file: {}').format(str(e)))
                else:
                    messages.error(request, _('Backup directory is not writable: {}').format(backup_directory))
            
            # Check PostgreSQL configuration
            try:
                from django.conf import settings
                from django.db import connection
                
                db_settings = settings.DATABASES.get('default', {})
                db_engine = db_settings.get('ENGINE', '')
                
                if 'postgresql' in db_engine:
                    # Try to connect
                    cursor = connection.cursor()
                    cursor.execute('SELECT version();')
                    version = cursor.fetchone()[0]
                    cursor.close()
                    
                    messages.success(request, _('Successfully connected to PostgreSQL: {}').format(version))
                    
                    # Check for environment variables
                    pg_env_vars = ['PGDATABASE', 'PGUSER', 'PGPASSWORD', 'PGHOST', 'PGPORT', 'DATABASE_URL']
                    missing = [var for var in pg_env_vars if var not in os.environ]
                    
                    if missing:
                        messages.warning(request, _('Some PostgreSQL environment variables are missing: {}')
                                       .format(', '.join(missing)))
                    else:
                        messages.success(request, _('All PostgreSQL environment variables are set'))
                else:
                    messages.warning(request, _('PostgreSQL is not configured. Current engine: {}')
                                   .format(db_engine))
            except Exception as e:
                messages.error(request, _('Error testing PostgreSQL connection: {}').format(str(e)))
                
            # Refresh the context after tests
            context['backup_dir_writable'] = os.access(backup_directory, os.W_OK) if os.path.exists(backup_directory) else False
            
        elif 'save' in request.POST:
            # Save backup configuration
            new_backup_dir = request.POST.get('backup_directory', '').strip()
            
            # Update backup directory
            if new_backup_dir and new_backup_dir != backup_directory:
                # Expand user directory if path starts with ~
                if new_backup_dir.startswith('~'):
                    new_backup_dir = os.path.expanduser(new_backup_dir)
                
                # Try to create the directory if it doesn't exist
                if not os.path.exists(new_backup_dir):
                    try:
                        os.makedirs(new_backup_dir, exist_ok=True)
                        messages.success(request, _('Created new backup directory: {}').format(new_backup_dir))
                    except Exception as e:
                        messages.error(request, _('Failed to create backup directory: {}').format(str(e)))
                        return redirect('admin:backup_config')
                
                # Check if directory is writable
                if not os.access(new_backup_dir, os.W_OK):
                    messages.error(request, _('Directory is not writable: {}').format(new_backup_dir))
                    return redirect('admin:backup_config')
                
                # Update configuration
                if set_backup_path(new_backup_dir):
                    messages.success(request, _('Backup directory updated to: {}').format(new_backup_dir))
                    backup_directory = new_backup_dir
                else:
                    messages.error(request, _('Failed to save backup configuration'))
            
            # Update Git backup settings
            git_enabled = 'git_enabled' in request.POST
            git_repo = request.POST.get('git_repo', '').strip()
            git_branch = request.POST.get('git_branch', '').strip() or 'main'
            git_username = request.POST.get('git_username', '').strip()
            
            # Validate repository URL if enabling
            if git_enabled and not git_repo:
                messages.error(request, _('Git repository URL is required when enabling Git backups'))
            else:
                # Update Git configuration
                if configure_git_backup(
                    enabled=git_enabled,
                    repo=git_repo,
                    branch=git_branch,
                    username=git_username
                ):
                    status = _('enabled') if git_enabled else _('disabled')
                    messages.success(request, _('Git backup {} successfully').format(status))
                else:
                    messages.error(request, _('Failed to save Git backup configuration'))
            
            # Refresh configuration
            config = load_config()
            git_config = get_backup_git_repo() or {}
            
            context.update({
                'backup_directory': backup_directory,
                'backup_dir_writable': os.access(backup_directory, os.W_OK) if os.path.exists(backup_directory) else False,
                'git_backup_enabled': git_config.get('enabled', False),
                'git_repo': git_config.get('repository', ''),
                'git_branch': git_config.get('branch', 'main'),
                'git_username': git_config.get('username', ''),
                'backup_locations': config.get('backup_locations', []),
            })
            
    return render(request, 'admin/backup_config.html', context)