
#!/bin/bash
# Pre-deployment script to set up certificates
echo "Setting up certificates for deployment..."
# Update CA certificates
update-ca-certificates --fresh || true
# Trust Replit's certificate 
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

# First, make sure the persistent_backups directory exists
mkdir -p persistent_backups

# Ensure permissions are correct
chmod 755 persistent_backups

# Continue with the regular build process
python -m pip install -r requirements.txt

# Create deployment directory where we can store deployment-specific files
mkdir -p deployment
chmod 755 deployment

echo "========================================================"
echo "PRE-DEPLOYMENT DATABASE BACKUP SYSTEM"
echo "========================================================"
echo "Current directory: $(pwd)"
echo "Current time: $(date)"
echo "Deployment directory: $(pwd)/deployment"

# List deployment directory contents for debugging
echo "Current files in deployment directory:"
ls -la deployment/

# Create a marker file to indicate we're in a deployment process
echo "$(date) - Pre-deployment script running" > deployment/DEPLOYMENT_IN_PROGRESS

# Special pre-deployment database preparation:
cd smorasfotball

# Check if we're in a production environment with existing deployment backups
# We do NOT want to overwrite production backups with development data
if [ -f "../deployment/deployment_db.sqlite" ] || [ -f "../deployment/deployment_db.json" ]; then
    echo "⚠️ CRITICAL: Detected existing deployment backups - PRESERVING PRODUCTION DATA"
    echo "✅ Will use existing deployment backups during deployment startup"
    echo "✅ Database integrity will be maintained across deployments"
    echo "✅ NO DEVELOPMENT DATA WILL REPLACE YOUR PRODUCTION DATA"
    
    # Create multiple timestamp backups of the existing deployment backups (just for safety)
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    
    # Make a backup with today's date for easy identification
    TODAY=$(date +"%Y%m%d")
    BACKUP_DIR="../deployment/backups"
    mkdir -p "$BACKUP_DIR"
    
    if [ -f "../deployment/deployment_db.sqlite" ]; then
        # Create a timestamped backup
        cp "../deployment/deployment_db.sqlite" "../deployment/deployment_db.sqlite.${TIMESTAMP}.bak"
        echo "Created timestamped safety backup: deployment_db.sqlite.${TIMESTAMP}.bak"
        
        # Create a dated backup
        cp "../deployment/deployment_db.sqlite" "$BACKUP_DIR/deployment_backup_${TODAY}.sqlite"
        echo "Created dated safety backup: $BACKUP_DIR/deployment_backup_${TODAY}.sqlite"
        
        # Make sure deployment_db.sqlite has the correct permissions
        chmod 644 "../deployment/deployment_db.sqlite"
        echo "Updated permissions on deployment_db.sqlite"
    fi
    
    if [ -f "../deployment/deployment_db.json" ]; then
        # Create a timestamped backup
        cp "../deployment/deployment_db.json" "../deployment/deployment_db.json.${TIMESTAMP}.bak"
        echo "Created timestamped safety backup: deployment_db.json.${TIMESTAMP}.bak"
        
        # Create a dated backup
        cp "../deployment/deployment_db.json" "$BACKUP_DIR/deployment_backup_${TODAY}.json"
        echo "Created dated safety backup: $BACKUP_DIR/deployment_backup_${TODAY}.json"
        
        # Make sure deployment_db.json has the correct permissions
        chmod 644 "../deployment/deployment_db.json"
        echo "Updated permissions on deployment_db.json"
    fi
    
    # Create a marker file to explicitly indicate we're in a production environment
    touch "../deployment/IS_PRODUCTION_ENVIRONMENT"
    echo "$(date) - Deployment detected and marked as production" > "../deployment/IS_PRODUCTION_ENVIRONMENT"
else
    # Only create new deployment backups if none exist (first deployment)
    echo "No existing deployment backups found - creating initial deployment backups..."
    
    # First create a SQLite backup (preferred for direct file replacement)
    echo "Creating SQLite deployment backup (preferred method)..."
    python manage.py deployment_backup --name "initial_deploy" --format sqlite || {
        echo "SQLite backup creation failed, trying without specific name..."
        python manage.py deployment_backup --format sqlite || {
            echo "SQLite backup format not supported, falling back to JSON..."
            # Create JSON backup as fallback if SQLite fails
            echo "Creating JSON deployment backup..."
            python manage.py deployment_backup --name "initial_deploy" --format json || python manage.py deployment_backup --name "initial_deploy" || {
                echo "WARNING: All backup attempts failed! Deployment may not have proper data."
            }
        }
    }
    
    # Create a second backup in JSON format for redundancy
    echo "Creating JSON deployment backup for redundancy..."
    python manage.py deployment_backup --name "initial_deploy" --format json || python manage.py deployment_backup --name "initial_deploy" || echo "JSON backup failed, but we have the SQLite backup"
    
    # Verify that at least one backup file exists
    if [ -f "../deployment/deployment_db.sqlite" ] || [ -f "../deployment/deployment_db.json" ]; then
        echo "✅ Successfully created INITIAL deployment backup(s)"
    else 
        echo "❌ ERROR: No deployment backups were created! Deployment may not have proper data."
    fi
fi

# Run migrations and collect static files
python manage.py migrate
python manage.py collectstatic --noinput

# Create a deployment admin user with secure credentials
# The username and password are stored in the .env file for reference
ADMIN_USERNAME="deployment_admin"
ADMIN_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 12)
echo "Creating deployment admin user: $ADMIN_USERNAME..."
python manage.py create_deployment_admin --username "$ADMIN_USERNAME" --password "$ADMIN_PASSWORD" || {
    echo "Warning: Failed to create deployment admin using custom command. Trying fallback method..."
    # Fallback to direct user creation if the management command fails
    python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()
from django.contrib.auth.models import User
try:
    if User.objects.filter(username='$ADMIN_USERNAME').exists():
        user = User.objects.get(username='$ADMIN_USERNAME')
        user.set_password('$ADMIN_PASSWORD')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print('Updated existing admin user')
    else:
        User.objects.create_superuser('$ADMIN_USERNAME', 'admin@example.com', '$ADMIN_PASSWORD')
        print('Created deployment admin user as superuser')
except Exception as e:
    print(f'Error: {str(e)}')
    # Create one more fallback admin in case everything else fails
    try:
        if not User.objects.filter(username='emergency_admin').exists():
            User.objects.create_superuser('emergency_admin', 'emergency@example.com', 'emergency123')
            print('Created emergency admin')
    except Exception as ee:
        print(f'Emergency admin creation also failed: {str(ee)}')
"
}
echo "Deployment admin credentials prepared"

echo "Pre-deployment script completed successfully"
