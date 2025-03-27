#!/bin/bash
# Startup script for smorasfotball application
# This script checks for persistent backups and restores them if needed

echo "========================================"
echo "STARTING SMORASFOTBALL APPLICATION"
echo "========================================"
echo "Current date: $(date)"
echo "Current directory: $(pwd)"

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"  # Change to the script directory
echo "Changed to script directory: $DIR"

PERSISTENT_BACKUP_DIR="../persistent_backups"
DEPLOYMENT_DIR="../deployment"
LATEST_BACKUP=""
IS_DEPLOYMENT=false

echo "Looking for deployment-specific backups..."
# Check if deployment backups exist
if [ -f "$DEPLOYMENT_DIR/deployment_db.sqlite" ]; then
    echo "✅ Found SQLite deployment backup: $DEPLOYMENT_DIR/deployment_db.sqlite"
    echo "   Last modified: $(stat -c %y $DEPLOYMENT_DIR/deployment_db.sqlite)"
    echo "   Size: $(stat -c %s $DEPLOYMENT_DIR/deployment_db.sqlite) bytes"
fi

if [ -f "$DEPLOYMENT_DIR/deployment_db.json" ]; then
    echo "✅ Found JSON deployment backup: $DEPLOYMENT_DIR/deployment_db.json"
    echo "   Last modified: $(stat -c %y $DEPLOYMENT_DIR/deployment_db.json)"
    echo "   Size: $(stat -c %s $DEPLOYMENT_DIR/deployment_db.json) bytes"
fi

# Check if we are running in a deployment environment
# Deployment environments will have a special marker file or environment variable
if [ -f "$DEPLOYMENT_DIR/deployment_db.sqlite" ] || [ -f "$DEPLOYMENT_DIR/deployment_db.json" ]; then
    IS_DEPLOYMENT=true
    echo "DEPLOYMENT ENVIRONMENT DETECTED!"
fi

echo "Current directory: $(pwd)"
echo "Checking for persistent backups..."

# Create persistent backup directory if it doesn't exist
mkdir -p $PERSISTENT_BACKUP_DIR

# Check if persistent backups exist
if [ -d "$PERSISTENT_BACKUP_DIR" ]; then
    # Look for manual backups first (not containing auto_startup or auto_shutdown)
    # Use more precise patterns with quotes to ensure proper matching
    echo "Searching for manual backups in $PERSISTENT_BACKUP_DIR..."
    
    # First list all the backups for debugging
    echo "All available backups:"
    find "$PERSISTENT_BACKUP_DIR" \( -name "*.sqlite3" -o -name "*.json" \) -type f -printf "%T@ %p\n" | sort -nr | awk '{print $2}'
    
    LATEST_MANUAL_SQLITE=$(find "$PERSISTENT_BACKUP_DIR" -name "backup_*.sqlite3" -type f -printf "%T@ %p\n" 2>/dev/null | sort -nr | awk '{print $2}' | grep -v "auto_startup\|auto_shutdown" | head -1)
    LATEST_MANUAL_JSON=$(find "$PERSISTENT_BACKUP_DIR" -name "backup_*.json" -type f -printf "%T@ %p\n" 2>/dev/null | sort -nr | awk '{print $2}' | grep -v "auto_startup\|auto_shutdown" | head -1)
    
    echo "Latest manual SQLite backup found: $LATEST_MANUAL_SQLITE"
    echo "Latest manual JSON backup found: $LATEST_MANUAL_JSON"
    
    # If no manual backups exist, fall back to any backup including auto backups
    LATEST_AUTO_SQLITE=$(find "$PERSISTENT_BACKUP_DIR" -name "*.sqlite3" -type f -printf "%T@ %p\n" 2>/dev/null | sort -nr | awk '{print $2}' | head -1)
    LATEST_AUTO_JSON=$(find "$PERSISTENT_BACKUP_DIR" -name "*.json" -type f -printf "%T@ %p\n" 2>/dev/null | sort -nr | awk '{print $2}' | head -1)
    
    # Prioritize manual backups over auto backups
    if [ -f "db.sqlite3" ] && [ ! -z "$LATEST_MANUAL_SQLITE" ]; then
        LATEST_BACKUP=$LATEST_MANUAL_SQLITE
        BACKUP_TYPE="sqlite"
        echo "Found manual SQLite backup: $LATEST_BACKUP"
    elif [ ! -z "$LATEST_MANUAL_JSON" ]; then
        LATEST_BACKUP=$LATEST_MANUAL_JSON
        BACKUP_TYPE="json"
        echo "Found manual JSON backup: $LATEST_BACKUP"
    elif [ -f "db.sqlite3" ] && [ ! -z "$LATEST_AUTO_SQLITE" ]; then
        LATEST_BACKUP=$LATEST_AUTO_SQLITE
        BACKUP_TYPE="sqlite"
        echo "Found auto SQLite backup: $LATEST_BACKUP"
    elif [ ! -z "$LATEST_AUTO_JSON" ]; then
        LATEST_BACKUP=$LATEST_AUTO_JSON
        BACKUP_TYPE="json"
        echo "Found auto JSON backup: $LATEST_BACKUP"
    fi
