from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from teammanager.models import UserProfile

class Command(BaseCommand):
    help = 'Updates an existing user\'s role and status'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user to update')
        parser.add_argument('--role', type=str, choices=['player', 'coach', 'admin'], 
                          default='admin', help='Role to assign (default: admin)')
        parser.add_argument('--status', type=str, choices=['pending', 'approved', 'rejected'], 
                          default='approved', help='Status to assign (default: approved)')

    def handle(self, *args, **options):
        username = options['username']
        role = options['role']
        status = options['status']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" does not exist.'))
            return

        # Ensure the UserProfile is created
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        # Update role and status
        profile.role = role
        profile.status = status
        profile.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated user "{username}" with role "{role}" and status "{status}".'
            )
        )