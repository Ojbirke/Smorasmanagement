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
    echo "Starting Django server..."
    cd smorasfotball && python manage.py runserver 0.0.0.0:5000
else
    echo "Auto-restore failed, starting Django server without restored data..."
    cd smorasfotball && python manage.py migrate && python manage.py runserver 0.0.0.0:5000
fi