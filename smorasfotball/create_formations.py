#!/usr/bin/env python
"""
Create formation templates for Smørås Fotball
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smorasfotball.settings')
django.setup()

from teammanager.models import FormationTemplate

def create_formations():
    """
    Creates standard formation templates for different player counts
    """
    # Define the formations
    formations = [
        # 5er fotball
        {"name": "2-2 (5er)", "structure": "2-2", "player_count": 5, "description": "Standard 5er formation med 2 forsvarere og 2 angripere"},
        {"name": "1-2-1 (5er)", "structure": "1-2-1", "player_count": 5, "description": "5er formation med midtbanespillere"},
        {"name": "1-1-2 (5er)", "structure": "1-1-2", "player_count": 5, "description": "5er formation med fokus på angrep"},
        {"name": "2-1-1 (5er)", "structure": "2-1-1", "player_count": 5, "description": "5er formation med fokus på forsvar"},
        
        # 7er fotball
        {"name": "2-3-1 (7er)", "structure": "2-3-1", "player_count": 7, "description": "Standard 7er formation med midtbanefokus"},
        {"name": "3-2-1 (7er)", "structure": "3-2-1", "player_count": 7, "description": "7er formation med sterkt forsvar"},
        {"name": "3-1-2 (7er)", "structure": "3-1-2", "player_count": 7, "description": "7er formation med to angripere"},
        {"name": "2-1-3 (7er)", "structure": "2-1-3", "player_count": 7, "description": "7er formation med sterkt angrep"},
        {"name": "2-2-2 (7er)", "structure": "2-2-2", "player_count": 7, "description": "Balansert 7er formation"},
        {"name": "3-3 (7er)", "structure": "3-3", "player_count": 7, "description": "Klassisk 7er formation uten spiss"},
        {"name": "2-4 (7er)", "structure": "2-4", "player_count": 7, "description": "Offensiv 7er formation"},
        {"name": "4-2 (7er)", "structure": "4-2", "player_count": 7, "description": "Defensiv 7er formation"},
        
        # 9er fotball
        {"name": "3-2-3 (9er)", "structure": "3-2-3", "player_count": 9, "description": "Balansert 9er formation"},
        {"name": "3-3-2 (9er)", "structure": "3-3-2", "player_count": 9, "description": "Standard 9er formation med midtbanefokus"},
        {"name": "3-4-1 (9er)", "structure": "3-4-1", "player_count": 9, "description": "9er formation med sterk midtbane"},
        {"name": "4-3-1 (9er)", "structure": "4-3-1", "player_count": 9, "description": "Defensiv 9er formation"},
        
        # 11er fotball
        {"name": "4-4-2 (11er)", "structure": "4-4-2", "player_count": 11, "description": "Klassisk 11er formation"},
        {"name": "4-3-3 (11er)", "structure": "4-3-3", "player_count": 11, "description": "Offensiv 11er formation"},
        {"name": "4-2-3-1 (11er)", "structure": "4-2-3-1", "player_count": 11, "description": "Moderne 11er formation"},
        {"name": "3-5-2 (11er)", "structure": "3-5-2", "player_count": 11, "description": "11er formation med wingbacks"},
        {"name": "5-3-2 (11er)", "structure": "5-3-2", "player_count": 11, "description": "Defensiv 11er formation med sweeper"},
        {"name": "3-4-3 (11er)", "structure": "3-4-3", "player_count": 11, "description": "Offensiv 11er formation med tre angripere"},
    ]
    
    # Create the formations
    created_count = 0
    for formation in formations:
        # Skip if it already exists
        if FormationTemplate.objects.filter(name=formation["name"]).exists():
            print(f"Formation {formation['name']} already exists, skipping.")
            continue
            
        # Create the formation
        template = FormationTemplate.objects.create(
            name=formation["name"],
            formation_structure=formation["structure"],
            player_count=formation["player_count"],
            description=formation["description"]
        )
        print(f"Created formation: {template}")
        created_count += 1
    
    print(f"\nCreated {created_count} new formation templates.")

if __name__ == "__main__":
    print("Creating formation templates...")
    create_formations()
    print("Done.")