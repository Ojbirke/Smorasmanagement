#!/usr/bin/env python
"""
PostgreSQL Backup Utility

This script creates a backup of the PostgreSQL database for the Smørås Fotball application.
It performs the following steps:
1. Verifies PostgreSQL is properly configured
2. Dumps all data using Django's dumpdata management command
3. Creates SQL backups using pg_dump if available
4. Stores backups in multiple locations for redundancy

Usage:
    python postgres_backup.py [--deployment]

Options:
    --deployment    If specified, creates a backup in the deployment directory
                   for redeployment purposes.
"""

import os
import sys
import time
import shutil
import argparse
import datetime
import subprocess
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smorasfotball.settings")
django.setup()

from django.core.management import call_command
from django.db import connections
from django.conf import settings

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Create PostgreSQL database backups")
    parser.add_argument('--deployment', action='store_true', 
                      help='Create a backup for deployment purposes')
    parser.add_argument('--json-only', action='store_true',
                      help='Create only JSON backup (no SQL dump)')
    parser.add_argument('--sql-only', action='store_true',
                      help='Create only SQL backup (no JSON export)')
    parser.add_argument('--output-dir', 
                      help='Custom output directory for backups')
    return parser.parse_args()

def is_postgres_configured():
    """Check if PostgreSQL is properly configured"""
    if 'DATABASE_URL' not in os.environ:
        print("ERROR: DATABASE_URL environment variable not set.")
        return False
    
    try:
        connection = connections['default']
        connection.ensure_connection()
        if 'postgresql' not in connection.vendor:
            print(f"ERROR: Default database is not PostgreSQL. Found: {connection.vendor}")
            return False
        return True
    except Exception as e:
        print(f"ERROR: Could not connect to PostgreSQL database: {e}")
        return False

def get_backup_directories(is_deployment=False):
    """Get backup directories based on backup type"""
    from backup_config import get_backup_path, load_config
    
    # Get the external backup path (outside repository)
    backup_dirs = [get_backup_path()]
    
    # Add project-local backups too for redundancy
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Add persistent_backups for redundancy
    backup_dirs.append(os.path.join(base_dir, 'persistent_backups'))
    
    # Regular app backups
    backup_dirs.append(os.path.join(os.path.dirname(__file__), 'backups'))
    
    # Add deployment backup location if requested
    if is_deployment:
        backup_dirs.append(os.path.join(base_dir, 'deployment'))
    
    # Load additional configured backup locations
    config = load_config()
    for location in config.get('backup_locations', []):
        if location.get('enabled', True):
            path = location.get('path')
            if path and path not in backup_dirs:
                # Handle relative paths
                if not os.path.isabs(path):
                    path = os.path.join(base_dir, path)
                backup_dirs.append(path)
    
    # Create directories if they don't exist
    for directory in backup_dirs:
        os.makedirs(directory, exist_ok=True)
    
    # Log all backup locations
    print(f"Using {len(backup_dirs)} backup locations:")
    for i, directory in enumerate(backup_dirs, 1):
        print(f"  {i}. {directory}")
    
    return backup_dirs

def create_json_backup(backup_dirs, timestamp):
    """Create Django JSON backup using dumpdata"""
    backup_files = []
    
    for backup_dir in backup_dirs:
        backup_file = os.path.join(backup_dir, f'backup_postgres_{timestamp}.json')
        
        print(f"Creating JSON backup: {backup_file}")
        try:
            call_command('dumpdata', '--exclude=contenttypes', '--exclude=auth.permission', 
                         '--indent=2', output=backup_file)
            backup_files.append(backup_file)
            print(f"JSON backup created: {backup_file}")
        except Exception as e:
            print(f"Error creating JSON backup: {e}")
    
    return backup_files

