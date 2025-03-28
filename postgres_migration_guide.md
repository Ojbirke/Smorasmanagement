# PostgreSQL Migration Guide

This guide explains how to migrate the Smørås Fotball application from SQLite to PostgreSQL for better database reliability during redeployments.

## Why PostgreSQL?

PostgreSQL offers several advantages over SQLite for this application:

1. **Better Concurrency**: Multiple users can write to the database simultaneously
2. **Improved Reliability**: Better transaction support prevents database corruption
3. **Enhanced Stability**: More robust during server redeployments and restarts
4. **Data Integrity**: Stronger constraint enforcement and validation
5. **Scalability**: Can handle larger datasets as the application grows

## Migration Process

The migration to PostgreSQL has been implemented with the following components:

1. **Updated Settings**: Django settings now automatically detect and use PostgreSQL when available
2. **Migration Script**: The `migrate_to_postgres.py` script transfers data from SQLite to PostgreSQL
3. **Backup Utilities**: Enhanced backup tools support PostgreSQL backups
4. **Safety Measures**: Multiple safety checks prevent data loss during migration

## How to Migrate

### Step 1: Prepare for Migration

Before migrating, ensure you have:

- A recent backup of your data
- The PostgreSQL connection details (provided by Replit)
- Required packages installed (`dj-database-url` and `psycopg2-binary`)

### Step 2: Run the Migration Script

```bash
cd smorasfotball
python migrate_to_postgres.py
```

This script will:
- Create a safety backup
- Count objects in the current database
- Set up the PostgreSQL schema
- Validate the migration was successful

### Step 3: Create PostgreSQL Backups

After migration, create a backup of your PostgreSQL database:

```bash
cd smorasfotball
python postgres_backup.py --deployment
```

This creates backups for regular use and deployment purposes.

## Deployment Configuration

The application is now configured to automatically use PostgreSQL when deployed:

1. If the `DATABASE_URL` environment variable is set, PostgreSQL is used
2. If not, the application falls back to SQLite (for development only)

This dual configuration ensures the application works in all environments.

## Backup and Restore

### PostgreSQL Backups

Regular backups are automated and stored in multiple locations:

- **Persistent Backups**: `/persistent_backups/` directory
- **Application Backups**: `/smorasfotball/backups/` directory
- **Deployment Backups**: `/deployment/` directory

### Restoring from Backup

The application's Database Recovery Wizard (`/team/recovery/`) supports PostgreSQL backups and can restore from:

1. JSON backups (via Django's loaddata)
2. SQL backups (via PostgreSQL utilities)

## Troubleshooting

If you encounter issues with PostgreSQL:

1. **Connection Issues**: Verify the `DATABASE_URL` environment variable is correct
2. **Migration Errors**: Check the migration log for specific error messages
3. **Missing Data**: Use the backup created before migration to recover data
4. **Performance Issues**: Ensure the database connection pool is properly configured