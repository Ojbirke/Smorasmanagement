from django.apps import AppConfig
import sys


class TeammanagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'teammanager'
    
    def ready(self):
        # We've removed the automatic backup code since we're now using PostgreSQL
        # The database is automatically backed up by the Replit infrastructure
        pass
