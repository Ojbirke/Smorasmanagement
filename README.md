# Smørås Fotball Team Management System

A comprehensive Django-powered football team management platform designed for Smørås Fotball youth teams.

## Features

- **Team Management**: Create and manage multiple teams within your club
- **Player Management**: Track player information, team assignments, and statistics
- **Match Sessions**: Record match participation, track play time, and manage periods
- **Formation Templates**: Pre-built formations for different team sizes (5er, 7er, 9er, 11er)
- **Statistics Dashboard**: Visual representations of player participation and team dynamics
- **Video Integration**: Record match highlights and create video reels
- **Database Protection**: Multi-layer system to protect data during redeployments
- **PostgreSQL Support**: Enhanced database reliability with PostgreSQL integration

## System Architecture

The application is built with Django and offers:

- **Multi-User Support**: Different roles for coaches, players, and administrators
- **Responsive Design**: Works on mobile devices for sideline use
- **Data Visualization**: Interactive matrices showing player combinations
- **Data Import/Export**: Easy data exchange with Excel spreadsheets
- **Intelligent Backup System**: Prevents data loss during redeployments

## PostgreSQL Database Integration

The application now uses PostgreSQL as its primary database for enhanced reliability:

- **Improved Stability**: Better handling of database connections during redeployments
- **Transaction Support**: Stronger data integrity protection
- **Concurrent Access**: Support for multiple simultaneous users
- **Automatic Fallback**: Falls back to SQLite if PostgreSQL is unavailable

## Deployment and Backup System

The application includes a robust backup and restoration system:

- **Pre-Deployment Backups**: Automatic backups before any deployment
- **Multiple Backup Formats**: Support for JSON and SQL database backups
- **Intelligent Restoration**: Smart backup selection based on content quality
- **Recovery Wizard**: User-friendly interface for database management

For detailed information on the backup system, see [DEPLOYMENT_BACKUP_GUIDE.md](DEPLOYMENT_BACKUP_GUIDE.md).

## Technical Documentation

### PostgreSQL Migration

To migrate existing data from SQLite to PostgreSQL:

```bash
python smorasfotball/migrate_to_postgres.py
```

### Creating PostgreSQL Backups

To create a backup of the PostgreSQL database:

```bash
python smorasfotball/postgres_backup.py
```

Add the `--deployment` flag to create a deployment backup:

```bash
python smorasfotball/postgres_backup.py --deployment
```

### Development Setup

1. Install required packages:
   ```bash
   pip install django pandas openpyxl reportlab dj-database-url psycopg2-binary
   ```

2. Run database migrations:
   ```bash
   cd smorasfotball
   python manage.py migrate
   ```

3. Create test data:
   ```bash
   python create_test_data.py
   python create_formations.py
   ```

4. Start the development server:
   ```bash
   python manage.py runserver 0.0.0.0:5000
   ```

## Admin Access

The superuser account has the following credentials:
- Username: djadmin
- Password: superuser123