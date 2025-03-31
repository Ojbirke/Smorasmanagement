#!/bin/bash
# Deployment script for using an external PostgreSQL database

set -e  # Exit on any error

echo "=================================================="
echo "  SMØRÅS FOTBALL EXTERNAL DATABASE DEPLOYMENT"
echo "=================================================="
echo

# Check if the external database is configured
if [ ! -f .env ]; then
    echo "No .env file found. You need to configure the external database first."
    echo "Running configuration script..."
    python configure_external_postgres.py
fi

# Create necessary directories
mkdir -p deployment

# Create markers to disable automatic database restoration
echo "Creating deployment markers..."
touch deployment/SKIP_DB_RESTORE
touch deployment/IS_PRODUCTION_ENVIRONMENT

# Modify WSGI file to load environment variables
echo "Modifying WSGI file to use external database..."
python modify_wsgi_for_external_db.py

# Test the database connection
echo "Testing database connection..."
python test_external_database.py
if [ $? -ne 0 ]; then
    echo "Database connection test failed. Please fix the issues before deploying."
    exit 1
fi

# Prepare for deployment
echo "Preparing for deployment..."
# Create a backup of current code if needed
git add .
git stash save "Pre-deployment backup $(date +%Y%m%d_%H%M%S)" || true

echo
echo "=================================================="
echo "  DEPLOYMENT PREPARATION COMPLETE"
echo "=================================================="
echo
echo "Your application is now ready to be deployed with an external PostgreSQL database."
echo
echo "After deployment, run these commands in your deployed application:"
echo "  cd smorasfotball"
echo "  python manage.py migrate"
echo "  python manage.py createsuperuser"
echo
echo "Click the 'Deploy' button in Replit to deploy your application."
echo "=================================================="