#!/bin/bash

# Deployment Auto-Restore with Protection
# This script runs the deployment protection first, then the auto-restore script

# Log our actions
timestamp=$(date "+%Y-%m-%d %H:%M:%S")
echo "Starting protected auto-restore at $timestamp" > auto_restore_log.txt
echo "----------------------------------------" >> auto_restore_log.txt

# First, run the deployment protection
echo "Running deployment protection..."
python deployment_protect.py
PROTECT_STATUS=$?

echo "Deployment protection status: $PROTECT_STATUS" >> auto_restore_log.txt

# Now run the auto-restore script
echo "Running auto-restore script..."
python auto_restore_after_deploy.py
RESTORE_STATUS=$?

echo "Auto-restore status: $RESTORE_STATUS" >> auto_restore_log.txt

# Generate a report
timestamp=$(date "+%Y-%m-%d %H:%M:%S")
echo "Completed auto-restore at $timestamp" >> auto_restore_log.txt

# If both scripts were successful, we're good
if [ $PROTECT_STATUS -eq 0 ] && [ $RESTORE_STATUS -eq 0 ]; then
    echo "Deployment protection and auto-restore completed successfully."
    echo "SUCCESS: Protection and auto-restore completed successfully." >> auto_restore_log.txt
    exit 0
else
    echo "WARNING: One or more steps failed. Check the logs for details."
    echo "FAILURE: One or more steps failed." >> auto_restore_log.txt
    exit 1
fi