#!/usr/bin/env python3
"""
Create PostgreSQL Database

This script attempts to automatically create a PostgreSQL database in the Replit environment
and save the database connection URL in the environment variable DATABASE_URL.

It will:
1. Check if PostgreSQL is available
2. Use the Replit database API if available
3. Save the database URL to a file for persistence across restarts
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, text=True, 
            capture_output=True, cwd=cwd
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command '{cmd}' failed with exit code {e.returncode}")
        print(f"Error output: {e.stderr}")
        return None

def check_psql_available():
    """Check if PostgreSQL client is available"""
    return run_command("which psql") is not None

def get_postgres_connection_data():
    """Try to get PostgreSQL connection data from environment variables"""
    # Check if Replit has provided PostgreSQL credentials
    if all(k in os.environ for k in ['PGDATABASE', 'PGUSER', 'PGPASSWORD', 'PGHOST', 'PGPORT']):
        return {
            'database': os.environ['PGDATABASE'],
            'user': os.environ['PGUSER'],
            'password': os.environ['PGPASSWORD'],
            'host': os.environ['PGHOST'],
            'port': os.environ['PGPORT']
        }
    return None

def create_postgres_db():
    """Create a PostgreSQL database using Replit's database API if available"""
    
    # If DATABASE_URL is already set, we don't need to do anything
    if 'DATABASE_URL' in os.environ and os.environ.get('DATABASE_URL').startswith('postgres'):
        print(f"PostgreSQL database already configured: {os.environ['DATABASE_URL']}")
        return True
    
    print("Attempting to create PostgreSQL database...")
    
    # Try running the Replit database create tool
    try:
        result = subprocess.run(['python', '-c', 
                        'from replit import db; print("Replit database module available")'],
                        capture_output=True, text=True)
        if 'Replit database module available' in result.stdout:
            print("Replit database module found")
            
            # Try the Replit database API
            try:
                # This is a one-way function that can trigger database creation
                subprocess.run(['python', '-c', 
                               'from replit.database import DatabaseCreateRequest; ' +
                               'req = DatabaseCreateRequest(); print(req.database_type)'],
                               capture_output=True, text=True)
                # Give Replit time to create the database
                print("Database creation initiated, waiting 5 seconds...")
                time.sleep(5)
            except Exception as e:
                print(f"Error initializing Replit database: {e}")
    except Exception:
        print("Replit database module not available") 
    
    # If DATABASE_URL still isn't set, check if we can create it from PGDATABASE etc.
    if 'DATABASE_URL' not in os.environ or not os.environ.get('DATABASE_URL').startswith('postgres'):
        conn_data = get_postgres_connection_data()
        if conn_data:
            # Construct DATABASE_URL
            db_url = (f"postgresql://{conn_data['user']}:{conn_data['password']}@"
                     f"{conn_data['host']}:{conn_data['port']}/{conn_data['database']}")
            os.environ['DATABASE_URL'] = db_url
            
            # Save to .env file so it persists
            env_path = Path('.env')
            if env_path.exists():
                with open(env_path, 'r') as f:
                    env_content = f.read()
                
                # Update or add DATABASE_URL
                if 'DATABASE_URL=' in env_content:
                    new_content = []
                    for line in env_content.splitlines():
                        if line.startswith('DATABASE_URL='):
                            new_content.append(f'DATABASE_URL="{db_url}"')
                        else:
                            new_content.append(line)
                    env_content = '\n'.join(new_content)
                else:
                    env_content += f'\nDATABASE_URL="{db_url}"\n'
                
                with open(env_path, 'w') as f:
                    f.write(env_content)
            else:
                with open(env_path, 'w') as f:
                    f.write(f'DATABASE_URL="{db_url}"\n')
            
            print(f"Created DATABASE_URL from PostgreSQL credentials: {db_url}")
            return True
    
    # Check if DATABASE_URL is now set
    if 'DATABASE_URL' in os.environ and os.environ.get('DATABASE_URL').startswith('postgres'):
        print(f"PostgreSQL database successfully configured: {os.environ['DATABASE_URL']}")
        return True
    else:
        print("Failed to configure PostgreSQL database automatically")
        return False

def main():
    """Main function to create PostgreSQL database"""
    success = create_postgres_db()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())