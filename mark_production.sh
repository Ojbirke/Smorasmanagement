#!/bin/bash
# Mark as Production Environment
# This script creates permanent markers to indicate a production environment
# Run this script after your first deployment to ensure data persistence

echo "========================================================"
echo "MARKING AS PRODUCTION ENVIRONMENT"
echo "========================================================"
echo "Current directory: $(pwd)"
echo "Current time: $(date)"

# Create deployment directory if it doesn't exist
mkdir -p deployment
echo "Deployment directory: $(pwd)/deployment"

# Create the marker files
echo "$(date) - Deployment detected and marked as production" > "deployment/IS_PRODUCTION_ENVIRONMENT"
echo "$(date) - PERMANENT PRODUCTION MARKER - DO NOT DELETE" > "deployment/PERMANENT_PRODUCTION_MARKER"

# Set permissions
chmod 644 "deployment/IS_PRODUCTION_ENVIRONMENT"
chmod 444 "deployment/PERMANENT_PRODUCTION_MARKER" # Make read-only

echo "✅ Successfully marked as production environment"
echo "✅ Future deployments will PRESERVE your data"
echo "✅ Database backups will be automatically restored on redeployment"