import os
import glob
import re
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Cleans up excess backups, keeping only the latest N backups of each type'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep',
            type=int,
            default=2,
            help='Number of backups to keep for each type (default: 2)',
        )
        parser.add_argument(
            '--force-cleanup',
            action='store_true',
            help='Force cleanup of all backup types',
        )

    def clean_old_backups(self, backup_dir, prefix, keep=2):
        """
        Clean old backups, keeping only the specified number of most recent ones for a given prefix
        """
        # List all backup files of this type
        json_pattern = os.path.join(backup_dir, f'backup_{prefix}_*.json')
        sqlite_pattern = os.path.join(backup_dir, f'backup_{prefix}_*.sqlite3')
        
        # Get list of files for each type
        json_files = glob.glob(json_pattern)
        sqlite_files = glob.glob(sqlite_pattern)
        
        # Get timestamps for better matching between JSON and SQLite files
        json_timestamps = {}
        sqlite_timestamps = {}
        
        # Extract timestamps from JSON filenames
        pattern = re.compile(f'backup_{prefix}_([0-9]+).json')
        for file_path in json_files:
            filename = os.path.basename(file_path)
            match = pattern.match(filename)
            if match:
                timestamp = match.group(1)
                json_timestamps[timestamp] = file_path
        
        # Extract timestamps from SQLite filenames
        pattern = re.compile(f'backup_{prefix}_([0-9]+).sqlite3')
        for file_path in sqlite_files:
            filename = os.path.basename(file_path)
            match = pattern.match(filename)
            if match:
                timestamp = match.group(1)
                sqlite_timestamps[timestamp] = file_path
        
        # Get all unique timestamps
        all_timestamps = list(set(list(json_timestamps.keys()) + list(sqlite_timestamps.keys())))
        # Sort timestamps in descending order (newest first)
        all_timestamps.sort(reverse=True)
        
        # Keep only the most recent 'keep' timestamps
        timestamps_to_remove = all_timestamps[keep:]
        
        # Remove the excess files
        for timestamp in timestamps_to_remove:
            # Remove JSON file if it exists
            if timestamp in json_timestamps:
                try:
                    os.remove(json_timestamps[timestamp])
                    self.stdout.write(f"Removed old JSON backup: {os.path.basename(json_timestamps[timestamp])}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not remove {json_timestamps[timestamp]}: {str(e)}"))
            
            # Remove SQLite file if it exists
            if timestamp in sqlite_timestamps:
                try:
                    os.remove(sqlite_timestamps[timestamp])
                    self.stdout.write(f"Removed old SQLite backup: {os.path.basename(sqlite_timestamps[timestamp])}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not remove {sqlite_timestamps[timestamp]}: {str(e)}"))

    def handle(self, *args, **options):
        # Get persistent backup directory (parent directory of the project)
        persistent_backup_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'persistent_backups')
        
        # Check if directory exists
        if not os.path.exists(persistent_backup_dir):
            self.stdout.write(self.style.WARNING(f"Backup directory does not exist: {persistent_backup_dir}"))
            return
        
        keep = options.get('keep', 2)
        force_cleanup = options.get('force_cleanup', False)
        
        # Clean up different types of backups
        backup_types = ['auto_startup', 'auto_shutdown']
        
        self.stdout.write(f"Cleaning up backups, keeping the latest {keep} of each type...")
        
        for backup_type in backup_types:
            self.clean_old_backups(persistent_backup_dir, backup_type, keep=keep)
            
        # Also clean up manual backups
        manual_pattern = os.path.join(persistent_backup_dir, 'backup_20*.json')
        manual_files = glob.glob(manual_pattern)
        
        # Extract timestamps for better matching
        manual_json_files = {}
        manual_sqlite_files = {}
        timestamp_pattern = re.compile(r'backup_([0-9_]+)\.json')
        
        # Get all JSON files with timestamps
        for file_path in manual_files:
            filename = os.path.basename(file_path)
            match = timestamp_pattern.match(filename)
            if match and 'auto_' not in filename:  # Exclude auto backups
                timestamp = match.group(1)
                manual_json_files[timestamp] = file_path
        
        # Get all corresponding SQLite files
        for timestamp in manual_json_files:
            sqlite_path = manual_json_files[timestamp].replace('.json', '.sqlite3')
            if os.path.exists(sqlite_path):
                manual_sqlite_files[timestamp] = sqlite_path
        
        # If there are more than 5 manual backups, remove the oldest ones
        manual_keep = 3
        timestamps = list(manual_json_files.keys())
        timestamps.sort(reverse=True)  # Sort newest first
        
        if len(timestamps) > manual_keep:
            self.stdout.write(f"Cleaning up manual backups, keeping the latest {manual_keep}...")
            for timestamp in timestamps[manual_keep:]:
                # Remove JSON file
                try:
                    os.remove(manual_json_files[timestamp])
                    self.stdout.write(f"Removed old manual JSON backup: {os.path.basename(manual_json_files[timestamp])}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not remove {manual_json_files[timestamp]}: {str(e)}"))
                
                # Remove SQLite file if it exists
                if timestamp in manual_sqlite_files:
                    try:
                        os.remove(manual_sqlite_files[timestamp])
                        self.stdout.write(f"Removed old manual SQLite backup: {os.path.basename(manual_sqlite_files[timestamp])}")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Could not remove {manual_sqlite_files[timestamp]}: {str(e)}"))
        
        # After the cleanup, check if we still have orphaned files
        if force_cleanup:
            self.stdout.write("Looking for orphaned files...")
            all_files = glob.glob(os.path.join(persistent_backup_dir, "backup_*.sqlite3"))
            all_files.extend(glob.glob(os.path.join(persistent_backup_dir, "backup_*.json")))
            
            # Count files by prefix
            file_counts = {}
            for file_path in all_files:
                filename = os.path.basename(file_path)
                if "_auto_" in filename:
                    prefix = 'auto_' + filename.split('_auto_')[1].split('_')[0]
                    if prefix not in file_counts:
                        file_counts[prefix] = []
                    file_counts[prefix].append(file_path)
            
            # Check if any prefix has more than 2*keep files
            for prefix, files in file_counts.items():
                if len(files) > 2*keep:  # 2*keep because we have both .json and .sqlite3
                    self.stdout.write(f"Found {len(files)} files for {prefix}, cleaning up...")
                    self.clean_old_backups(persistent_backup_dir, prefix, keep=keep)
        
        self.stdout.write(self.style.SUCCESS("Backup cleanup completed"))