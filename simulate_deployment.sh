#!/bin/bash
# Simulate Deployment Script
# This script simulates a deployment process to test backup and restore procedures

set -e # Exit on error
echo "Simulating a deployment process to test backup and restore..."

# Step 1: Run the pre-deploy script to create backups
echo "Step 1: Running pre-deployment tasks..."
bash pre_deploy.sh

# Step 2: Verify that the backups were created
echo "Step 2: Verifying backup creation..."
ls -l deployment/

# Step 3: Simulate a deployment by completely removing the database
echo "Step 3: Simulating deployment by removing database..."
find smorasfotball -name "db.sqlite3" -exec rm {} \;
echo "Database removed. This simulates a fresh deployment."

# Step 4: Run database migrations to create a fresh empty database
echo "Step 4: Creating a fresh empty database..."
cd smorasfotball
python manage.py migrate
cd ..

# Step 5: Verify that the database is empty
echo "Step 5: Verifying database is empty..."
python -c "
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
sys.path.append('smorasfotball')
django.setup()
from django.contrib.auth.models import User
from teammanager.models import Team, Player
print(f'Users: {User.objects.count()}, Teams: {Team.objects.count()}, Players: {Player.objects.count()}')
"

# Step 6: Run the auto-restore script
echo "Step 6: Running auto-restore script..."
python auto_restore_after_deploy.py

# Step 7: Verify database was restored
echo "Step 7: Verifying database restoration..."
python -c "
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
sys.path.append('smorasfotball')
django.setup()
from django.contrib.auth.models import User
from teammanager.models import Team, Player
print(f'Users: {User.objects.count()}, Teams: {Team.objects.count()}, Players: {Player.objects.count()}')
"

echo "Deployment simulation completed."
echo "If the counts in Step 7 match your expected database content, the backup and restore process is working."
echo "If the counts are zero or incorrect, there may be issues with the backup or restore process."