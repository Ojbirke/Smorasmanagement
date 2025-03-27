
#!/bin/bash
# Pre-deployment script to set up certificates
echo "Setting up certificates for deployment..."
# Update CA certificates
update-ca-certificates --fresh || true
# Trust Replit's certificate 
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

# Continue with the regular build process
python -m pip install -r requirements.txt && mkdir -p deployment && cd smorasfotball && python manage.py migrate && python manage.py collectstatic --noinput
