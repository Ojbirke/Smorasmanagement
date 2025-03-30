#!/usr/bin/env python
"""Create a superuser for development testing"""

import os

if __name__ == '__main__':
    # Django setup
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
    import django
    django.setup()
    
    from django.contrib.auth.models import User
    
    username = 'devadmin'
    email = 'dev@example.com'
    password = 'devpassword123'
    
    # Create superuser if it doesn't exist
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"Superuser {username} created successfully")
    else:
        user = User.objects.get(username=username)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f"Superuser {username} updated successfully")
    
    print(f"Superuser credentials: {username} / {password}")