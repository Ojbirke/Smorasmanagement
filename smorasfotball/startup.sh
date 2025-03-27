#!/bin/bash
# Startup script for smorasfotball application
# This script checks for persistent backups and restores them if needed

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"  # Change to the script directory

PERSISTENT_BACKUP_DIR="../persistent_backups"
DEPLOYMENT_DIR="../deployment"
LATEST_BACKUP=""
IS_DEPLOYMENT=false

# Check if we are running in a deployment environment
# Deployment environments will have a special marker file or environment variable
if [ -f "$DEPLOYMENT_DIR/deployment_db.json" ]; then
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
DEPLOYMENT_BACKUP="../deployment/deployment_db.json"
if [ -f "$DEPLOYMENT_BACKUP" ]; then
    echo "Found deployment-specific backup: $DEPLOYMENT_BACKUP"
    echo "This indicates we're running in a deployment environment"
    
    # Check if database is empty
    TEAM_COUNT=$(python manage.py shell -c "from teammanager.models import Team; print(Team.objects.count())" 2>/dev/null)
    
    if [ "$?" -ne "0" ] || [ "$TEAM_COUNT" -eq "0" ]; then
        echo "Database appears to be empty in deployment environment. Loading deployment backup..."
        
        # If we need to run migrations first
        echo "Applying migrations..."
        python manage.py migrate
        
        echo "Restoring from deployment backup..."
        # Use our custom management command for deployment backup restore
        python manage.py deployment_backup --restore
        echo "Deployment database restored from backup"
        
        # Exit early with successful status
        exit 0
    fi
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

# Output success message
echo "Startup script completed."

# Start the application if needed (handled by replit workflow)
# gunicorn --bind 0.0.0.0:5000 smorasfotball.wsgi:application
