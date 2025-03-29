import os
import sys
import datetime
import subprocess
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from postgres_backup import main as backup_main

class Command(BaseCommand):
    help = 'Create a backup of the PostgreSQL database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--deployment',
            action='store_true',
            help='Create a backup for deployment (stored in deployment directory)',
        )
        
        parser.add_argument(
            '--json-only',
            action='store_true',
            help='Create only JSON backup (no SQL dump)',
        )
        
        parser.add_argument(
            '--sql-only',
            action='store_true',
            help='Create only SQL backup (no JSON export)',
        )
        
        parser.add_argument(
            '--output-dir',
            help='Custom output directory for backups',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating PostgreSQL database backup...'))
        
        # Check if PostgreSQL is configured
        db_settings = settings.DATABASES.get('default', {})
        db_engine = db_settings.get('ENGINE', '')
        
        if 'postgresql' not in db_engine:
            self.stdout.write(self.style.ERROR(
                f'PostgreSQL is not configured. Current engine: {db_engine}'
            ))
            return
        
        # Pass arguments to the main backup function
        sys.argv = ['postgres_backup.py']
        
        if options['deployment']:
            sys.argv.append('--deployment')
        
        if options['json_only']:
            sys.argv.append('--json-only')
        
        if options['sql_only']:
            sys.argv.append('--sql-only')
        
        if options['output_dir']:
            sys.argv.extend(['--output-dir', options['output_dir']])
        
        # Call the main backup function
        self.stdout.write('Calling postgres_backup.py...')
        backup_main()
        self.stdout.write(self.style.SUCCESS('PostgreSQL backup completed.'))