
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

# Create a special pre-deployment backup that will be used for the deployment environment
# using our custom management command which handles all the details
python manage.py deployment_backup --name "predeploy"
echo "Created deployment database backup for use in the deployed application"

# Run migrations and collect static files
python manage.py migrate
python manage.py collectstatic --noinput

# Create a deployment admin user with secure credentials
# The username and password are stored in the .env file for reference
ADMIN_USERNAME="deployment_admin"
ADMIN_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 12)
python manage.py create_deployment_admin --username "$ADMIN_USERNAME" --password "$ADMIN_PASSWORD"
echo "Created deployment admin user: $ADMIN_USERNAME with secure password"

echo "Pre-deployment script completed successfully"
