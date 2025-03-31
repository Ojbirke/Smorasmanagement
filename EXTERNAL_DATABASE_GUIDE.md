# External PostgreSQL Database Guide

This guide explains how to set up and use an external PostgreSQL database with the Smørås Fotball application instead of using SQLite or Replit's PostgreSQL.

## Why Use an External Database?

1. **Data Persistence**: External databases are more reliable for long-term data storage
2. **Performance**: Dedicated PostgreSQL databases often offer better performance
3. **Control**: More control over database configuration and backup strategies
4. **Integration**: Can integrate with existing systems

## Setup Process

### 1. Configure the Database Connection

Run the configuration script:

```bash
python configure_external_postgres.py
```

This script will:
- Ask for your database connection details
- Create a `.env` file with the DATABASE_URL
- Create markers to disable automatic SQLite-to-PostgreSQL migration
- Configure the application to use your external database

Alternatively, you can provide the connection details as command-line arguments:

```bash
python configure_external_postgres.py myteamsno_smorasg2015 your-hostname database-user password 5432
```

### 2. Test the Connection

Test that your database connection works:

```bash
python test_external_database.py
```

This will verify that:
- The database is accessible
- Proper credentials are being used
- The connection is stable

### 3. Modify WSGI for Deployment

Ensure the deployment will use your external database:

```bash
python modify_wsgi_for_external_db.py
```

This script modifies the WSGI configuration to load environment variables from the `.env` file during deployment.

### 4. Run Pre-Deployment Script

Before deploying, run:

```bash
bash pre_deploy_external_db.sh
```

This script:
- Creates necessary marker files to skip database restoration
- Ensures the DATABASE_URL is properly configured
- Prepares the application for deployment

### 5. Deploy the Application

Deploy your application through Replit's deployment interface.

### 6. Initial Database Setup

After deployment, run the following commands in your deployed application:

```bash
cd smorasfotball
python manage.py migrate
python manage.py createsuperuser
```

This will:
- Create all necessary database tables
- Set up a superuser for administrative access

## Troubleshooting

### 1. Connection Issues

If you're having trouble connecting to the external database:

- Verify the connection details (hostname, port, username, password)
- Check if your database server allows connections from the deployment environment
- Ensure the database user has appropriate permissions

### 2. Migration Issues

If migrations fail:

- Check the database logs for specific errors
- Verify that the database user has permission to create tables
- Try running migrations with the `--fake-initial` flag if tables already exist

### 3. Environment Variable Issues

If the application can't find the DATABASE_URL:

- Check the `.env` file to ensure it contains the correct URL
- Verify that the WSGI file was properly modified
- Try setting the environment variable manually in the deployment environment

## Managing Your Database

### Backing Up Data

To back up your external database:

```bash
pg_dump -h your-hostname -U username -d myteamsno_smorasg2015 -f backup.sql
```

### Restoring Data

To restore from a backup:

```bash
psql -h your-hostname -U username -d myteamsno_smorasg2015 -f backup.sql
```

## Important Notes

1. **Keep Credentials Secure**: Never commit your database credentials to the repository
2. **Regular Backups**: Set up regular backups of your external database
3. **Monitor Performance**: Keep an eye on database performance and resource usage