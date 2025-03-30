"""
Create Development Superuser

This script creates a development superuser account for testing in the web view environment.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

User = get_user_model()

def create_dev_admin():
    """Create a development superuser for testing"""
    username = 'devadmin'
    email = 'dev@example.com'
    password = 'devpassword123'
    
    try:
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            print(f"User {username} already exists. Updating to superuser status.")
            user.is_staff = True
            user.is_superuser = True
            user.save()
        else:
            # Create new superuser
            User.objects.create_superuser(username=username, email=email, password=password)
            print(f"Superuser '{username}' created successfully.")
        
        print(f"Superuser credentials: Username: {username} | Password: {password}")
    
    except IntegrityError:
        print(f"Error: User '{username}' could not be created. Username may already be taken.")
    except Exception as e:
        print(f"Error creating superuser: {e}")

if __name__ == '__main__':
    create_dev_admin()