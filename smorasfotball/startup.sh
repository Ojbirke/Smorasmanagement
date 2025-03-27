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
    # Find the latest .sqlite3 backup (if using SQLite)
    LATEST_SQLITE=$(ls -t $PERSISTENT_BACKUP_DIR/*.sqlite3 2>/dev/null | head -1)
    
    # Find the latest .json backup
    LATEST_JSON=$(ls -t $PERSISTENT_BACKUP_DIR/*.json 2>/dev/null | head -1)
    
    # Determine which backup to use based on database engine
    if [ -f "db.sqlite3" ] && [ ! -z "$LATEST_SQLITE" ]; then
        LATEST_BACKUP=$LATEST_SQLITE
        BACKUP_TYPE="sqlite"
    elif [ ! -z "$LATEST_JSON" ]; then
        LATEST_BACKUP=$LATEST_JSON
        BACKUP_TYPE="json"
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
        else
            echo "Restoring from JSON backup..."
            # Load the backup data
            python manage.py loaddata "$LATEST_BACKUP"
            echo "JSON data restored from backup"
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

# Output success message
echo "Startup script completed."
#!/bin/bash
# Create backup directory if it doesn't exist
mkdir -p ../persistent_backups

# Run persistent backup before startup
python manage.py persistent_backup --name "pre_deploy"

# Start the application
gunicorn --bind 0.0.0.0:5000 smorasfotball.wsgi:application
