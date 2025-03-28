#!/usr/bin/env python3
"""
Test Deployment Backup and Restore Process

This script simulates a full deployment cycle including backup and restore.
It verifies that the database content is properly preserved across deployments.
"""
import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
import importlib.util

def count_db_objects():
    """Import the count script and run it to get object counts"""
    try:
        # Try to import the check_db_counts module
        spec = importlib.util.spec_from_file_location("check_db_counts", "check_db_counts.py")
        count_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(count_module)
        
        # Run the count function
        return count_module.check_db_counts()
    except ImportError:
        print("Could not import check_db_counts.py")
        return None

def create_deployment_backup():
    """Create a deployment backup using the management command"""
    print("\n--- Creating Deployment Backup ---")
    result = subprocess.run(
        ["cd", "smorasfotball", "&&", "python", "manage.py", "deployment_backup"],
        shell=True,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True

def simulate_deployment():
    """Simulate a deployment by removing the database and reinstalling"""
    print("\n--- Simulating Deployment (Removing Database) ---")
    
    # Find and remove the database
    db_path = os.path.join('smorasfotball', 'db.sqlite3')
    
    if os.path.exists(db_path):
        print(f"Removing database: {db_path}")
        backup_path = f"{db_path}.simulation_backup"
        shutil.copy2(db_path, backup_path)
        os.remove(db_path)
        print(f"Database removed (backup saved to {backup_path})")
    else:
        print(f"Database not found at: {db_path}")
        return False
    
    # Run migrations to create a fresh database
    print("\n--- Creating Fresh Database ---")
    result = subprocess.run(
        ["cd", "smorasfotball", "&&", "python", "manage.py", "migrate"],
        shell=True,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
        
    return True

def restore_from_backup():
    """Restore the database from the deployment backup"""
    print("\n--- Restoring Database from Backup ---")
    result = subprocess.run(
        ["python", "auto_restore_after_deploy.py"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True

def main():
    """Main function to run the simulation"""
    print("=== STARTING DEPLOYMENT SIMULATION ===")
    
    # Step 1: Get current database counts
    print("\n=== STEP 1: Get Initial Database Counts ===")
    initial_counts = count_db_objects()
    if not initial_counts:
        print("Error: Could not get initial database counts")
        return False
    
    # Step 2: Create deployment backup
    print("\n=== STEP 2: Create Deployment Backup ===")
    if not create_deployment_backup():
        print("Error: Deployment backup creation failed")
        return False
    
    # Step 3: Simulate deployment (remove database)
    print("\n=== STEP 3: Simulate Deployment ===")
    if not simulate_deployment():
        print("Error: Deployment simulation failed")
        return False
    
    # Step 4: Verify the database is empty
    print("\n=== STEP 4: Verify Database is Empty ===")
    empty_counts = count_db_objects()
    if empty_counts[0] > 0 or empty_counts[1] > 0 or empty_counts[2] > 0:
        print("Error: Database still contains data after simulated deployment")
        return False
    
    # Step 5: Restore from backup
    print("\n=== STEP 5: Restore from Backup ===")
    if not restore_from_backup():
        print("Error: Backup restoration failed")
        return False
    
    # Step 6: Verify the database was restored
    print("\n=== STEP 6: Verify Database Restoration ===")
    restored_counts = count_db_objects()
    if not restored_counts:
        print("Error: Could not get restored database counts")
        return False
    
    # Step 7: Compare before and after counts
    print("\n=== STEP 7: Comparing Before and After Counts ===")
    print(f"INITIAL COUNTS: {initial_counts}")
    print(f"RESTORED COUNTS: {restored_counts}")
    
    if initial_counts == restored_counts:
        print("\n✅ SUCCESS: Database was fully restored with all data intact!")
        return True
    else:
        print("\n❌ FAILURE: Data restoration was incomplete or incorrect.")
        
        # Show the differences
        print("\nDifferences detected:")
        labels = ["Users", "Teams", "Players", "Matches"]
        for i, (label, initial, restored) in enumerate(zip(labels, initial_counts, restored_counts)):
            if initial != restored:
                print(f"- {label}: {initial} → {restored} ({'+' if restored > initial else ''}{restored - initial})")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)