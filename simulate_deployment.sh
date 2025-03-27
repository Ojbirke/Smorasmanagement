#!/bin/bash
# Simulate deployment script
# This script tests the deployment backup system by:
# 1. Creating a temporary folder to simulate a fresh deployment
# 2. Copying the necessary files to this folder
# 3. Running the pre_deploy.sh script
# 4. Running the startup.sh script in the simulated environment
# 5. Testing that the database has been correctly restored

echo "========================================"
echo "SIMULATING REPLIT DEPLOYMENT PROCESS"
echo "========================================"
echo "This script tests that your database will be preserved during redeployment"
echo

# Create a temporary deployment directory
TEMP_DIR="./temp_deployment_test"
echo "Creating temporary deployment environment at $TEMP_DIR"
mkdir -p $TEMP_DIR

# Create necessary subdirectories
mkdir -p $TEMP_DIR/smorasfotball
mkdir -p $TEMP_DIR/deployment
mkdir -p $TEMP_DIR/persistent_backups

# First, check if we have existing deployment backups
echo "Checking for existing deployment backups..."
if [ -f "./deployment/deployment_db.sqlite" ]; then
    echo "Found SQLite deployment backup, copying to simulation environment..."
    cp "./deployment/deployment_db.sqlite" "$TEMP_DIR/deployment/"
    BACKUP_FOUND=true
elif [ -f "./deployment/deployment_db.json" ]; then
    echo "Found JSON deployment backup, copying to simulation environment..."
    cp "./deployment/deployment_db.json" "$TEMP_DIR/deployment/"
    BACKUP_FOUND=true
else
    echo "No existing deployment backups found."
    echo "Creating test deployment backup..."
    cd smorasfotball
    python manage.py deployment_backup --name "test_simulation" --format sqlite || python manage.py deployment_backup --name "test_simulation"
    cd ..
    
    if [ -f "./deployment/deployment_db.sqlite" ]; then
        echo "Created SQLite test backup, copying to simulation environment..."
        cp "./deployment/deployment_db.sqlite" "$TEMP_DIR/deployment/"
        BACKUP_FOUND=true
    elif [ -f "./deployment/deployment_db.json" ]; then
        echo "Created JSON test backup, copying to simulation environment..."
        cp "./deployment/deployment_db.json" "$TEMP_DIR/deployment/"
        BACKUP_FOUND=true
    else
        echo "Failed to create test backup. Simulation cannot continue."
        rm -rf $TEMP_DIR
        exit 1
    fi
fi

# Copy essential files for deployment
echo "Copying essential files to simulation environment..."
cp -r ./smorasfotball/* $TEMP_DIR/smorasfotball/
cp pre_deploy.sh $TEMP_DIR/
cp recreate_superuser.py $TEMP_DIR/

# Change to the temporary directory
cd $TEMP_DIR

# Run the pre_deploy.sh script
echo
echo "========================================"
echo "STEP 1: RUNNING PRE-DEPLOYMENT SCRIPT"
echo "========================================"
chmod +x pre_deploy.sh
./pre_deploy.sh

# Check that the deployment backups were preserved
echo
echo "========================================"
echo "STEP 2: CHECKING DEPLOYMENT BACKUPS PRESERVATION"
echo "========================================"
if [ -f "./deployment/deployment_db.sqlite" ]; then
    echo "✅ SQLite deployment backup was preserved as expected"
elif [ -f "./deployment/deployment_db.json" ]; then
    echo "✅ JSON deployment backup was preserved as expected"
else
    echo "❌ ERROR: No deployment backups found after pre-deployment"
    echo "This suggests that the deployment backups would not be preserved"
    cd ..
    rm -rf $TEMP_DIR
    exit 1
fi

# Run the startup script
echo
echo "========================================"
echo "STEP 3: RUNNING STARTUP SCRIPT"
echo "========================================"
cd smorasfotball
chmod +x startup.sh
./startup.sh

# Check if the database now exists
echo
echo "========================================"
echo "STEP 4: VERIFYING DATABASE RESTORATION"
echo "========================================"
if [ -f "./db.sqlite3" ]; then
    echo "✅ Database file exists"
    
    # Try to run a simple Django command to verify it's working
    DB_CHECK=$(python manage.py shell -c "from teammanager.models import Team; print(f'Found {Team.objects.count()} teams in the database')")
    if [ $? -eq 0 ]; then
        echo "✅ Database is functional: $DB_CHECK"
    else
        echo "❌ Database exists but appears to be corrupted or invalid"
    fi
else
    echo "❌ ERROR: Database file does not exist after startup"
    echo "This suggests that database restoration failed"
fi

# Return to the original directory and clean up
cd ../../
echo
echo "========================================"
echo "SIMULATION COMPLETE"
echo "========================================"
echo "The simulation environment is at: $TEMP_DIR"
echo "You can inspect it to verify the deployment process behavior"
echo
echo "To clean up the simulation environment, run:"
echo "rm -rf $TEMP_DIR"