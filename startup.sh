#!/bin/bash
# Root level startup script
# This script runs during the deployment process
# and ensures the correct database is used

echo "========================================"
echo "DEPLOYMENT RESTORATION SCRIPT STARTING"
echo "========================================"

echo "Current directory: $(pwd)"
echo "Current date and time: $(date)"

# Deployment directory where backup data is stored
DEPLOYMENT_DIR="./deployment"
mkdir -p "$DEPLOYMENT_DIR"

echo "Checking for deployment backups in $DEPLOYMENT_DIR..."

# List all files in deployment directory for debugging
echo "Files in deployment directory:"
ls -la "$DEPLOYMENT_DIR"

# Set marker flag for deployment environment
echo "$(date) - Deployment startup script executed" > "$DEPLOYMENT_DIR/DEPLOYMENT_IN_PROGRESS"

# Check if we have a deployment backup
if [ -f "$DEPLOYMENT_DIR/deployment_db.sqlite" ]; then
    echo "✅ FOUND DEPLOYMENT SQLITE BACKUP!"
    echo "File details:"
    ls -la "$DEPLOYMENT_DIR/deployment_db.sqlite"
    echo "File size: $(stat -c %s $DEPLOYMENT_DIR/deployment_db.sqlite) bytes"
    echo "Last modified: $(stat -c %y $DEPLOYMENT_DIR/deployment_db.sqlite)"
    
    echo "Creating marker file to indicate production environment..."
    echo "$(date) - Deployment environment with SQLite backup detected" > "$DEPLOYMENT_DIR/IS_PRODUCTION_ENVIRONMENT"
    chmod 644 "$DEPLOYMENT_DIR/IS_PRODUCTION_ENVIRONMENT"
    
    # Also check for the database location
    DB_PATH="./smorasfotball/db.sqlite3"
    if [ -f "$DB_PATH" ]; then
        echo "Current database exists at $DB_PATH"
        echo "Current database size: $(stat -c %s $DB_PATH) bytes"
        
        # Create a backup of current DB just in case
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        cp "$DB_PATH" "${DB_PATH}.${TIMESTAMP}.pre_deploy"
        echo "Created backup of current database at ${DB_PATH}.${TIMESTAMP}.pre_deploy"
    else
        echo "No current database found at $DB_PATH"
    fi
    
    # Force deployment backup restoration by copying directly
    echo "⚠️ FORCING DEPLOYMENT DATABASE RESTORATION..."
    BACKUP_SIZE=$(stat -c %s "$DEPLOYMENT_DIR/deployment_db.sqlite")
    if [ "$BACKUP_SIZE" -gt 1000 ]; then
        # Make sure parent directory exists
        mkdir -p $(dirname "$DB_PATH")
        
        # Copy the backup directly to the database location
        cp "$DEPLOYMENT_DIR/deployment_db.sqlite" "$DB_PATH"
        chmod 644 "$DB_PATH"
        
        # Verify the copy worked
        if [ -f "$DB_PATH" ]; then
            COPY_SIZE=$(stat -c %s "$DB_PATH")
            if [ "$COPY_SIZE" -eq "$BACKUP_SIZE" ]; then
                echo "✅ DATABASE SUCCESSFULLY RESTORED! ($COPY_SIZE bytes)"
            else
                echo "⚠️ WARNING: Size mismatch after copy! Backup: $BACKUP_SIZE, Copy: $COPY_SIZE bytes"
            fi
        else
            echo "❌ ERROR: Copy failed - destination file doesn't exist!"
        fi
    else
        echo "❌ ERROR: Backup file is too small ($BACKUP_SIZE bytes), might be corrupted!"
    fi
    
    # Also try to use the Django management command method as a backup approach
    echo "Also trying Django management command approach..."
    cd smorasfotball
    python manage.py deployment_backup --restore || {
        echo "Django management command failed, but direct file copy should have worked"
    }
    cd ..
elif [ -f "$DEPLOYMENT_DIR/deployment_db.json" ]; then
    echo "✅ FOUND DEPLOYMENT JSON BACKUP!"
    echo "File details:"
    ls -la "$DEPLOYMENT_DIR/deployment_db.json"
    echo "File size: $(stat -c %s $DEPLOYMENT_DIR/deployment_db.json) bytes"
    echo "Last modified: $(stat -c %y $DEPLOYMENT_DIR/deployment_db.json)"
    
    echo "Creating marker file to indicate production environment..."
    echo "$(date) - Deployment environment with JSON backup detected" > "$DEPLOYMENT_DIR/IS_PRODUCTION_ENVIRONMENT"
    chmod 644 "$DEPLOYMENT_DIR/IS_PRODUCTION_ENVIRONMENT"
    
    # Use the Django command for JSON restoration
    echo "Will restore from JSON backup using Django command..."
    cd smorasfotball
    python manage.py deployment_backup --restore || {
        echo "Django management command failed, trying direct loaddata..."
        python manage.py loaddata "../$DEPLOYMENT_DIR/deployment_db.json" || {
            echo "❌ ERROR: Both restoration methods failed!"
        }
    }
    cd ..
else
    echo "⚠️ NO DEPLOYMENT BACKUPS FOUND! Will use fresh database."
    
    # Check if we have any backup files at all with pattern matching
    BACKUP_FILES=$(find "$DEPLOYMENT_DIR" -name "*deployment*.sqlite" -o -name "*production*.sqlite" 2>/dev/null)
    
    if [ ! -z "$BACKUP_FILES" ]; then
        echo "Found alternative backup files:"
        echo "$BACKUP_FILES"
        
        # Find the newest backup file
        NEWEST_BACKUP=$(find "$DEPLOYMENT_DIR" -name "*deployment*.sqlite" -o -name "*production*.sqlite" -type f -printf "%T@ %p\n" 2>/dev/null | sort -nr | head -1 | awk '{print $2}')
        
        if [ ! -z "$NEWEST_BACKUP" ]; then
            echo "Using newest alternative backup: $NEWEST_BACKUP"
            # Copy to the standard deployment backup location
            cp "$NEWEST_BACKUP" "$DEPLOYMENT_DIR/deployment_db.sqlite"
            chmod 644 "$DEPLOYMENT_DIR/deployment_db.sqlite"
            echo "Created standard deployment backup from alternative source"
            
            # Restart this script to use the newly created backup
            echo "Restarting script to use new backup..."
            exec "$0"
        fi
    fi
fi

echo "========================================"
echo "DEPLOYMENT RESTORATION SCRIPT COMPLETED"
echo "========================================"

# Continue with normal application startup
echo "Starting normal application processes..."
cd smorasfotball
./startup.sh