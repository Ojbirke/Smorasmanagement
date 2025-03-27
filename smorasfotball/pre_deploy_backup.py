
from django.core.management import call_command

def backup():
    try:
        call_command('persistent_backup', name='pre_deploy')
        print("Pre-deployment backup created successfully")
    except Exception as e:
        print(f"Error creating pre-deployment backup: {e}")
