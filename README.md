# Smørås Fotball Team Management

A Django-powered football team management platform for Smørås Fotball, providing tools for managing youth team development through advanced technological solutions.

## Key Features

- Team management with player tracking and statistics
- Match session management with substitution tracking
- Player performance monitoring and visualization
- Advanced matrix visualization showing which players have played together
- Secure multi-role authentication system
- Interactive lineup builder with formation management
- Database backup and restore system

## Deployment and Database Management

This application has a sophisticated backup and restoration system designed to maintain database integrity across deployments.

### Backup Types

1. **Deployment Backups**: Located in `/deployment` directory
   - These backups are specifically for production deployment
   - SQLite format (direct file copy) is preferred for reliability
   - JSON format provided as fallback
   - These backups are NEVER replaced during redeployment
   - Daily production backups are automatically created with date-stamped names
   - Only the 3 most recent backups are kept to save space

2. **Persistent Backups**: Located in `/persistent_backups` directory
   - Created automatically on startup and shutdown
   - Manual backups created via the UI
   - Both SQLite and JSON formats
   - Used as fallback if deployment backups aren't available

### Database Preservation During Deployment

- When you redeploy the application, your production database is automatically preserved
- Pre-deployment script detects existing deployment backups and keeps them intact
- Startup script prioritizes deployment backups during restoration
- This ensures your live data (teams, players, matches) is never overwritten by development data

### Backup Workflow

1. **First Deployment**:
   - Initial backup created from development database
   - This becomes the starting point for the production database

2. **Subsequent Deployments**:
   - Existing production backups are preserved
   - Production database is restored from these backups
   - Development data never replaces production data

3. **Automatic Backups**:
   - Daily production backups created automatically
   - Safety backups before each deployment
   - Automatic cleanup of older backups

### How to Create a Manual Backup

1. Go to the Database Overview page
2. Click "Create Backup Now"
3. The backup will be stored in the `/persistent_backups` directory

### Emergency Restoration

If needed, you can force a restoration from the most recent deployment backup by running:

```
cd smorasfotball
python manage.py deployment_backup --restore
```

## Development Setup

1. Clone the repository
2. Install the required packages: `pip install -r requirements.txt`
3. Change directory to smorasfotball: `cd smorasfotball`
4. Run migrations: `python manage.py migrate`
5. Create a superuser: `python manage.py createsuperuser`
6. Start the development server: `python manage.py runserver 0.0.0.0:5000`

## Admin Credentials

- Default Django Admin: Username: `djadmin` | Password: `superuser123`
- A deployment-specific admin is also created automatically during deployment