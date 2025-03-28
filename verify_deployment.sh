#!/bin/bash
# Verify Deployment Environment
# This script checks if the deployment environment is properly configured
# and provides information about the current state

echo "========================================================"
echo "DEPLOYMENT ENVIRONMENT VERIFICATION"
echo "========================================================"
echo "Current directory: $(pwd)"
echo "Current time: $(date)"
echo "Deployment directory: $(pwd)/deployment"

# Check if deployment directory exists and what's in it
if [ -d "deployment" ]; then
    echo "✅ Deployment directory exists"
    
    # Check for backup files
    SQLITE_BACKUP=$(find deployment -name "deployment_db.sqlite" | head -1)
    JSON_BACKUP=$(find deployment -name "deployment_db.json" | head -1)
    
    if [ -n "$SQLITE_BACKUP" ]; then
        SQLITE_SIZE=$(stat -c%s "$SQLITE_BACKUP")
        echo "✅ SQLite backup exists: $SQLITE_BACKUP ($SQLITE_SIZE bytes)"
    else
        echo "❌ No SQLite backup found"
    fi
    
    if [ -n "$JSON_BACKUP" ]; then
        JSON_SIZE=$(stat -c%s "$JSON_BACKUP")
        echo "✅ JSON backup exists: $JSON_BACKUP ($JSON_SIZE bytes)"
    else
        echo "❌ No JSON backup found"
    fi
    
    # Check production markers
    if [ -f "deployment/IS_PRODUCTION_ENVIRONMENT" ]; then
        echo "✅ Production environment marker exists"
        echo "   $(cat deployment/IS_PRODUCTION_ENVIRONMENT)"
    else
        echo "❌ No production environment marker found"
    fi
    
    if [ -f "deployment/PERMANENT_PRODUCTION_MARKER" ]; then
        echo "✅ Permanent production marker exists"
        echo "   $(cat deployment/PERMANENT_PRODUCTION_MARKER)"
    else
        echo "❌ No permanent production marker found"
    fi
    
    # Count backup files
    SQLITE_BACKUPS=$(find deployment -name "*.sqlite" | wc -l)
    JSON_BACKUPS=$(find deployment -name "*.json" | wc -l)
    
    echo "Total SQLite backups: $SQLITE_BACKUPS"
    echo "Total JSON backups: $JSON_BACKUPS"
    
else
    echo "❌ Deployment directory does not exist"
fi

# Check if the app is in a valid state
cd smorasfotball

echo "========================================================"
echo "DATABASE INFORMATION"
echo "========================================================"
# Get Django database info
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from django.db import connections
from django.contrib.auth.models import User
from teammanager.models import Team, Player, Match

# Print database info
db_settings = connections['default'].settings_dict
print(f'Engine: {db_settings[\"ENGINE\"]}')
print(f'Name: {db_settings[\"NAME\"]}')

# Print model counts
print(f'\\nModel counts:')
print(f'Users: {User.objects.count()}')
print(f'Teams: {Team.objects.count()}')
print(f'Players: {Player.objects.count()}')
print(f'Matches: {Match.objects.count()}')

# Print some details about teams if they exist
if Team.objects.exists():
    print(f'\\nTeam details:')
    for team in Team.objects.all():
        print(f'- {team.name} (ID: {team.id})')
        
# Print some details about recent users if they exist
if User.objects.exists():
    print(f'\\nUser details (non-superusers):')
    for user in User.objects.filter(is_superuser=False)[:5]:
        print(f'- {user.username} (ID: {user.id})')
" || echo "❌ Failed to get database information"

echo "========================================================"
echo "VERIFICATION SUMMARY"
echo "========================================================"
# Determine overall status
if [ -f "../deployment/PERMANENT_PRODUCTION_MARKER" ] && [ -f "../deployment/deployment_db.sqlite" ]; then
    echo "✅ DEPLOYMENT ENVIRONMENT CONFIGURED CORRECTLY"
    echo "   Your data will be preserved across deployments"
else
    echo "❌ DEPLOYMENT ENVIRONMENT NEEDS CONFIGURATION"
    echo "   Run ./mark_production.sh to configure properly"
fi

cd ..