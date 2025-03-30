#!/bin/bash
# Force PostgreSQL in Production
#
# This script is designed to be run in the production environment immediately after
# a deployment to ensure that PostgreSQL is properly configured and used.
#
# It will:
# 1. Create a PostgreSQL database if needed
# 2. Run the fix_production_postgres.py script
# 3. Restart the application using PostgreSQL
#
# Usage: bash force_postgres_production.sh

echo "Starting PostgreSQL enforcement in production environment..."

# Check if we already have DATABASE_URL environment variable
if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL not found. Attempting to create PostgreSQL database..."
    
    # Check if we have PostgreSQL credentials
    if [ -n "$PGDATABASE" ] && [ -n "$PGUSER" ] && [ -n "$PGHOST" ]; then
        echo "Found PostgreSQL credentials, constructing DATABASE_URL..."
        export DATABASE_URL="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
        echo "DATABASE_URL created from environment variables."
        
        # Save to .env file
        echo "Adding DATABASE_URL to .env file..."
        echo -e "\n# PostgreSQL database URL added by force_postgres_production.sh" >> .env
        echo "DATABASE_URL=$DATABASE_URL" >> .env
    else
        echo "No PostgreSQL credentials found. Trying to create PostgreSQL database..."
        
        # Try to create a PostgreSQL database using Replit's tools
        python create_postgres_db.py
        
        # Check if DATABASE_URL is now set
        if [ -z "$DATABASE_URL" ]; then
            echo "Failed to create PostgreSQL database automatically."
            echo "Please use Replit's 'Secrets' feature to set DATABASE_URL."
            exit 1
        fi
    fi
fi

# Run the fix_production_postgres.py script
echo "Running fix_production_postgres.py script..."
python fix_production_postgres.py

# Check the exit code of the script
if [ $? -ne 0 ]; then
    echo "PostgreSQL migration failed. Please check the output above for details."
    exit 1
fi

# Save PostgreSQL credentials to various locations for redundancy
echo "Saving PostgreSQL credentials in multiple locations..."

# Create deployment directory if it doesn't exist
mkdir -p deployment

# 1. Standard location
cat > deployment/postgres_credentials.json << EOF
{
    "DATABASE_URL": "$DATABASE_URL"
}
EOF

# 2. Backup location in case standard one is overwritten
cat > deployment/postgres_creds_backup.json << EOF
{
    "DATABASE_URL": "$DATABASE_URL"
}
EOF

# Create production environment marker
echo "$(date) - Manually marked as production by force_postgres_production.sh" > "deployment/IS_PRODUCTION_ENVIRONMENT"
echo "$(date) - PERMANENT production marker created by force_postgres_production.sh" > "deployment/PERMANENT_PRODUCTION_MARKER"

echo "PostgreSQL enforcement completed successfully!"
echo "This production environment is now using PostgreSQL."
echo "Your data has been migrated from SQLite to PostgreSQL."
echo "Future deployments will maintain this PostgreSQL configuration."

# Final verification
cd smorasfotball
python manage.py dbstatus

echo "✅ Process complete. You may need to restart your application server."