def create_pg_dump_backup(backup_dirs, timestamp):
    """Create raw PostgreSQL backup using pg_dump if available"""
    backup_files = []
    
    # Check if pg_dump is available
    try:
        subprocess.run(['pg_dump', '--version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("pg_dump not available, skipping SQL backup")
        return backup_files
    
    # Extract database connection parameters from DATABASE_URL
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL not set, skipping SQL backup")
        return backup_files
    
    for backup_dir in backup_dirs:
        backup_file = os.path.join(backup_dir, f'backup_postgres_{timestamp}.sql')
        
        print(f"Creating SQL backup: {backup_file}")
        try:
            command = [
                'pg_dump',
                '--dbname', db_url,
                '--format', 'plain',
                '--file', backup_file
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode == 0:
                backup_files.append(backup_file)
                print(f"SQL backup created: {backup_file}")
            else:
                print(f"Error creating SQL backup: {result.stderr}")
        except Exception as e:
            print(f"Error running pg_dump: {e}")
    
    return backup_files

def cleanup_old_backups(backup_dirs, max_backups=5):
    """Remove old backups to save space"""
    for backup_dir in backup_dirs:
        # Get all JSON backups
        json_backups = [f for f in os.listdir(backup_dir) 
                       if f.startswith('backup_postgres_') and f.endswith('.json')]
        
        # Get all SQL backups
        sql_backups = [f for f in os.listdir(backup_dir) 
                      if f.startswith('backup_postgres_') and f.endswith('.sql')]
        
        # Sort by name (which includes timestamp)
        json_backups.sort(reverse=True)
        sql_backups.sort(reverse=True)
        
        # Remove excess JSON backups
        for old_backup in json_backups[max_backups:]:
            try:
                os.remove(os.path.join(backup_dir, old_backup))
                print(f"Removed old JSON backup: {old_backup}")
            except Exception as e:
                print(f"Failed to remove old backup {old_backup}: {e}")
        
        # Remove excess SQL backups
        for old_backup in sql_backups[max_backups:]:
            try:
                os.remove(os.path.join(backup_dir, old_backup))
                print(f"Removed old SQL backup: {old_backup}")
            except Exception as e:
                print(f"Failed to remove old backup {old_backup}: {e}")

def main():
    """Main backup function"""
    args = parse_args()
    
    print("\n" + "=" * 80)
    print("POSTGRESQL BACKUP UTILITY".center(80))
    print("=" * 80)
    
    # 1. Verify PostgreSQL is configured
    if not is_postgres_configured():
        print("PostgreSQL database is not properly configured. Aborting backup.")
        sys.exit(1)
    
    # 2. Generate timestamp for backup files
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 3. Determine backup directories
    backup_dirs = []
    
    # Handle custom output directory if specified
    if hasattr(args, 'output_dir') and args.output_dir:
        output_dir = args.output_dir
        # Expand user directory if path starts with ~
        if output_dir.startswith('~'):
            output_dir = os.path.expanduser(output_dir)
        # Create the directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        backup_dirs.append(output_dir)
        print(f"Using custom output directory: {output_dir}")
    else:
        # Use standard backup directories
        backup_dirs = get_backup_directories(is_deployment=args.deployment)
    
    # Track which backups were created
    json_backups = []
    sql_backups = []
    
    # 4. Create JSON backups (if not sql_only)
    if not hasattr(args, 'sql_only') or not args.sql_only:
        json_backups = create_json_backup(backup_dirs, timestamp)
    else:
        print("Skipping JSON backup creation (--sql-only specified).")
    
    # 5. Create SQL backups with pg_dump (if not json_only)
    if not hasattr(args, 'json_only') or not args.json_only:
        sql_backups = create_pg_dump_backup(backup_dirs, timestamp)
    else:
        print("Skipping SQL backup creation (--json-only specified).")
    
    # 6. Clean up old backups
    cleanup_old_backups(backup_dirs)
    
    # 7. Report results
    print("\n" + "=" * 80)
    print("BACKUP SUMMARY".center(80))
    print("=" * 80)
    
    if json_backups:
        print("\nJSON Backups:")
        for backup in json_backups:
            print(f"  - {backup}")
    
    if sql_backups:
        print("\nSQL Backups:")
        for backup in sql_backups:
            print(f"  - {backup}")
    
    if not json_backups and not sql_backups:
        print("\nNo backups were created successfully.")
        sys.exit(1)
    
    print("\nBackup completed successfully.")
    
    # 8. Special deployment message
    if args.deployment:
        print("\n" + "=" * 80)
        print("DEPLOYMENT BACKUP CREATED".center(80))
        print("This backup will be used for restoration after redeployment.".center(80))
        print("=" * 80)

if __name__ == "__main__":
    main()