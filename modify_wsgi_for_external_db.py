#!/usr/bin/env python3
"""
Modify WSGI for External Database

This script modifies the WSGI application configuration to ensure
that the external PostgreSQL database is used in the deployment environment.
It adds the necessary environment variable loading to the WSGI script.

Usage:
    python modify_wsgi_for_external_db.py
"""

import os
import sys
from pathlib import Path

# Path to the WSGI file
WSGI_PATH = Path('smorasfotball/smorasfotball/wsgi.py')

def backup_wsgi_file():
    """Create a backup of the WSGI file before modifying it"""
    backup_path = WSGI_PATH.with_suffix('.py.bak')
    if not backup_path.exists():
        with open(WSGI_PATH, 'r') as f_in:
            with open(backup_path, 'w') as f_out:
                f_out.write(f_in.read())
        print(f"Created backup of WSGI file at {backup_path}")
    else:
        print(f"Backup already exists at {backup_path}")

def modify_wsgi_file():
    """Modify the WSGI file to load environment variables"""
    if not WSGI_PATH.exists():
        print(f"Error: WSGI file not found at {WSGI_PATH}")
        return False
    
    # Read the current content
    with open(WSGI_PATH, 'r') as f:
        content = f.read()
    
    # Check if our code is already there
    if "# Load environment variables for external database" in content:
        print("WSGI file already modified for external database.")
        return True
    
    # Prepare the code to insert
    env_code = """
# Load environment variables for external database
import os
from pathlib import Path

# Load from .env file if it exists
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    print(f"Loading environment variables from {env_path}")
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
    print("Environment variables loaded.")
"""
    
    # Find the insertion point (after the imports, before application init)
    import_section_end = max(content.find("os.environ.setdefault"), 0)
    if import_section_end == 0:
        # If we can't find the os.environ line, insert at the beginning
        modified_content = env_code + content
    else:
        # Insert after the os.environ line
        import_line_end = content.find('\n', import_section_end) + 1
        modified_content = content[:import_line_end] + env_code + content[import_line_end:]
    
    # Write the modified content
    with open(WSGI_PATH, 'w') as f:
        f.write(modified_content)
    
    print(f"Modified WSGI file to load environment variables from .env file.")
    return True

def main():
    """Main function"""
    print("Modifying WSGI for external database...")
    
    if not WSGI_PATH.exists():
        print(f"Error: WSGI file not found at {WSGI_PATH}")
        return
    
    # Create a backup first
    backup_wsgi_file()
    
    # Modify the WSGI file
    if modify_wsgi_file():
        print("WSGI file successfully modified.")
        print("The application will now load DATABASE_URL from .env file during deployment.")
    else:
        print("Failed to modify WSGI file.")

if __name__ == "__main__":
    main()