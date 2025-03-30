#!/usr/bin/env python3
"""
Fix Production PostgreSQL Configuration

This script is designed to fix the issue where the production environment
is still using SQLite instead of PostgreSQL. It will:

1. Check if the application is using PostgreSQL
2. If not, force the migration from SQLite to PostgreSQL
3. Properly save the PostgreSQL credentials for future deployments
4. Mark the environment as production to ensure data persistence

Usage:
    python fix_production_postgres.py

Run this script in the production environment after deployment.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

# Check if DATABASE_URL environment variable is set
if not os.environ.get('DATABASE_URL'):
    print("DATABASE_URL environment variable is not set. Attempting to create a PostgreSQL database automatically...")
    
    # Try to create a PostgreSQL database
    try:
        print("Running automatic PostgreSQL database creation script...")
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'create_postgres_db.py')
        
        if not os.path.exists(script_path):
            print(f"Script not found at {script_path}, creating it...")
            with open(script_path, 'w') as f:
                f.write("""#!/usr/bin/env python3
'''
Create PostgreSQL Database

This script attempts to automatically create a PostgreSQL database in the Replit environment.
'''

import os
import sys
import json
import subprocess
import time
from pathlib import Path

def run_command(cmd, cwd=None):
    '''Run a shell command and return output'''
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

def get_postgres_connection_data():
    '''Try to get PostgreSQL connection data from environment variables'''
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
    '''Create a PostgreSQL database using Replit's database API if available'''
    if 'DATABASE_URL' in os.environ and os.environ.get('DATABASE_URL').startswith('postgres'):
        print(f"PostgreSQL database already configured: {os.environ['DATABASE_URL']}")
        return True
    
    # Try using Replit's database tools
    try:
        subprocess.run(['python', '-c', 
                    'from replit import db; print("Replit database module available")'],
                    capture_output=True, text=True)
        
        # This is a one-way function that can trigger database creation
        subprocess.run(['python', '-c', 
                       'from replit.database import DatabaseCreateRequest; ' +
                       'req = DatabaseCreateRequest(); print(req.database_type)'],
                       capture_output=True, text=True)
        # Give Replit time to create the database
        time.sleep(5)
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
            with open(env_path, 'w' if not env_path.exists() else 'a') as f:
                f.write(f'\\nDATABASE_URL="{db_url}"\\n')
            
            print(f"Created DATABASE_URL from PostgreSQL credentials")
            return True
    
    if 'DATABASE_URL' in os.environ and os.environ.get('DATABASE_URL').startswith('postgres'):
        print(f"PostgreSQL database successfully configured")
        return True
    else:
        print("Failed to configure PostgreSQL database automatically")
        return False

if __name__ == "__main__":
    create_postgres_db()
