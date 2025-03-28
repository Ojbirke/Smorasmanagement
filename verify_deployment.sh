#!/bin/bash
# Verify Deployment Script
# This script verifies that the database has been properly restored after deployment

echo "Verifying deployment status..."

# Navigate to Django project
cd smorasfotball

# Check if database has users
echo "Checking for users in database..."
USER_COUNT=$(python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
import django
django.setup()
from django.contrib.auth.models import User
print(User.objects.count())
")

echo "Found $USER_COUNT users in database"

if [ "$USER_COUNT" -eq "0" ]; then
    echo "WARNING: No users found in database! Deployment may have failed to restore data."
    echo "Attempting to restore from backup..."
    cd ..
    python auto_restore_after_deploy.py
    exit 1
else
    echo "Database appears to have users. Deployment verification passed."
fi

# Check for teams
echo "Checking for teams in database..."
TEAM_COUNT=$(python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
import django
django.setup()
from teammanager.models import Team
print(Team.objects.count())
")

echo "Found $TEAM_COUNT teams in database"

if [ "$TEAM_COUNT" -eq "0" ]; then
    echo "WARNING: No teams found in database! Deployment may have failed to restore team data."
    echo "Attempting to restore from backup..."
    cd ..
    python auto_restore_after_deploy.py
    exit 1
else
    echo "Database appears to have teams. Deployment verification passed."
fi

# Check for players
echo "Checking for players in database..."
PLAYER_COUNT=$(python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
import django
django.setup()
from teammanager.models import Player
print(Player.objects.count())
")

echo "Found $PLAYER_COUNT players in database"

if [ "$PLAYER_COUNT" -eq "0" ]; then
    echo "WARNING: No players found in database! Deployment may have failed to restore player data."
    echo "Attempting to restore from backup..."
    cd ..
    python auto_restore_after_deploy.py
    exit 1
else
    echo "Database appears to have players. Deployment verification passed."
fi

echo "Deployment verification completed successfully"
exit 0