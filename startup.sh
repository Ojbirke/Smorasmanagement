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
            
            # Copy the deployment backup to the active database location
            cp "../deployment/deployment_db.sqlite" "$DB_PATH"
            chmod 644 "$DB_PATH"
            echo "✅ Successfully restored database from deployment backup"
            
            # Run migrations to ensure schema is up to date
            python manage.py migrate --noinput
            echo "Ran migrations to ensure database schema is current"
        else
            echo "❌ ERROR: Couldn't determine database path"
        fi
    else
        echo "❌ ERROR: No SQLite backup found in deployment directory"
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