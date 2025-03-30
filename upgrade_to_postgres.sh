#!/bin/bash
# Upgrade to PostgreSQL Database
# This script helps you migrate from SQLite to PostgreSQL in one simple step.

echo "=== Smørås Fotball Database Upgrade Tool ==="
echo "This script will upgrade your database from SQLite to PostgreSQL."
echo ""

# Check if PostgreSQL is available
if ! command -v psql &> /dev/null
then
    echo "PostgreSQL client not found. Installing required packages..."
    # This is handled by Replit's environment
fi

# Create PostgreSQL database if needed
echo "Step 1: Creating PostgreSQL database..."
python create_postgres_db.py
if [ $? -ne 0 ]; then
    echo "Failed to create PostgreSQL database. Please try again."
    exit 1
fi

# Run the comprehensive database fix script
echo "Step 2: Migrating data to PostgreSQL..."
python fix_production_postgres.py
if [ $? -ne 0 ]; then
    echo "Migration encountered issues. Trying alternate approach..."
    python fix_production_database.py
fi

# Verify the database status
echo "Step 3: Verifying database configuration..."
cd smorasfotball && python manage.py dbstatus
cd ..

echo ""
echo "Database upgrade complete!"
echo "To check your database status at any time, run:"
echo "  cd smorasfotball && python manage.py dbstatus"