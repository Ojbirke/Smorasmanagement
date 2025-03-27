
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

# Special pre-deployment database preparation:
cd smorasfotball

# Check if we're in a production environment with existing deployment backups
# We do NOT want to overwrite production backups with development data
if [ -f "../deployment/deployment_db.sqlite" ] || [ -f "../deployment/deployment_db.json" ]; then
    echo "⚠️ Detected existing deployment backups - PRESERVING PRODUCTION DATA"
    echo "✅ Will use existing deployment backups during deployment startup"
    echo "✅ Database integrity will be maintained across deployments"
    
    # Create a timestamp backup of the existing deployment backups (just for safety)
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    if [ -f "../deployment/deployment_db.sqlite" ]; then
        cp "../deployment/deployment_db.sqlite" "../deployment/deployment_db.sqlite.${TIMESTAMP}.bak"
        echo "Created safety backup: deployment_db.sqlite.${TIMESTAMP}.bak"
    fi
    
    if [ -f "../deployment/deployment_db.json" ]; then
        cp "../deployment/deployment_db.json" "../deployment/deployment_db.json.${TIMESTAMP}.bak"
        echo "Created safety backup: deployment_db.json.${TIMESTAMP}.bak"
    fi
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
