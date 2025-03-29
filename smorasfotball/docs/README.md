# Smørås Fotball Documentation

This directory contains documentation for the Smørås Fotball application.

## Contents

- [PostgreSQL Backup System](postgres_backup_system.md): Comprehensive guide for the database backup system

## Additional Resources

For more information about the Smørås Fotball application, please refer to the following resources:

- Django Documentation: https://docs.djangoproject.com/
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Git Documentation: https://git-scm.com/doc

## Project Structure

The Smørås Fotball application is structured as follows:

- `smorasfotball/`: Main Django project directory
  - `teammanager/`: The main application for team management
  - `docs/`: Documentation files
  - `backups/`: Database backup files
  - `persistent_backups/`: Persistent backup files that survive redeployments
  - `deployment/`: Deployment-specific files, including deployment backups

## Management Commands

The application includes several custom management commands for various administrative tasks:

- `backup_postgres`: Creates PostgreSQL database backups
- `configure_backups`: Configures backup locations and settings
- `sync_backups_with_repo`: Synchronizes backups with a Git repository

For more information on how to use these commands, please refer to their specific documentation files or run:

```bash
python manage.py <command_name> --help
```

## Troubleshooting

If you encounter issues with the application, please check the following:

1. Ensure PostgreSQL is running and accessible
2. Verify that all required environment variables are set
3. Check the application logs for error messages
4. Consult the relevant documentation files in this directory

For additional assistance, please contact the development team.