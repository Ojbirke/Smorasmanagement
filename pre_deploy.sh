#!/bin/bash

echo "Running pre-deploy script..."

# Ensure Django is installed
python -m pip install django pandas openpyxl reportlab

# Navigate to the Django project
cd smorasfotball

# Check for production indicator
IS_PROD="../deployment/IS_PRODUCTION_ENVIRONMENT"
if [ -f "$IS_PROD" ]; then
    echo "This is a PRODUCTION environment."
    
    # Check if existing deployment backup exists and is valid
    deployment_path="../deployment/deployment_db.json"
    if [ -f "$deployment_path" ]; then
        size=$(stat -c%s "$deployment_path")
        echo "Existing deployment backup size: $size bytes"
        
        if [ $size -gt 100 ]; then
            # Count records in existing backup
            team_count=$(grep -c "teammanager.team" "$deployment_path")
            player_count=$(grep -c "teammanager.player" "$deployment_path")
            user_count=$(grep -c "auth.user" "$deployment_path")
            echo "Existing deployment backup contains: $team_count teams, $player_count players, $user_count users"
            
            # Make a timestamp backup of the existing deployment file
            timestamp=$(date +"%Y%m%d_%H%M%S")
            backup_path="../deployment/pre_deploy_backup_${timestamp}.json"
            echo "Creating safety backup of existing deployment file..."
            cp "$deployment_path" "$backup_path"
            echo "Safety backup created: $backup_path"
        fi
    fi
else
    echo "This is a DEVELOPMENT environment."
fi

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
        
        # If we're in production and have a safety backup, restore it
        if [ -f "$IS_PROD" ] && [ -f "$backup_path" ]; then
            echo "Restoring production deployment backup from safety copy..."
            cp "$backup_path" "$deployment_path"
            echo "Safety backup restored."
        fi
    else
        echo "Deployment backup looks good - $size bytes."
        # Count records in backup
        team_count=$(grep -c "teammanager.team" "$deployment_path")
        player_count=$(grep -c "teammanager.player" "$deployment_path")
        user_count=$(grep -c "auth.user" "$deployment_path")
        echo "Deployment backup contains: $team_count teams, $player_count players, $user_count users"
        
        # In production, verify the backup has the expected content
        if [ -f "$IS_PROD" ]; then
            # Simple test - make sure we have some reasonable number of records
            if [ $team_count -lt 1 ] || [ $player_count -lt 5 ] || [ $user_count -lt 1 ]; then
                echo "WARNING: Deployment backup seems suspiciously small for production!"
                
                # If we have a safety backup, restore it
                if [ -f "$backup_path" ]; then
                    echo "Restoring production deployment backup from safety copy..."
                    cp "$backup_path" "$deployment_path"
                    
                    # Verify restoration
                    team_count=$(grep -c "teammanager.team" "$deployment_path")
                    player_count=$(grep -c "teammanager.player" "$deployment_path")
                    user_count=$(grep -c "auth.user" "$deployment_path")
                    echo "Restored backup contains: $team_count teams, $player_count players, $user_count users"
                fi
            fi
        fi
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