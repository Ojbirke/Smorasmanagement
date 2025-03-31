#!/bin/bash

# Pre-deployment script for using an external PostgreSQL database
# This script runs before deployment to ensure the application is configured
# to use the external PostgreSQL database without migrating from SQLite

echo "===== CONFIGURING EXTERNAL POSTGRESQL DATABASE ====="

# Create deployment directory if it doesn't exist
mkdir -p deployment

# Create marker to skip database restore
touch deployment/SKIP_DB_RESTORE

# Create production environment marker
touch deployment/IS_PRODUCTION_ENVIRONMENT

# Check if DATABASE_URL is already set in .env
if grep -q "DATABASE_URL=" .env 2>/dev/null; then
    echo "DATABASE_URL already configured in .env file"
else
    echo "No DATABASE_URL found in .env file"
    echo "Running external database configuration script..."
    python configure_external_postgres.py
fi

echo "===== EXTERNAL DATABASE PRE-DEPLOYMENT CONFIGURATION COMPLETE ====="

# Run the deployment script
echo "You can now deploy the application."
echo "After deployment, you'll need to run migrations and create a superuser."
echo "Run these commands after deployment:"
echo "  cd smorasfotball && python manage.py migrate"
echo "  cd smorasfotball && python manage.py createsuperuser"