#!/usr/bin/env python
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
sys.path.insert(0, 'smorasfotball')
django.setup()

# Now you can import Django models
from django.contrib.auth.models import User
from teammanager.models import UserProfile

# Create the superuser
username = 'djadmin'
password = 'superuser123'
email = 'admin@example.com'  # You can change this to your email if needed

# Check if user already exists
if User.objects.filter(username=username).exists():
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"Updated existing superuser '{username}' with the specified password.")
else:
    # Create a new superuser
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f"Created new superuser '{username}' with the specified password.")

# Ensure UserProfile exists and is properly configured
try:
    try:
        profile = user.profile
    except (UserProfile.DoesNotExist, AttributeError):
        profile = UserProfile.objects.create(user=user)
        print(f"Created new UserProfile for {username}")

    # Try the new profile schema first (role/status)
    try:
        # Set as admin and approved
        profile.role = 'admin'
        profile.status = 'approved'
        profile.save()
        print(f"User profile set to admin role with approved status.")
    except Exception as e:
        print(f"Error using new profile schema: {str(e)}")
        # Fall back to the legacy profile schema if needed
        try:
            profile.is_coach = True
            profile.is_approved = True
            profile.save()
            print(f"User profile set to coach role with approved status (legacy schema).")
        except Exception as legacy_error:
            print(f"Error using legacy profile schema: {str(legacy_error)}")
            print("Profile updates failed, but superuser access should still work.")
except Exception as profile_error:
    print(f"Warning: Could not configure user profile: {str(profile_error)}")
    print("Superuser should still be able to access the admin panel.")

print("=" * 60)
print(f"Superuser '{username}' is now ready to use.")
print(f"Password: {password}")
print(f"Login at: http://localhost:5000/admin/ or http://yourdomain.com/admin/")
print("=" * 60)