fi

# First check if we're in a deployment environment and a deployment-specific backup exists
DEPLOYMENT_SQLITE="../deployment/deployment_db.sqlite"
DEPLOYMENT_JSON="../deployment/deployment_db.json"
PRODUCTION_MARKER="../deployment/IS_PRODUCTION_ENVIRONMENT"

# List all available backups for debugging
echo "DEBUG: Listing all files in deployment directory:"
ls -la "../deployment/"

if [ -f "$PRODUCTION_MARKER" ] || [ -f "$DEPLOYMENT_SQLITE" ] || [ -f "$DEPLOYMENT_JSON" ]; then
    echo "=========================================================="
    echo "CRITICAL: PRODUCTION ENVIRONMENT DETECTED"
    echo "=========================================================="
    echo "Timestamp: $(date)"
    
    if [ -f "$PRODUCTION_MARKER" ]; then
        echo "Production marker file found: $PRODUCTION_MARKER"
        cat "$PRODUCTION_MARKER"
    fi
    
    if [ -f "$DEPLOYMENT_SQLITE" ]; then
        echo "Found SQLite deployment-specific backup: $DEPLOYMENT_SQLITE"
        echo "  Last modified: $(stat -c %y $DEPLOYMENT_SQLITE)"
        echo "  File size: $(stat -c %s $DEPLOYMENT_SQLITE) bytes"
    fi
    
    if [ -f "$DEPLOYMENT_JSON" ]; then
        echo "Found JSON deployment-specific backup: $DEPLOYMENT_JSON"
        echo "  Last modified: $(stat -c %y $DEPLOYMENT_JSON)"
        echo "  File size: $(stat -c %s $DEPLOYMENT_JSON) bytes"
    fi
    
    echo "This confirms we're running in a PRODUCTION deployment environment"
    echo "RESTORING PRODUCTION DATABASE..."
    
    # Always run migrations first
    echo "Applying migrations..."
    python manage.py migrate
    
    # Make a copy of existing database if it exists (just in case)
    if [ -f "db.sqlite3" ]; then
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        cp "db.sqlite3" "db.sqlite3.${TIMESTAMP}.pre_restore"
        echo "Created safety copy of current database: db.sqlite3.${TIMESTAMP}.pre_restore"
    fi
    
    echo "RESTORING PRODUCTION DATABASE FROM DEPLOYMENT BACKUP..."
    # Try multiple restoration methods to ensure success
    
    # Method 1: Use our custom management command
    echo "Method 1: Using deployment_backup management command..."
    python manage.py deployment_backup --restore
    
    # Method 2: Direct file copy for SQLite (most reliable method)
    if [ -f "$DEPLOYMENT_SQLITE" ]; then
        echo "Method 2: Using direct SQLite file copy (most reliable)..."
        cp "$DEPLOYMENT_SQLITE" db.sqlite3
        chmod 644 db.sqlite3
        echo "SQLite backup applied directly via file copy"
    fi
    
    # Method 3: JSON restoration
    if [ -f "$DEPLOYMENT_JSON" ] && [ ! -f "$DEPLOYMENT_SQLITE" ]; then
        echo "Method 3: Using JSON restoration..."
        python manage.py flush --no-input
        python manage.py loaddata "$DEPLOYMENT_JSON"
        echo "JSON backup restored"
    fi
    
    # Verify restoration success
    python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from teammanager.models import Team, Player
from django.contrib.auth.models import User
print(f'Verification: Found {Team.objects.count()} teams, {Player.objects.count()} players, {User.objects.count()} users')
"
    
    echo "PRODUCTION database restore process completed"
    echo "=========================================================="
    
    # Run migrations again after restore to ensure database schema is current
    echo "Re-applying migrations post-restoration..."
    python manage.py migrate
    
    # Create a record of this restoration
    echo "$(date) - Production database restored during startup" >> "../deployment/restoration_log.txt"
    
    # Make another backup after restoration
    echo "Creating post-restoration backup..."
    python manage.py deployment_backup --name "post_restore_$(date +%Y%m%d_%H%M%S)" --format sqlite
    
    # Continue with normal startup process
