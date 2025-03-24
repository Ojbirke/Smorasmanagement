from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from teammanager.models import UserProfile

class Command(BaseCommand):
    help = 'Reset a user password and optionally update their role and status'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user to update')
        parser.add_argument('password', type=str, help='New password for the user')
        parser.add_argument('--role', type=str, choices=['player', 'coach', 'admin'], help='Role to assign to the user')
        parser.add_argument('--status', type=str, choices=['pending', 'approved', 'rejected'], help='Status to assign to the user')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        role = options.get('role')
        status = options.get('status')
        
        try:
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully updated password for user: {username}'))
            
            if role or status:
                try:
                    profile = UserProfile.objects.get(user=user)
                    if role:
                        profile.role = role
                    if status:
                        profile.status = status
                    profile.save()
                    self.stdout.write(self.style.SUCCESS(f'Successfully updated profile for user: {username}'))
                except UserProfile.DoesNotExist:
                    if role and status:
                        UserProfile.objects.create(user=user, role=role, status=status)
                        self.stdout.write(self.style.SUCCESS(f'Created new profile for user: {username}'))
                    else:
                        self.stdout.write(self.style.WARNING('User profile does not exist. Please provide both --role and --status to create a new profile.'))
                        
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with username {username} does not exist'))