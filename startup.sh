#!/bin/bash
# Startup script for handling deployment and database restoration
# This script runs automatically during deployment startup

echo "========================================================"
echo "DEPLOYMENT STARTUP DATABASE RESTORATION SYSTEM"
echo "========================================================"
echo "Current directory: $(pwd)"
echo "Current time: $(date)"
echo "Deployment directory: $(pwd)/deployment"

# Make sure the deployment directory exists
mkdir -p deployment

# Execute the database restoration command
cd smorasfotball

echo "First, trying to pull latest backups from repository..."
python manage.py sync_backups_with_repo --pull

echo "Now attempting database restoration from deployment backups..."
python manage.py deployment_backup --restore || {
    echo "Warning: Main deployment_backup restore failed. Trying direct restoration..."
    
    # If the management command fails, try direct file restoration
    # First check if we have direct SQLite file backup
    if [ -f "../deployment/deployment_db.sqlite" ]; then
        echo "Found deployment SQLite backup, attempting direct DB file replacement..."
        
        # Get the database path
        DB_PATH=$(python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from django.db import connections
print(connections['default'].settings_dict['NAME'])
")
        
        if [ -n "$DB_PATH" ]; then
            echo "Current database path: $DB_PATH"
            
            # Ensure parent directory exists
            mkdir -p $(dirname "$DB_PATH")
            
            # Make a backup of current DB if it exists
            if [ -f "$DB_PATH" ]; then
                cp "$DB_PATH" "${DB_PATH}.pre_restore.bak"
                echo "Backed up current database to ${DB_PATH}.pre_restore.bak"
            fi
            
            # Check the size of the deployment backup (it should be at least 20KB to be valid)
            BACKUP_SIZE=$(stat -c%s "../deployment/deployment_db.sqlite")
            if [ "$BACKUP_SIZE" -lt 20000 ]; then
                echo "⚠️ WARNING: Deployment backup file is suspiciously small ($BACKUP_SIZE bytes)"
                echo "Checking for other backup files in deployment directory..."
                
                # Look for alternative backup files
                LATEST_BACKUP=""
                LATEST_BACKUP_TIME=0
                for f in ../deployment/deployment_db.sqlite* ../deployment/backups/deployment_backup_*.sqlite; do
                    if [ -f "$f" ]; then
                        FILE_SIZE=$(stat -c%s "$f")
                        FILE_TIME=$(stat -c%Y "$f")
                        if [ "$FILE_SIZE" -gt 20000 ] && [ "$FILE_TIME" -gt "$LATEST_BACKUP_TIME" ]; then
                            LATEST_BACKUP="$f"
                            LATEST_BACKUP_TIME="$FILE_TIME"
                        fi
                    fi
                done
                
                if [ -n "$LATEST_BACKUP" ]; then
                    echo "Found better backup file: $LATEST_BACKUP ($(stat -c%s "$LATEST_BACKUP") bytes)"
                    echo "Using this file instead of the default deployment_db.sqlite"
                    cp "$LATEST_BACKUP" "$DB_PATH"
                else
                    echo "No better backup found, proceeding with original file despite small size"
                    cp "../deployment/deployment_db.sqlite" "$DB_PATH"
                fi
            else
                # Original file is good, proceed with it
                cp "../deployment/deployment_db.sqlite" "$DB_PATH"
            fi
            
            chmod 644 "$DB_PATH"
            echo "✅ Successfully restored database from deployment backup"
            
            # Run migrations to ensure schema is up to date
            python manage.py migrate --noinput
            echo "Ran migrations to ensure database schema is current"
        else
            echo "❌ ERROR: Couldn't determine database path"
        fi
    else
        # Look for any SQLite backup in the deployment directory with pattern matching
        echo "No standard deployment_db.sqlite file found. Searching for alternatives..."
        
        LATEST_BACKUP=""
        LATEST_BACKUP_TIME=0
        for f in ../deployment/deployment_backup_*.sqlite ../deployment/backups/deployment_backup_*.sqlite; do
            if [ -f "$f" ]; then
                FILE_SIZE=$(stat -c%s "$f")
                FILE_TIME=$(stat -c%Y "$f")
                if [ "$FILE_SIZE" -gt 20000 ] && [ "$FILE_TIME" -gt "$LATEST_BACKUP_TIME" ]; then
                    LATEST_BACKUP="$f"
                    LATEST_BACKUP_TIME="$FILE_TIME"
                fi
            fi
        done
        
        if [ -n "$LATEST_BACKUP" ]; then
            echo "Found backup file: $LATEST_BACKUP"
            
            # Get the database path
            DB_PATH=$(python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from django.db import connections
print(connections['default'].settings_dict['NAME'])
")
            
            if [ -n "$DB_PATH" ]; then
                # Ensure parent directory exists
                mkdir -p $(dirname "$DB_PATH")
                
                # Make a backup of current DB if it exists
                if [ -f "$DB_PATH" ]; then
                    cp "$DB_PATH" "${DB_PATH}.pre_restore.bak"
                    echo "Backed up current database to ${DB_PATH}.pre_restore.bak"
                fi
                
                # Copy the backup to the standard location and to the active database
                cp "$LATEST_BACKUP" "../deployment/deployment_db.sqlite"
                cp "$LATEST_BACKUP" "$DB_PATH"
                chmod 644 "$DB_PATH"
                echo "✅ Successfully restored database from alternative backup"
                
                # Run migrations to ensure schema is up to date
                python manage.py migrate --noinput
                echo "Ran migrations to ensure database schema is current"
            else
                echo "❌ ERROR: Couldn't determine database path"
            fi
        else
            echo "❌ ERROR: No SQLite backup found in deployment directory"
            
            # If we have a JSON backup, try to use that as a last resort
            if [ -f "../deployment/deployment_db.json" ]; then
                echo "Found JSON backup, attempting to load data from it..."
                
                # Get the database path and reset it first
                DB_PATH=$(python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from django.db import connections
print(connections['default'].settings_dict['NAME'])
")
                
                if [ -n "$DB_PATH" ]; then
                    # Ensure the database exists with proper schema
                    python manage.py migrate --noinput
                    
                    # Try to load the data
                    python manage.py loaddata "../deployment/deployment_db.json" && {
                        echo "✅ Successfully restored database from JSON backup"
                    } || {
                        echo "❌ ERROR: Failed to load data from JSON backup"
                    }
                else
                    echo "❌ ERROR: Couldn't determine database path"
                fi
            fi
        fi
    fi
}

echo "Performing final deployment checks..."

# Run migrations in case any database schema changes were needed
python manage.py migrate --noinput

# Verify deployment admin user exists
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='deployment_admin').exists() and not User.objects.filter(is_superuser=True).exists():
    print('Creating emergency admin user...')
    User.objects.create_superuser('emergency_admin', 'emergency@example.com', 'emergency123')
    print('✅ Created emergency admin user with username: emergency_admin and password: emergency123')
else:
    print('✅ Admin user exists, no need to create emergency admin')
"

echo "Deployment startup completed"
cd ..