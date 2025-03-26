import os
import sys
import django

# Set up Django environment
sys.path.append('smorasfotball')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()

# Import models
from django.contrib.auth.models import User
from teammanager.models import UserProfile

# Print user information
print(f'Users: {User.objects.count()}')
print('User details:')
for user in User.objects.all():
    print(f'  - {user.username} (Staff: {user.is_staff}, Superuser: {user.is_superuser})')

# Print user profile information
print(f'\nUser Profiles: {UserProfile.objects.count()}')
print('User Profile details:')
for profile in UserProfile.objects.all():
    print(f'  - {profile.user.username}: Role={profile.role}, Status={profile.status}')