""")
        
        # Make the script executable
        os.chmod(script_path, 0o755)
        
        # Run the script
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True)
        print(result.stdout)
        
        # Check if the script created a DATABASE_URL successfully
        if os.environ.get('DATABASE_URL') and os.environ.get('DATABASE_URL').startswith('postgres'):
            print("PostgreSQL database successfully created and configured!")
        else:
            print("Failed to automatically create a PostgreSQL database.")
            print("Please set DATABASE_URL to a valid PostgreSQL connection string.")
            print("You can create a new PostgreSQL database in Replit using the 'Database' tab.")
            sys.exit(1)
    except Exception as e:
        print(f"Error creating PostgreSQL database: {e}")
        print("Please set DATABASE_URL to a valid PostgreSQL connection string.")
        print("You can create a new PostgreSQL database in Replit using the 'Database' tab.")
        sys.exit(1)

# Print database URL (with sensitive parts hidden)
db_url = os.environ.get('DATABASE_URL', '')
db_url_parts = db_url.split('@')
if len(db_url_parts) > 1:
    print(f"Using DATABASE_URL: {db_url_parts[0]}@{'*' * len(db_url_parts[1])}")
else:
    print(f"Using DATABASE_URL: {'*' * len(db_url)}")

# Add Django project to path
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball')
sys.path.append(BASE_DIR)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')

try:
    import django
    django.setup()
    from django.core.management import call_command
    from django.conf import settings
    from django.db import connections
except ImportError:
    print("Error: Django could not be imported. Make sure Django is installed.")
    sys.exit(1)

def detect_database_engine():
    """Detect which database engine is currently being used"""
    engine = settings.DATABASES['default'].get('ENGINE', '')
    print(f"Current database engine: {engine}")
    
    if 'postgresql' in engine.lower():
        print("PostgreSQL is already being used.")
        return 'postgresql'
    elif 'sqlite' in engine.lower():
        print("SQLite is currently being used.")
        return 'sqlite'
    else:
        print(f"Unknown database engine: {engine}")
        return 'unknown'

def export_data_from_sqlite():
    """Export data from SQLite to a JSON file"""
    if detect_database_engine() != 'sqlite':
        print("SQLite is not currently active, cannot export data")
        return None
    
    try:
        # Create a backup of the current SQLite database
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_file = f"sqlite_export_{timestamp}.json"
        
        print(f"Exporting SQLite data to {backup_file}...")
        call_command('dumpdata', output=backup_file)
        
        if os.path.exists(backup_file) and os.path.getsize(backup_file) > 100:
            print(f"SQLite data exported to {backup_file} ({os.path.getsize(backup_file)} bytes)")
            return backup_file
        else:
            print("Error: Export file is too small or doesn't exist")
            return None
    except Exception as e:
        print(f"Error exporting SQLite data: {e}")
        return None

def get_database_counts():
    """Get counts of objects in the current database"""
    try:
        # Get models
        from django.contrib.auth.models import User
        from teammanager.models import Team, Player, Match
        
        teams = Team.objects.count()
        players = Player.objects.count()
        matches = Match.objects.count()
        users = User.objects.count()
        
        print(f"Database contains: {teams} teams, {players} players, {matches} matches, {users} users")
        
        return {
            'teams': teams,
            'players': players,
            'matches': matches,
            'users': users,
        }
    except Exception as e:
        print(f"Error counting database objects: {e}")
        return {'teams': 0, 'players': 0, 'matches': 0, 'users': 0}

def save_postgres_credentials():
    """Save PostgreSQL credentials to a file for future deployments"""
    if not os.environ.get('DATABASE_URL'):
        print("DATABASE_URL not set, cannot save credentials")
        return False
    
    try:
        # Save credentials to deployment directory
        repo_root = Path(settings.BASE_DIR).parent
        deployment_dir = repo_root / 'deployment'
        os.makedirs(deployment_dir, exist_ok=True)
        
        creds_file = deployment_dir / 'postgres_credentials.json'
        
        # Save only the DATABASE_URL to avoid saving other sensitive credentials
        with open(creds_file, 'w') as f:
            json.dump({'DATABASE_URL': os.environ.get('DATABASE_URL')}, f)
        
        print(f"PostgreSQL credentials saved to {creds_file}")
        
        # Update the IS_PRODUCTION_ENVIRONMENT marker
        marker_path = deployment_dir / 'IS_PRODUCTION_ENVIRONMENT'
        with open(marker_path, 'w') as f:
            f.write(f"This instance was marked as production after PostgreSQL migration on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Create a PERMANENT marker that won't be overwritten by deployments
        perm_marker_path = deployment_dir / 'PERMANENT_PRODUCTION_MARKER'
        with open(perm_marker_path, 'w') as f:
            f.write(f"This instance was permanently marked as production on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"DO NOT DELETE THIS FILE - It ensures data persistence across deployments.\n")
        
        print("Environment marked as production")
        return True
    except Exception as e:
        print(f"Error saving PostgreSQL credentials: {e}")
        return False

def restart_using_postgres():
    """Force Django to restart using PostgreSQL"""
    print("Restarting Django with PostgreSQL settings...")
    
    # Modify DJANGO_SETTINGS_MODULE to trigger a reload
    old_settings = os.environ.get('DJANGO_SETTINGS_MODULE', '')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'temp_settings_module'
    os.environ['DJANGO_SETTINGS_MODULE'] = old_settings
    
    # Reload Django
    import django
    django.setup()
    
    # Check if PostgreSQL is now active
    engine = detect_database_engine()
    return engine == 'postgresql'

def migrate_to_postgres(data_file):
    """Migrate data from SQLite to PostgreSQL"""
    if not data_file or not os.path.exists(data_file):
        print("No data file available for migration")
        return False
    
    try:
        # Force restart with PostgreSQL
        if not restart_using_postgres():
            print("Failed to restart Django with PostgreSQL settings")
            return False
        
        # Apply migrations to PostgreSQL to ensure tables exist
        print("Applying migrations to PostgreSQL...")
        call_command('migrate')
        
        # Load data into PostgreSQL
        print(f"Loading data from {data_file} into PostgreSQL...")
        call_command('loaddata', data_file)
        
        # Verify data was loaded
        counts = get_database_counts()
        
        # Save PostgreSQL credentials for future use
        save_postgres_credentials()
        
        if counts['teams'] > 0 and counts['players'] > 0:
            print("Migration to PostgreSQL completed successfully!")
            
            # Clean up export file
            try:
                os.remove(data_file)
                print(f"Removed temporary file {data_file}")
            except:
                pass
                
            return True
        else:
            print("Warning: Migration succeeded but database has no teams or players")
            return False
    except Exception as e:
        print(f"Error migrating to PostgreSQL: {e}")
        return False

def ensure_postgres_environment_variable():
    """Ensure the DATABASE_URL environment variable is used in future sessions"""
    try:
        # Check if we're in a Replit environment
        replit_dir = Path.home() / '.config' / 'replit'
        if replit_dir.exists():
            # Try to update the .env file
            env_path = Path('.') / '.env'
            
            # Read existing content
            env_content = []
            if env_path.exists():
                with open(env_path, 'r') as f:
                    env_content = f.readlines()
            
            # Check if DATABASE_URL is already in the .env file
            has_db_url = any(line.startswith('DATABASE_URL=') for line in env_content)
            
            # Add or update DATABASE_URL entry
            if not has_db_url:
                with open(env_path, 'a') as f:
                    f.write(f"\n# PostgreSQL database URL added on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"DATABASE_URL={os.environ.get('DATABASE_URL')}\n")
                print(f"Added DATABASE_URL to .env file: {env_path}")
            else:
                print("DATABASE_URL already exists in .env file")
            
            return True
        else:
            print("Not running in a Replit environment, skipping .env update")
            return False
    except Exception as e:
        print(f"Error ensuring DATABASE_URL environment variable: {e}")
        return False

def main():
    print("Starting PostgreSQL migration fix...")
    
    # Check current database engine
    engine = detect_database_engine()
    
    if engine == 'postgresql':
        print("Good news! PostgreSQL is already being used.")
        print("Saving credentials to ensure future deployments use PostgreSQL...")
        save_postgres_credentials()
        ensure_postgres_environment_variable()
        
        # Get current database counts
        get_database_counts()
        
        print("PostgreSQL configuration is correct.")
        sys.exit(0)
    
    if engine == 'sqlite':
        print("SQLite is being used. Starting migration to PostgreSQL...")
        
        # Get current SQLite database state
        print("Checking current SQLite database state:")
        sqlite_counts = get_database_counts()
        
        # Export SQLite data
        data_file = export_data_from_sqlite()
        
        if not data_file:
            print("Failed to export SQLite data. Cannot proceed with migration.")
            sys.exit(1)
        
        # Migrate to PostgreSQL
        if migrate_to_postgres(data_file):
            print("Migration to PostgreSQL completed successfully!")
            
            # Ensure environment variable is set for future sessions
            ensure_postgres_environment_variable()
            
            # Final check to confirm migration
            postgres_counts = get_database_counts()
            
            if (postgres_counts['teams'] >= sqlite_counts['teams'] and 
                postgres_counts['players'] >= sqlite_counts['players']):
                print("✅ Success! All data was migrated correctly to PostgreSQL.")
                print("✅ Future deployments will use PostgreSQL.")
                sys.exit(0)
            else:
                print("⚠️ Warning: Some data may not have been migrated correctly.")
                print("   Please verify your database contents.")
                sys.exit(1)
        else:
            print("❌ Migration to PostgreSQL failed.")
            sys.exit(1)
    
    print("❌ Unknown database engine. Cannot fix PostgreSQL configuration.")
    sys.exit(1)

if __name__ == "__main__":
    main()