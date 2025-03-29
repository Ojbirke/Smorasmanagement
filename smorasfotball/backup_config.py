"""
Backup Configuration Module

This module provides centralized configuration for backup locations and behaviors.
It allows for customizable backup paths, separate from the main codebase.

Usage:
    from backup_config import get_backup_path, get_backup_git_repo

    # Get the primary backup path
    backup_dir = get_backup_path()
    
    # Get the Git repository for backups
    backup_repo = get_backup_git_repo()
"""

import os
import json
from pathlib import Path
from django.conf import settings

# Default configuration - will be used if no custom config file exists
DEFAULT_CONFIG = {
    # Primary backup directory (outside the Git repository)
    "backup_directory": os.path.join(str(Path.home()), "smorasfotball_backups"),
    
    # Secondary backup locations
    "backup_locations": [
        # Project-local backups (still inside the main codebase)
        {"path": "persistent_backups", "enabled": True, "max_backups": 5},
        {"path": "deployment", "enabled": True, "max_backups": 3}
    ],
    
    # Git backup repository configuration
    "git_backup": {
        "enabled": False,  # Set to True to enable Git backup
        "repository": "https://github.com/username/smorasfotball-backups.git",
        "branch": "main",
        "username": "",  # Git username for authentication
        "token": ""      # Git token/password for authentication (set via environment variable)
    }
}

# Path to configuration file
CONFIG_FILE = os.path.join(settings.BASE_DIR, "backup_config.json")

def load_config():
    """
    Load backup configuration from file or return defaults
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"Error loading backup config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """
    Save the backup configuration to file
    """
    try:
        # Create a sanitized version without sensitive data
        sanitized = config.copy()
        if "git_backup" in sanitized and "token" in sanitized["git_backup"]:
            sanitized["git_backup"]["token"] = ""  # Don't save token to file
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(sanitized, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving backup config: {e}")
        return False

def get_backup_path(location_name=None):
    """
    Get the configured backup path
    
    Args:
        location_name: Optional name of a secondary backup location
        
    Returns:
        Path to the backup directory (string)
    """
    config = load_config()
    
    # If a specific location is requested
    if location_name:
        for loc in config["backup_locations"]:
            if loc.get("name") == location_name and loc.get("enabled", True):
                path = loc["path"]
                # Convert relative paths to absolute
                if not os.path.isabs(path):
                    path = os.path.join(str(Path(settings.BASE_DIR).parent), path)
                return path
        return None
    
    # Return primary backup path
    path = config["backup_directory"]
    # Ensure the directory exists
    os.makedirs(path, exist_ok=True)
    return path

def get_backup_git_repo():
    """
    Get Git repository configuration for backups
    
    Returns:
        Dictionary with Git repository configuration or None if not enabled
    """
    config = load_config()
    git_config = config.get("git_backup", {})
    
    if not git_config.get("enabled", False):
        return None
    
    # Use environment variable for token if available
    if "GITHUB_TOKEN" in os.environ and not git_config.get("token"):
        git_config["token"] = os.environ["GITHUB_TOKEN"]
    
    return git_config

def set_backup_path(path):
    """
    Set the primary backup path
    
    Args:
        path: New backup path
        
    Returns:
        Boolean indicating success
    """
    config = load_config()
    config["backup_directory"] = path
    return save_config(config)

def configure_git_backup(enabled=True, repo=None, branch=None, username=None):
    """
    Configure Git backup settings
    
    Args:
        enabled: Whether Git backup is enabled
        repo: Git repository URL
        branch: Branch name
        username: Git username
        
    Returns:
        Boolean indicating success
    """
    config = load_config()
    
    git_config = config.get("git_backup", {})
    git_config["enabled"] = enabled
    
    if repo:
        git_config["repository"] = repo
    if branch:
        git_config["branch"] = branch
    if username:
        git_config["username"] = username
    
    config["git_backup"] = git_config
    return save_config(config)