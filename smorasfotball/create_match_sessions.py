#!/usr/bin/env python
"""
Create match sessions script for Smørås Fotball

This script creates match sessions for existing matches.
"""
import os
import sys
import django
import random
import datetime

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()

from django.utils import timezone
from teammanager.models import Match, MatchSession

def create_match_sessions():
    """
    Creates match sessions for existing matches
    """
    # Get matches
    matches = Match.objects.all()
    if not matches:
        print("No matches found. Please run create_match_data first.")
        return
    
    # Clean up existing match sessions
    MatchSession.objects.all().delete()
    
    # Create match sessions
    created_sessions = []
    for match in matches:
        # Create a match session for each match
        session = MatchSession.objects.create(
            match=match,
            name=f"Game Day {random.randint(1, 5)}",
            periods=2,
            period_length=25,
            substitution_interval=5,
            is_active=False,
            current_period=1,
            elapsed_time=0,
            start_time=timezone.now() - timezone.timedelta(hours=random.randint(1, 5))
        )
        created_sessions.append(session)
        print(f"Created match session: {session.name} for match {match}")
    
    # Activate one random session
    if created_sessions:
        active_session = random.choice(created_sessions)
        active_session.is_active = True
        active_session.save()
        print(f"\nActivated session: {active_session.name} for match {active_session.match}")
    
    print(f"\nCreated {len(created_sessions)} match sessions")

if __name__ == "__main__":
    create_match_sessions()