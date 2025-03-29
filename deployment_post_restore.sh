#!/bin/bash
# Deployment Post-Restore Script
# This script is run after deployment to restore the database from Git

echo "Running post-deployment restore script..."

# Check if we're in a Git repository
if [ ! -d .git ]; then
    echo "Error: Not in a Git repository"
    exit 1
fi

# Ensure we have the latest code
echo "Pulling latest code..."
git pull origin main

# Run the auto-restore script
echo "Running auto-restore script..."
python auto_restore_after_deploy.py

# Check if restore was successful
if [ $? -eq 0 ]; then
    echo "Auto-restore completed successfully"
else
    echo "Auto-restore failed, will run database population script..."
    
    # Run migrations
    cd smorasfotball && python manage.py migrate
    
    # Recreate the superuser if needed
    cd .. && python recreate_superuser.py
    
    # Reset and populate the database with comprehensive data
    echo "Populating database with teams, players, matches and sessions..."
    cd smorasfotball && python reset_and_populate_db.py
    
    cd ..
fi

# Start the Django server
echo "Starting Django server..."
cd smorasfotball && python manage.py runserver 0.0.0.0:5000