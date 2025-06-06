#!/usr/bin/env python3
"""Recreate Django Superuser

This script recreates the Django superuser (djadmin) with default credentials
if it doesn't exist. Used for emergency recovery.
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

def recreate_superuser():
    """Creates or updates the superuser account"""
    username = 'djadmin'
    password = 'superuser123'
    email = 'admin@example.com'
    
    try:
        # Check if the user exists
        try:
            superuser = User.objects.get(username=username)
            print(f"Superuser '{username}' already exists.")
            
            # Reset the password
            superuser.set_password(password)
            superuser.email = email
            superuser.is_staff = True
            superuser.is_superuser = True
            superuser.save()
            print(f"Reset password for superuser '{username}'.")
        except User.DoesNotExist:
            # Create a new superuser
            User.objects.create_superuser(username=username, email=email, password=password)
            print(f"Created new superuser '{username}'.")
        
        # Make sure the user's UserProfile has admin privileges
        try:
            user = User.objects.get(username=username)
            profile = UserProfile.objects.get(user=user)
            profile.role = 'admin'
            profile.status = 'approved'
            profile.save()
            print(f"User '{username}' is now an approved admin in the application.")
        except UserProfile.DoesNotExist:
            # This shouldn't happen due to the signal, but just in case
            user = User.objects.get(username=username)
            UserProfile.objects.create(user=user, role='admin', status='approved')
            print(f"Created UserProfile for '{username}' as an approved admin.")
            
        return True
    except Exception as e:
        print(f"Error creating/updating superuser: {e}")
        return False

def main():
    """Main function"""
    print("Checking/recreating Django superuser...")
    success = recreate_superuser()
    
    if success:
        print("\nSuperuser account details:")
        print("- Username: djadmin")
        print("- Password: superuser123")
        print("- Role: Django Admin + Application Admin")
        print("\nLogin with these credentials to access the admin interface.")
    else:
        print("Failed to create/update superuser.")
        sys.exit(1)

if __name__ == "__main__":
    main()