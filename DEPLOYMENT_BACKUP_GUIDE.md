# Smørås Fotball Deployment & Backup Guide

This document explains the database backup and restoration system for the Smørås Fotball application.

## Deployment Backup System Overview

The Smørås Fotball application includes a comprehensive backup system designed to prevent data loss during deployments and redeployments. The system includes several layers of protection:

1. **Pre-Deployment Backups**: The system creates backups before any deployment actions
2. **Git-Based Backup Storage**: Backups are stored in Git for reliable version control
3. **Deployment Protection**: Special protection for production deployments
4. **Automatic Restoration**: Intelligent restoration after deployments
5. **Safety Backups**: Multiple fallback mechanisms for data recovery
6. **Database Recovery Wizard**: User-friendly interface for database management
7. **PostgreSQL Integration**: Enhanced reliability with PostgreSQL database

## Key Components

### Backup Types

- **Regular Backups**: Standard database backups for everyday use
- **Deployment Backups**: Special backups used for deployment to production
- **Persistent Backups**: Backups that survive redeployments
- **Git Backups**: Backups stored in the Git repository
- **Safety Backups**: Pre-operation backups created automatically
- **PostgreSQL Backups**: Both JSON and SQL format backups for PostgreSQL

### Important Scripts

- `pre_deploy.sh`: Runs before deployment to create backups
- `deployment_protect.py`: Special safeguards for production deployments
- `auto_restore_after_deploy.py`: Restores database after deployment
- `run_auto_restore_with_protection.sh`: Runs both protection and restoration
- `mark_production.sh`: Marks an instance as production
- `postgres_backup.py`: Creates PostgreSQL-specific backups
- `migrate_to_postgres.py`: Migrates data from SQLite to PostgreSQL

## PostgreSQL Database System

The application now uses PostgreSQL as its primary database, which provides several key advantages:

1. **Improved Reliability**: PostgreSQL offers better transaction support and concurrency
2. **Enhanced Stability During Redeployments**: The external database connection prevents data loss
3. **Better Scalability**: PostgreSQL handles larger datasets and more concurrent users
4. **Automatic Fallback**: If PostgreSQL is unavailable, the system falls back to SQLite

### PostgreSQL Backup Formats

- **JSON Backups**: Created using Django's dumpdata command
- **SQL Backups**: Created using pg_dump when available
- **Multiple Backup Locations**: Backups stored in persistent, deployment, and application directories

## Deployment Protection System

The deployment protection system is designed to prevent accidental overwrites of production data. It includes several layers:

1. **Production Detection**: The system automatically detects if it's running in a production environment
2. **Content Validation**: All backups are checked for content before restoration
3. **Safe Fallback**: If a bad backup is detected, the system reverts to a known good state
4. **Size Checks**: Backups are checked for minimum size requirements
5. **Record Counts**: The number of teams, players, and users are verified 
6. **Last-Resort Recovery**: Multiple fallback options in case of failures
7. **Database-Specific Protection**: Special handling for PostgreSQL vs SQLite backups

## How Redeployment Works

When the application is redeployed, the following sequence occurs:

1. `pre_deploy.sh` creates a deployment backup (PostgreSQL or SQLite based on environment)
2. The backup is saved to the Git repository
3. The application is deployed to the new environment
4. `deployment_protect.py` runs to ensure database safety
5. `auto_restore_after_deploy.py` restores the database from the backup
6. The production marker is established for future runs

## Important Directory Structure

- `/deployment/`: Contains deployment backups and markers
- `/persistent_backups/`: Contains backups that survive redeployments
- `/smorasfotball/backups/`: Contains regular application backups

## Recovery Wizard

The Database Recovery Wizard provides a user-friendly interface for database management operations:

1. Access it at `/team/recovery/`
2. Follow the step-by-step process for assessing your database
3. Choose the backup source (Git, deployment, persistent, regular)
4. Select a specific backup file
5. Confirm and execute the restoration

## Special Notes for Production Environments

- Production environments have extra safeguards to prevent data loss
- The system will not allow a backup with fewer records to overwrite a database with more records
- Multiple safety copies are created before any restoration
- The system will detect and fix corrupted deployment backups
- PostgreSQL provides additional reliability for production deployments

## PostgreSQL Migration

The application includes a migration utility to transfer data from SQLite to PostgreSQL:

1. Run `python smorasfotball/migrate_to_postgres.py` to initiate migration
2. The script creates a safety backup before migration
3. All data is transferred to the PostgreSQL database
4. The script verifies that the migration was successful

## Troubleshooting

If you encounter issues with database restoration:

1. Check the logs in auto_restore_log.txt and deployment_protection_*.log
2. Look for the DEPLOYMENT_PROTECTED marker in the deployment directory
3. Use the Database Recovery Wizard to assess available backups
4. Check if any safety backups were created (pre_git_pull_backup, pre_deploy_backup)
5. For PostgreSQL issues, check the database connection string and SSL settings
6. If all else fails, use the Emergency Recovery option in the wizard

## PostgreSQL Connection Settings

The application uses the following environment variables for PostgreSQL connection:

- `DATABASE_URL`: The main connection string for PostgreSQL
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`: Individual connection parameters

These are automatically configured in the Replit environment.