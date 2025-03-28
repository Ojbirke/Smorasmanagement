#!/bin/bash
# Simulate Deployment Script
# This script simulates what happens during a Replit deployment
# by running the same steps in the same order

echo "========================================================"
echo "SIMULATING REPLIT DEPLOYMENT"
echo "========================================================"
echo "Current directory: $(pwd)"
echo "Current date and time: $(date)"

# Automatically continue since we're running a test
echo "Automatically continuing with simulation for testing purposes..."

# Create a backup of the current database for safety
DB_PATH="./smorasfotball/db.sqlite3"
if [ -f "$DB_PATH" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP="./smorasfotball/db.sqlite3.${TIMESTAMP}.pre_simulation"
    cp "$DB_PATH" "$BACKUP"
    echo "Created backup of current database at $BACKUP"
fi

echo "========================================================"
echo "STEP 1: Run pre_deploy.sh"
echo "========================================================"
# Run the pre-deployment script
chmod +x pre_deploy.sh
./pre_deploy.sh

echo "========================================================"
echo "STEP 2: Simulate deployment environment preparation"
echo "========================================================"
# Clear any existing database to simulate a fresh environment
if [ -f "$DB_PATH" ]; then
    rm "$DB_PATH"
    echo "Removed current database to simulate fresh deployment"
fi

# Run migrations to create a fresh database
cd smorasfotball
python manage.py migrate
cd ..
echo "Created fresh database with migrations"

echo "========================================================"
echo "STEP 3: Run startup.sh from root directory"
echo "========================================================"
# Run the startup script which should restore from deployment backups
chmod +x startup.sh
./startup.sh

echo "========================================================"
echo "STEP 4: Verify restoration"
echo "========================================================"
# Verify that the database has been restored properly
cd smorasfotball
python - << 'EOF'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from teammanager.models import Team, Player, Match
from django.contrib.auth.models import User
print('Database verification:')
print(f'- {User.objects.count()} users')
print(f'- {Team.objects.count()} teams')
print(f'- {Player.objects.count()} players')
print(f'- {Match.objects.count()} matches')
EOF
cd ..

echo "========================================================"
echo "DEPLOYMENT SIMULATION COMPLETED"
echo "========================================================"
echo "Original database backup: $BACKUP"
echo "You can restore this backup if needed."
echo "To do this: cp $BACKUP $DB_PATH"