#!/bin/bash
# Debug Deployment Restore Script
# This script helps diagnose issues with deployment database restoration

echo "========================================================"
echo "DEPLOYMENT DATABASE RESTORATION DIAGNOSTIC TOOL"
echo "========================================================"
echo "Current directory: $(pwd)"
echo "Current time: $(date)"
echo "Deployment directory: $(pwd)/deployment"

# Create a comprehensive diagnostic log
LOG_FILE="deployment_restore_debug_$(date +"%Y%m%d_%H%M%S").log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Creating diagnostic log: $LOG_FILE"

# Check if deployment directory exists and what's in it
echo "========================================================"
echo "DEPLOYMENT DIRECTORY STATUS"
echo "========================================================"
if [ -d "deployment" ]; then
    echo "Deployment directory exists"
    echo "Contents:"
    ls -la deployment/
    
    # Check deployment markers
    if [ -f "deployment/IS_PRODUCTION_ENVIRONMENT" ]; then
        echo "Production environment marker found"
        cat "deployment/IS_PRODUCTION_ENVIRONMENT"
    else
        echo "No production environment marker found"
    fi
    
    if [ -f "deployment/PERMANENT_PRODUCTION_MARKER" ]; then
        echo "Permanent production marker found"
        cat "deployment/PERMANENT_PRODUCTION_MARKER"
    else
        echo "No permanent production marker found"
    fi
    
    # Check backup files
    if [ -f "deployment/deployment_db.sqlite" ]; then
        SQLITE_SIZE=$(stat -c%s "deployment/deployment_db.sqlite")
        echo "SQLite backup exists: $SQLITE_SIZE bytes"
        # Try to get some basic info about the SQLite file
        if command -v sqlite3 &>/dev/null; then
            echo "Table count in SQLite backup:"
            sqlite3 "deployment/deployment_db.sqlite" ".tables" || echo "Failed to read SQLite file"
            echo "Table sizes in SQLite backup:"
            sqlite3 "deployment/deployment_db.sqlite" "SELECT name, count(*) FROM sqlite_master WHERE type='table';" || echo "Failed to query SQLite file"
        else
            echo "sqlite3 command not available for deeper inspection"
        fi
    else
        echo "No SQLite backup found"
    fi
    
    if [ -f "deployment/deployment_db.json" ]; then
        JSON_SIZE=$(stat -c%s "deployment/deployment_db.json")
        echo "JSON backup exists: $JSON_SIZE bytes"
        # Basic JSON analysis
        echo "JSON backup structure:"
        grep -o '"model": "[^"]*"' "deployment/deployment_db.json" | sort | uniq -c || echo "Failed to analyze JSON file"
    else
        echo "No JSON backup found"
    fi
    
    # Check for backup directory
    if [ -d "deployment/backups" ]; then
        echo "Backup directory exists"
        echo "Contents:"
        ls -la deployment/backups/
    else
        echo "No backup directory found"
    fi
    
else
    echo "Deployment directory does not exist"
    mkdir -p deployment
    echo "Created deployment directory"
fi

# Check Django database configuration
echo "========================================================"
echo "DJANGO DATABASE CONFIGURATION"
echo "========================================================"
cd smorasfotball
echo "Current directory: $(pwd)"

# Get Django database info
echo "Django database configuration:"
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from django.db import connections
db_settings = connections['default'].settings_dict
print(f'Engine: {db_settings[\"ENGINE\"]}')
print(f'Name: {db_settings[\"NAME\"]}')
print(f'User: {db_settings.get(\"USER\", \"N/A\")}')
print(f'Host: {db_settings.get(\"HOST\", \"N/A\")}')
"

