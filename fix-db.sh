#!/bin/bash
# Fix Production Database
# Simple script to run the database fix utility
# Usage: bash fix-db.sh

echo "Running production database fix utility..."
python fix_production_database.py

# Check exit code
if [ $? -eq 0 ]; then
  echo "✅ Database fix completed successfully"
else
  echo "❌ Database fix encountered errors"
  echo "Please check the output above for details"
fi

# Provide help for manually fixing issues
echo
echo "If you're still having problems, try these steps:"
echo "1. Click 'Database' in the Replit sidebar"
echo "2. Create a PostgreSQL database"
echo "3. Run this script again: bash fix-db.sh"
echo
echo "If problems persist, run: python fix_production_postgres.py"