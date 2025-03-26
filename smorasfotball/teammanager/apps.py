from django.apps import AppConfig
import os
import sys
import atexit


class TeammanagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'teammanager'
    
    def ready(self):
        # Avoid running this when manage.py is called with certain commands
        if 'runserver' in sys.argv or 'runproduction' in sys.argv:
            # Import here to avoid AppRegistryNotReady error
            from django.core.management import call_command
            from django.db import connections
            from django.core.exceptions import ImproperlyConfigured
            from teammanager.models import Team, Player
            
            # Check if there's data worth backing up
            try:
                team_count = Team.objects.count()
                player_count = Player.objects.count()
                
                # If we have data, register an exit handler to create a backup when the server stops
                if team_count > 0 or player_count > 0:
                    def create_persistent_backup():
                        try:
                            # Close DB connections before backup
                            connections.close_all()
                            print("Creating persistent backup on server shutdown...")
                            call_command('persistent_backup', name='auto_shutdown')
                            print("Persistent backup completed successfully")
                        except Exception as e:
                            print(f"Error creating persistent backup: {str(e)}")
                    
                    # Register the function to be called when the server exits
                    atexit.register(create_persistent_backup)
                    
                    # Also create a backup at startup to ensure we have a fresh one
                    if not os.environ.get('BACKUP_CREATED_ON_STARTUP'):
                        print("Creating persistent backup on server startup...")
                        call_command('persistent_backup', name='auto_startup')
                        os.environ['BACKUP_CREATED_ON_STARTUP'] = '1'
                        print("Persistent backup completed successfully")
            except (ImproperlyConfigured, Exception) as e:
                # This might happen during migrations or if DB isn't set up yet
                print(f"Skipping automatic backup check: {str(e)}")
