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

# Let's try updating an existing user
try:
    # See if the coach user exists and update it
    user = User.objects.get(username='coach')
    user.set_password('coach123')  # Set password to coach123
    user.save()
    
    # Make sure the profile is set to admin and approved
    profile = UserProfile.objects.get(user=user)
    profile.role = 'admin'
    profile.status = 'approved'
    profile.save()
    
    print("Updated coach user with password: coach123")
    print("Role set to admin, status set to approved")
except User.DoesNotExist:
    print("Coach user does not exist")

# Let's try a different user - 'testadmin'
try:
    user = User.objects.get(username='testadmin')
    user.set_password('admin123')  # Set password to admin123
    user.save()
    
    # Make sure the profile is set to admin and approved
    profile = UserProfile.objects.get(user=user)
    profile.role = 'admin'
    profile.status = 'approved'
    profile.save()
    
    print("Updated testadmin user with password: admin123")
    print("Role set to admin, status set to approved")
except User.DoesNotExist:
    print("Testadmin user does not exist")

print("Done.")