# Check if the database exists
DB_PATH=$(python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from django.db import connections
print(connections['default'].settings_dict['NAME'])
")

if [ -n "$DB_PATH" ]; then
    echo "Database path: $DB_PATH"
    if [ -f "$DB_PATH" ]; then
        echo "Database file exists"
        DB_SIZE=$(stat -c%s "$DB_PATH")
        echo "Database size: $DB_SIZE bytes"
        
        # Try to get some basic info about the database file
        if command -v sqlite3 &>/dev/null; then
            echo "Table count in current database:"
            sqlite3 "$DB_PATH" ".tables" || echo "Failed to read database file"
            echo "Row counts in current database:"
            sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM auth_user;" || echo "Failed to query auth_user"
            sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM teammanager_team;" || echo "Failed to query teammanager_team"
            sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM teammanager_player;" || echo "Failed to query teammanager_player"
        else
            echo "sqlite3 command not available for deeper inspection"
        fi
    else
        echo "Database file does not exist"
    fi
else
    echo "Failed to determine database path"
fi

# Try to get model counts using Django ORM
echo "========================================================"
echo "DJANGO MODEL COUNTS"
echo "========================================================"
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from django.contrib.auth.models import User
from teammanager.models import Team, Player, Match
print(f'User count: {User.objects.count()}')
print(f'Team count: {Team.objects.count()}')
print(f'Player count: {Player.objects.count()}')
print(f'Match count: {Match.objects.count()}')
"

# Test restore capability
echo "========================================================"
echo "TESTING RESTORATION CAPABILITY"
echo "========================================================"
# Check if we have valid backup files to restore from
if [ -f "../deployment/deployment_db.sqlite" ] && [ $(stat -c%s "../deployment/deployment_db.sqlite") -gt 20000 ]; then
    echo "Valid SQLite backup exists for restoration"
    
    # Try to do a test restore to a temporary database
    TEMP_DB="/tmp/test_restore_db_$(date +%s).sqlite"
    echo "Attempting test restore to $TEMP_DB"
    cp "../deployment/deployment_db.sqlite" "$TEMP_DB"
    
    if [ -f "$TEMP_DB" ]; then
        echo "Test restore succeeded"
        if command -v sqlite3 &>/dev/null; then
            echo "Checking test database content:"
            sqlite3 "$TEMP_DB" ".tables" || echo "Failed to read test database"
            echo "Row counts in test database:"
            sqlite3 "$TEMP_DB" "SELECT COUNT(*) FROM auth_user;" || echo "Failed to query auth_user in test database"
            sqlite3 "$TEMP_DB" "SELECT COUNT(*) FROM teammanager_team;" || echo "Failed to query teammanager_team in test database"
            sqlite3 "$TEMP_DB" "SELECT COUNT(*) FROM teammanager_player;" || echo "Failed to query teammanager_player in test database"
        fi
        rm "$TEMP_DB"
    else
        echo "Test restore failed"
    fi
else
    echo "No valid SQLite backup available for test restoration"
fi

echo "========================================================"
echo "DATABASE DIAGNOSTIC SUMMARY"
echo "========================================================"
echo "1. Deployment directory status: $([ -d "../deployment" ] && echo "EXISTS" || echo "MISSING")"
echo "2. SQLite backup status: $([ -f "../deployment/deployment_db.sqlite" ] && echo "EXISTS - $(stat -c%s "../deployment/deployment_db.sqlite") bytes" || echo "MISSING")"
echo "3. JSON backup status: $([ -f "../deployment/deployment_db.json" ] && echo "EXISTS - $(stat -c%s "../deployment/deployment_db.json") bytes" || echo "MISSING")"
echo "4. Current database status: $([ -f "$DB_PATH" ] && echo "EXISTS - $(stat -c%s "$DB_PATH") bytes" || echo "MISSING")"
echo "5. Production environment markers: $([ -f "../deployment/IS_PRODUCTION_ENVIRONMENT" ] || [ -f "../deployment/PERMANENT_PRODUCTION_MARKER" ] && echo "PRESENT" || echo "MISSING")"

echo "========================================================"
echo "RECOMMENDATIONS"
echo "========================================================"
if [ -f "../deployment/deployment_db.sqlite" ] && [ $(stat -c%s "../deployment/deployment_db.sqlite") -gt 20000 ]; then
    echo "✅ Valid SQLite backup exists. Try running:"
    echo "   bash startup.sh"
    echo "   or for direct restoration:"
    echo "   cp deployment/deployment_db.sqlite smorasfotball/db.sqlite3"
    echo "   cd smorasfotball && python manage.py migrate"
elif [ -f "../deployment/deployment_db.json" ] && [ $(stat -c%s "../deployment/deployment_db.json") -gt 1000 ]; then
    echo "✅ Valid JSON backup exists. Try running:"
    echo "   cd smorasfotball && python manage.py loaddata ../deployment/deployment_db.json"
else
    echo "❌ No valid backups found. You may need to recreate your data."
    echo "   Consider running: python create_test_data.py"
fi

echo "========================================================"
echo "DIAGNOSTIC COMPLETE"
echo "========================================================"
echo "Log file: $LOG_FILE"
cd ..