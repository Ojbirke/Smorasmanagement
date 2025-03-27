#!/bin/bash
# Startup script for smorasfotball application
# This script checks for persistent backups and restores them if needed

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"  # Change to the script directory

PERSISTENT_BACKUP_DIR="../persistent_backups"
LATEST_BACKUP=""

echo "Current directory: $(pwd)"
echo "Checking for persistent backups..."

# Create persistent backup directory if it doesn't exist
mkdir -p $PERSISTENT_BACKUP_DIR

# Check if persistent backups exist
if [ -d "$PERSISTENT_BACKUP_DIR" ]; then
    # Look for manual backups first (not containing auto_startup or auto_shutdown)
    # Use more precise patterns with quotes to ensure proper matching
    LATEST_MANUAL_SQLITE=$(find "$PERSISTENT_BACKUP_DIR" -name "backup_*.sqlite3" -type f -printf "%T@ %p\n" 2>/dev/null | sort -nr | awk '{print $2}' | grep -v "auto_startup\|auto_shutdown" | head -1)
    LATEST_MANUAL_JSON=$(find "$PERSISTENT_BACKUP_DIR" -name "backup_*.json" -type f -printf "%T@ %p\n" 2>/dev/null | sort -nr | awk '{print $2}' | grep -v "auto_startup\|auto_shutdown" | head -1)
    
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

# If we found a backup and the database is empty, restore it
if [ ! -z "$LATEST_BACKUP" ]; then
    echo "Found latest backup: $LATEST_BACKUP"
    
    # Check if database is empty
    TEAM_COUNT=$(python manage.py shell -c "from teammanager.models import Team; print(Team.objects.count())" 2>/dev/null)
    
    if [ "$?" -ne "0" ] || [ "$TEAM_COUNT" -eq "0" ]; then
        echo "Database appears to be empty or not initialized."
        
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
        echo "Database already contains data, skipping restore."
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
