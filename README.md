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
- The system uses a GitHub-based backup synchronization mechanism to ensure backups persist across deployments
- Pre-deployment script pulls the latest backups from the repository before checking for existing deployment backups
- Startup script prioritizes deployment backups during restoration
- Any new backups created are automatically pushed to the repository for persistence
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

If the automatic restoration fails during redeployment, you have several options:

1. **Use the Standard Command**:
   ```
   cd smorasfotball
   python manage.py deployment_backup --restore
   ```

2. **Use the Force Restore Script** (more aggressive direct file copy approach):
   ```
   python force_deployment_restore.py
   ```
   
   Options:
   - `--dry-run`: Show what would be done without making changes
   - `--verbose`: Show detailed information

3. **Reset the Deployment Backup Environment** (for testing only):
   ```
   python reset_deployment_backups.py
   ```
   
   Options:
   - `--dry-run`: Show what would be done without making changes
   - `--force`: Skip confirmation prompt
   - `--keep-backups`: Create new backups without deleting existing ones
   
4. **Simulate a Deployment** (for testing the deployment process):
   ```
   ./simulate_deployment.sh
   ```
   This script runs the same steps as a real deployment to verify that the system works correctly.

5. **Test GitHub-based Backup Sync**:
   ```
   python test_backup_sync.py
   ```
   This script tests the GitHub-based backup synchronization system by creating a backup, pushing it to the repository, simulating a redeployment, and then pulling the backup from the repository.

### GitHub-based Backup Sync System

The application now uses GitHub as a persistent storage solution for deployment backups:

1. **Automatic Push**: When a backup is created, it's automatically pushed to the repository via the `sync_backups_with_repo` command.

2. **Automatic Pull**: During deployment, the system pulls the latest backups from the repository before checking for existing deployment backups.

3. **Manual Commands**:
   - Push backups to repository: `python manage.py sync_backups_with_repo --push`
   - Pull backups from repository: `python manage.py sync_backups_with_repo --pull`

This ensures that backups persist across deployments even if the deployment process overwrites the files in the deployment directory.

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