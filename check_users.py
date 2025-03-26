#!/usr/bin/env python
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
sys.path.insert(0, 'smorasfotball')
django.setup()

# Import Django models
from django.contrib.auth.models import User
from teammanager.models import UserProfile

# Count and list all users
users = User.objects.all()
print(f"Total users in database: {users.count()}")

# List superusers
superusers = User.objects.filter(is_superuser=True)
print(f"Superusers: {superusers.count()}")
for su in superusers:
    print(f" - {su.username} (Email: {su.email}, Active: {su.is_active})")

# List regular users with profiles
regular_users = User.objects.filter(is_superuser=False)
print(f"\nRegular users: {regular_users.count()}")
for user in regular_users:
    try:
        profile = user.profile
        role = profile.role
        status = profile.status
    except UserProfile.DoesNotExist:
        role = "No profile"
        status = "N/A"
    
    print(f" - {user.username} (Email: {user.email}, Role: {role}, Status: {status})")

print("\nDone.")