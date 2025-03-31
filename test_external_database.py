#!/usr/bin/env python3
"""
Test External Database Connection

This script tests the connection to an external PostgreSQL database.
It's useful for verifying that the database connection works
before deploying the application.

Usage:
    python test_external_database.py
"""

import os
import sys
import time

# Check for DATABASE_URL
if 'DATABASE_URL' not in os.environ:
    print("No DATABASE_URL environment variable found.")
    print("Please set DATABASE_URL or run configure_external_postgres.py first.")
    sys.exit(1)

db_url = os.environ['DATABASE_URL']
print(f"Testing connection to database: {db_url.split('@')[1] if '@' in db_url else 'unknown'}")

try:
    import psycopg2
    from urllib.parse import urlparse

    # Parse the URL
    url = urlparse(db_url)
    
    # Extract connection parameters
    dbname = url.path[1:]  # Remove leading slash
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port
    
    # Connect to the database
    print("Connecting to PostgreSQL database...")
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    
    # Create a cursor
    cur = conn.cursor()
    
    # Test query
    print("Testing database query...")
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"PostgreSQL version: {version[0]}")
    
    # Check for Django tables
    print("\nChecking for Django tables...")
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    
    if not tables:
        print("No tables found in the database. This appears to be a fresh database.")
        print("You'll need to run migrations after deployment.")
    else:
        print(f"Found {len(tables)} tables in the database:")
        for table in tables[:10]:  # Show only first 10 tables
            print(f"  - {table[0]}")
        if len(tables) > 10:
            print(f"  ... and {len(tables) - 10} more.")
    
    # Close connection
    cur.close()
    conn.close()
    
    print("\nDatabase connection test successful!")
    print("The external PostgreSQL database is accessible and ready to use.")

except ImportError:
    print("Error: psycopg2 module not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    print("Please run this script again after installation.")
    sys.exit(1)
except Exception as e:
    print(f"Error connecting to the database: {e}")
    print("\nPossible solutions:")
    print("1. Check that the DATABASE_URL is correct")
    print("2. Ensure the database server is accessible from your current location")
    print("3. Verify that the database user has the necessary permissions")
    print("4. Check if a firewall is blocking the connection")
    sys.exit(1)