fi

# If no deployment backup or we're not in deployment mode, continue with regular backup process
# Always restore from the most recent backup on redeployment
if [ ! -z "$LATEST_BACKUP" ]; then
    echo "Found latest backup: $LATEST_BACKUP"
    
    # Note: We're no longer checking if the database is empty
    # Instead, we always restore from the latest backup after redeployment
    # This ensures user changes persist across redeployments
    
    echo "Restoring from backup after redeployment..."
    
    # If we need to run migrations first
    echo "Applying migrations..."
    python manage.py migrate
    
    if [ "$BACKUP_TYPE" == "sqlite" ]; then
        echo "Restoring from SQLite backup..."
        # Make a copy of the backup to the db.sqlite3 file
        cp "$LATEST_BACKUP" db.sqlite3
        echo "SQLite database restored from backup"
        
        # Record which backup was used for diagnostic purposes
        BASENAME=$(basename "$LATEST_BACKUP")
        export LAST_RESTORED_BACKUP="$BASENAME"
        export LAST_RESTORE_TIME="$(date +'%Y-%m-%d %H:%M:%S')"
        echo "export LAST_RESTORED_BACKUP=\"$BASENAME\"" >> ../.env
        echo "export LAST_RESTORE_TIME=\"$(date +'%Y-%m-%d %H:%M:%S')\"" >> ../.env
        echo "Recorded restore of backup: $BASENAME at $(date +'%Y-%m-%d %H:%M:%S')"
    else
        echo "Restoring from JSON backup..."
        # Load the backup data
        python manage.py loaddata "$LATEST_BACKUP"
        echo "JSON data restored from backup"
        
        # Record which backup was used for diagnostic purposes
        BASENAME=$(basename "$LATEST_BACKUP")
        export LAST_RESTORED_BACKUP="$BASENAME"
        export LAST_RESTORE_TIME="$(date +'%Y-%m-%d %H:%M:%S')"
        echo "export LAST_RESTORED_BACKUP=\"$BASENAME\"" >> ../.env
        echo "export LAST_RESTORE_TIME=\"$(date +'%Y-%m-%d %H:%M:%S')\"" >> ../.env
        echo "Recorded restore of backup: $BASENAME at $(date +'%Y-%m-%d %H:%M:%S')"
    fi
else
    echo "No persistent backups found."
fi

# Run migrations regardless
python manage.py migrate

# Check if recreate_superuser.py exists in parent directory and run it
SUPERUSER_SCRIPT="../recreate_superuser.py"
if [ -f "$SUPERUSER_SCRIPT" ]; then
    echo "Running superuser recreation script..."
    # Run the superuser script in the current Django environment
    cd .. && python recreate_superuser.py && cd "$DIR"
else
    echo "Superuser recreation script not found at $SUPERUSER_SCRIPT"
fi

# Create backup before starting the application
mkdir -p ../persistent_backups
python manage.py persistent_backup --name "pre_deploy"

# Create a production backup if we're in deployment environment
if [ "$IS_DEPLOYMENT" = true ]; then
    echo "Creating production database backup in deployment environment..."
    
    # Get today's date for the backup name
    TODAY_DATE=$(date +"%Y%m%d")
    
    # Create both SQLite and JSON backups of the production database
    echo "Creating daily production SQLite backup..."
    python manage.py deployment_backup --name "production_${TODAY_DATE}" --format sqlite
    
    echo "Creating daily production JSON backup (for redundancy)..."
    python manage.py deployment_backup --name "production_${TODAY_DATE}" --format json
    
    echo "✅ Created fresh production database backups"
    
    # Clean up old production backups (keep only the 3 most recent)
    echo "Cleaning up old production backups..."
    find "../deployment" -name "deployment_backup_production_*.sqlite" -type f -printf "%T@ %p\n" | sort -n | head -n -3 | cut -d' ' -f2- | xargs -r rm
    find "../deployment" -name "deployment_backup_production_*.json" -type f -printf "%T@ %p\n" | sort -n | head -n -3 | cut -d' ' -f2- | xargs -r rm
    echo "Kept the 3 most recent production backups of each type"
fi

# Output success message
echo "========================================"
echo "Startup script completed successfully!"
echo "Database restoration status: SUCCESS"
if [ "$IS_DEPLOYMENT" = true ]; then
    echo "Environment: PRODUCTION DEPLOYMENT"
else
    echo "Environment: DEVELOPMENT"
fi
echo "========================================"

# Start the application if needed (handled by replit workflow)
# gunicorn --bind 0.0.0.0:5000 smorasfotball.wsgi:application
