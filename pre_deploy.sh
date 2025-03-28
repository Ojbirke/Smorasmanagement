#!/bin/bash

echo "Running pre-deploy script..."

# Ensure Django is installed
python -m pip install django pandas openpyxl reportlab

# Navigate to the Django project
cd smorasfotball

# Create deployment backup
echo "Creating deployment backup..."
python manage.py deployment_backup

# Verify backup contents
deployment_path="../deployment/deployment_db.json"
if [ -f "$deployment_path" ]; then
    size=$(stat -c%s "$deployment_path")
    echo "Deployment backup size: $size bytes"
    
    if [ $size -lt 100 ]; then
        echo "WARNING: Deployment backup is too small!"
    else
        echo "Deployment backup looks good - $size bytes."
        # Count records in backup
        team_count=$(grep -c "teammanager.team" "$deployment_path")
        player_count=$(grep -c "teammanager.player" "$deployment_path")
        user_count=$(grep -c "auth.user" "$deployment_path")
        echo "Deployment backup contains: $team_count teams, $player_count players, $user_count users"
    fi
else
    echo "WARNING: deployment_db.json not found!"
fi

# Sync with Git repository
echo "Syncing with Git repository..."
python manage.py sync_backups_with_repo --push

# Verify Git push was successful
if [ $? -eq 0 ]; then
    echo "Successfully pushed backups to Git."
else
    echo "WARNING: Git push may have failed. Continuing anyway."
fi

# Mark as production environment
echo "Marking as production environment..."
cd ..
bash mark_production.sh

echo "Pre-deployment tasks completed successfully."