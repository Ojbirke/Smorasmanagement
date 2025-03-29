from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import connections
from django.db.utils import OperationalError
from django.conf import settings
from .models import Team, Player, Match, MatchAppearance, UserProfile
import os
import json
import sys
from datetime import datetime

def is_admin(user):
    """Check if user is an approved admin"""
    if not user.is_authenticated:
        return False
    try:
        return user.profile.is_admin() and user.profile.is_approved()
    except:
        return False

@login_required
def database_overview(request):
    """Display database statistics"""
    if not is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get database statistics
    stats = {
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
        'matches': Match.objects.count(),
        'appearances': MatchAppearance.objects.count(),
        'users': User.objects.count(),
        'profiles': UserProfile.objects.count()
    }
    
    has_data = any(count > 0 for count in stats.values())
    
    # Check database connection status
    is_postgres = 'postgresql' in settings.DATABASES['default']['ENGINE']
    
    # Attempt to check database connection
    db_connected = False
    try:
        # Use Django's connections built-in functionality
        connections['default'].ensure_connection()
        db_connected = True
    except OperationalError:
        db_connected = False
    
    # Build context for template
    context = {
        'stats': stats,
        'has_data': has_data,
        'is_postgres': is_postgres,
        'db_connected': db_connected,
        'db_name': settings.DATABASES['default'].get('NAME', 'Unknown'),
        'db_host': settings.DATABASES['default'].get('HOST', 'localhost'),
    }
    
    return render(request, 'teammanager/database_overview.html', context)