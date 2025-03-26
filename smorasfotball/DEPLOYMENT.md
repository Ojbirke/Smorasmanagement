# Deployment Guide for Smørås G2015 Fotball

This guide provides instructions on how to safely deploy new versions of the Smørås G2015 Fotball application without losing your database data.

## Before Deployment

When you're running the application in production and need to deploy a new version, always follow these steps to protect your database:

### 1. Check Your Database

Run the following command to check how much data is in your database:

```
python manage.py check_database
```

This will show you how many teams, players, matches, and users are in your database.

### 2. Create a Backup

Before any deployment, create a backup of your database:

```
python manage.py check_database --backup
```

This will create a backup in the `backup` directory with a timestamp. Two files will be created:
- A JSON file with all your database content
- A copy of your SQLite database file

## Deploying a New Version

### Option 1: Simple Deployment (Recommended)

1. Deploy the new code without running the data population command:
   ```
   # Start the server without populating data
   python manage.py migrate  # Apply any database migrations
   python manage.py runserver  # Start the server
   ```

2. Check that everything is working as expected.

### Option 2: Clean Deployment with Data Restore

If you want to start with a fresh database but keep your data:

1. Create a backup as described above
2. Deploy the new code and start with a fresh database
3. Restore your data:
   ```
   python manage.py restore_database backup/your_backup_file.json
   ```

## After Deployment

1. Check that your application is working as expected
2. Verify that all your data is intact:
   ```
   python manage.py check_database
   ```

## Troubleshooting

### Data Loss During Deployment

If you accidentally lose data during deployment:

1. Stop the server
2. Restore from the most recent backup:
   ```
   python manage.py restore_database
   ```
   This will list all available backups. Then run:
   ```
   python manage.py restore_database backup/db_backup_YYYYMMDD_HHMMSS.json
   ```

3. Restart the server

### Database Migration Errors

If you encounter database migration errors:

1. Create a backup before attempting any fixes
2. Try running migrations with the `--fake` flag:
   ```
   python manage.py migrate --fake
   ```

## Production Environment Configuration

For a production environment, consider these additional settings:

1. Use a more robust database like PostgreSQL instead of SQLite
2. Configure proper email settings for password reset functionality
3. Set `DEBUG = False` in settings.py
4. Configure proper `ALLOWED_HOSTS` in settings.py
5. Set up a proper web server like Nginx or Apache with WSGI

Remember to always backup your database before making significant changes!