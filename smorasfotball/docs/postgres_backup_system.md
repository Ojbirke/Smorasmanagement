# PostgreSQL Backup System

This document provides comprehensive information about the PostgreSQL backup system for the Smørås Fotball application.

## Overview

The backup system automatically creates and manages backups of your PostgreSQL database in multiple locations for redundancy and safety. It supports both JSON exports (using Django's dumpdata) and SQL dumps (using pg_dump), providing flexibility for different restoration needs.

## Features

- **Multiple Backup Locations**: Stores backups in various locations for redundancy
- **Configurable Paths**: Set custom backup directories, including external paths
- **Git Integration**: Optionally synchronize backups with a Git repository
- **Automatic Cleanup**: Removes old backups to save space
- **Deployment Protection**: Creates special backups for use during deployment
- **Admin Interface**: Configure backups through the Django admin

## Backup Locations

Backups are stored in multiple locations by default:

1. **Primary Backup Directory**: Configured in `backup_config.json` (defaults to `~/smorasfotball_backups`)
2. **Project Backups**: Inside the `smorasfotball/backups` directory
3. **Persistent Backups**: In the `persistent_backups` directory at the project root
4. **Deployment Backups**: In the `deployment` directory at the project root (when using `--deployment` flag)

## Backup Types

The system creates two types of backup files:

1. **JSON Backups**: Created using Django's `dumpdata` command
   - Format: `backup_postgres_<timestamp>.json`
   - Suitable for Django loaddata operations
   - Preserves object relationships

2. **SQL Backups**: Created using `pg_dump` (if available)
   - Format: `backup_postgres_<timestamp>.sql`
   - Full database dump with schema and data
   - Suitable for direct PostgreSQL restoration

## Using the Backup System

### Command Line Tools

#### Creating Backups

To create a standard backup:

```bash
python manage.py backup_postgres
```

To create a deployment backup (for use after redeployment):

```bash
python manage.py backup_postgres --deployment
```

Advanced options:

```bash
# Create only JSON backups (no SQL dump)
python manage.py backup_postgres --json-only

# Create only SQL backups (no JSON export)
python manage.py backup_postgres --sql-only

# Store backups in a custom directory
python manage.py backup_postgres --output-dir /path/to/backups
```

#### Testing Backup Configuration

```bash
# Show current backup configuration
python manage.py configure_backups --show-config

# Test if backup directories are writable
python manage.py configure_backups --test-backup-dir

# Test PostgreSQL connection and backup capabilities
python manage.py configure_backups --test-postgres
```

#### Configuring Backup Locations

```bash
# Set primary backup directory
python manage.py configure_backups --set-backup-path /path/to/backups

# Add a secondary backup location
python manage.py configure_backups --add-location backup2:/path/to/backup2

# Remove a secondary backup location
python manage.py configure_backups --remove-location backup2
```

#### Configuring Git Integration

```bash
# Enable Git backup with repository URL
python manage.py configure_backups --enable-git --git-repo https://github.com/username/repo.git

# Set Git branch
python manage.py configure_backups --git-branch main

# Set Git username (if needed for authentication)
python manage.py configure_backups --git-username your-username

# Disable Git backup
python manage.py configure_backups --disable-git
```

#### Syncing Backups with Git

```bash
# Push backups to Git repository
python manage.py sync_backups_with_repo --push

# Pull backups from Git repository
python manage.py sync_backups_with_repo --pull

# Pull backups safely (don't overwrite existing)
python manage.py sync_backups_with_repo --pull --safe

# Use a separate backup repository instead of main repo
python manage.py sync_backups_with_repo --pull --backup-repo https://github.com/username/backups.git
```

### Admin Interface

The backup system can also be configured through the Django admin interface:

1. Log in to the Django admin site
2. Click on "Backup Configuration" in the sidebar
3. Configure backup paths, Git repository settings, and other options
4. Click "Save Configuration" to apply changes
5. Use "Test Backup Paths" to verify your configuration

## Configuration File

The backup system is configured through the `backup_config.json` file, which is created automatically with default settings. You can edit this file manually or use the command-line tools or admin interface to update it.

Example configuration:

```json
{
  "backup_directory": "~/smorasfotball_backups",
  "backup_locations": [
    {
      "name": "persistent",
      "path": "persistent_backups",
      "enabled": true,
      "max_backups": 5
    },
    {
      "name": "deployment",
      "path": "deployment",
      "enabled": true,
      "max_backups": 3
    }
  ],
  "git_backup": {
    "enabled": false,
    "repository": "https://github.com/username/smorasfotball-backups.git",
    "branch": "main",
    "username": ""
  }
}
```

## Automatic Backups

The system automatically creates the following backups:

1. **Startup Backups**: Created when the server starts
2. **Deployment Backups**: Created during the deployment process
3. **Manual Backups**: Created when you run the backup commands

## Backup Rotation

To prevent excessive disk usage, the system automatically removes old backups, keeping only the most recent ones. By default, it keeps the latest 5 backups of each type in each location, but this can be configured through the `max_backups` setting.

## Best Practices

1. **Regular Backups**: Create backups regularly, especially before major changes
2. **Multiple Locations**: Store backups in multiple locations (external drives, cloud storage)
3. **Test Restoration**: Periodically test restoring from backups to ensure they work
4. **Secure Storage**: Keep backup files secure, especially those containing sensitive data
5. **Git Integration**: Use a private Git repository for additional backup redundancy

## Troubleshooting

### Backup Fails with Database Connection Error

Ensure that:
- PostgreSQL is running
- The `DATABASE_URL` environment variable is set
- Database credentials are correct

### pg_dump Not Available

If SQL backups are not being created:

1. Install the PostgreSQL client tools
2. Ensure `pg_dump` is in your PATH
3. If pg_dump cannot be installed, use the `--json-only` flag to create only JSON backups

### Git Synchronization Fails

For issues with Git integration:

1. Verify that Git is installed and configured
2. Check that the repository URL is correct
3. Ensure you have proper authentication (GitHub token, SSH keys)
4. Set the `GITHUB_TOKEN` environment variable if needed

## Support

For additional support with the backup system, contact the development team or consult the Django documentation for more information about database operations and management.