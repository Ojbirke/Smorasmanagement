#!/usr/bin/env python
"""
Create users script for Smørås Fotball

This script creates sample users with different roles.
"""
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()

from django.contrib.auth.models import User
from teammanager.models import Player, UserProfile

def create_users():
    """
    Creates sample users with different roles (admin, coach, player)
    """
    # Delete existing user profiles first
    UserProfile.objects.filter(user__is_superuser=False).delete()
    User.objects.filter(is_superuser=False).delete()
    
    # Create users
    user_data = [
        {
            "username": "coach1",
            "password": "smoras2025",
            "email": "coach@example.com",
            "first_name": "Coach",
            "last_name": "Eksempel",
            "role": "Coach",
            "status": "Approved"
        },
        {
            "username": "player1",
            "password": "smoras2025",
            "email": "player@example.com",
            "first_name": "Spiller",
            "last_name": "Eksempel",
            "role": "Player",
            "status": "Approved",
            "player": Player.objects.filter(active=True).first()
        }
    ]
    
    for user_info in user_data:
        # Extract role, status, and player info
        role = user_info.pop("role", "Player")
        status = user_info.pop("status", "Pending")
        player = user_info.pop("player", None)
        
        # Create user
        user = User.objects.create_user(**user_info)
        
        # Create profile
        profile = UserProfile.objects.create(
            user=user,
            role=role,
            status=status,
            player=player
        )
        
        print(f"Created user: {user.username} with role {role}")
    
    print("\nUser accounts created:")
    print("Coach: username='coach1', password='smoras2025'")
    print("Player: username='player1', password='smoras2025'")

if __name__ == "__main__":
    create_users()