#!/usr/bin/env python3
"""Create Production Admin User

This script creates a production admin user for the Smørås Football application.
It will:
1. Create a superuser in Django's auth system
2. Create/update the corresponding UserProfile with admin privileges
3. Ensure the user is approved in the system

Usage:
    python create_production_admin.py
"""

import os
import sys

# Add Django project to path
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smorasfotball')
sys.path.append(BASE_DIR)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')

try:
    import django
    django.setup()
    from django.contrib.auth.models import User
    from teammanager.models import UserProfile
except ImportError:
    print("Error: Django could not be imported. Make sure Django is installed.")
    sys.exit(1)

def create_production_admin():
    """Creates or updates the production admin user account"""
    username = 'prodadmin'
    password = 'smoras2015admin'
    email = 'admin@smorasfotball.no'
    first_name = 'Production'
    last_name = 'Admin'
    
    try:
        # Check if the user exists
        try:
            admin_user = User.objects.get(username=username)
            print(f"Admin user '{username}' already exists.")
            
            # Reset the password and update details
            admin_user.set_password(password)
            admin_user.email = email
            admin_user.first_name = first_name
            admin_user.last_name = last_name
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.save()
            print(f"Reset password and updated details for admin user '{username}'.")
        except User.DoesNotExist:
            # Create a new superuser
            admin_user = User.objects.create_superuser(
                username=username, 
                email=email, 
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            print(f"Created new admin user '{username}'.")
        
        # Make sure the UserProfile is set up correctly
        profile = UserProfile.objects.get(user=admin_user)
        profile.role = 'admin'
        profile.status = 'approved'
        profile.save()
        print(f"Updated UserProfile for '{username}' to be an approved admin.")
        
        return True
    except Exception as e:
        print(f"Error creating/updating admin user: {e}")
        return False

def main():
    """Main function"""
    print("Creating production admin user...")
    success = create_production_admin()
    
    if success:
        print("\nProduction admin account details:")
        print("- Username: prodadmin")
        print("- Password: smoras2015admin")
        print("- Role: Django Superuser + Application Admin")
        print("\nLogin with these credentials to access the admin interface in production.")
        
        # Also recreate the devadmin user for good measure
        try:
            dev_user = User.objects.get(username='devadmin')
            dev_user.set_password('devpassword123')
            dev_user.is_staff = True
            dev_user.is_superuser = True
            dev_user.is_active = True
            dev_user.save()
            
            dev_profile = UserProfile.objects.get(user=dev_user)
            dev_profile.role = 'admin'
            dev_profile.status = 'approved'
            dev_profile.save()
            print("\nDev admin account also updated:")
            print("- Username: devadmin")
            print("- Password: devpassword123")
        except Exception as e:
            print(f"Note: Could not update devadmin user: {e}")
    else:
        print("Failed to create/update production admin user.")
        sys.exit(1)

if __name__ == "__main__":
    main()