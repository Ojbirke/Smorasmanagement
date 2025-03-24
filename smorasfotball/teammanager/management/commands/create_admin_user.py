from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from teammanager.models import UserProfile

class Command(BaseCommand):
    help = 'Creates a new admin user with approved status'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the admin user')
        parser.add_argument('email', type=str, help='Email for the admin user')
        parser.add_argument('password', type=str, help='Password for the admin user')
        parser.add_argument('--first-name', type=str, help='First name for the admin user')
        parser.add_argument('--last-name', type=str, help='Last name for the admin user')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')

        # Check if the user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists.'))
            return

        # Create the user - ensure first_name and last_name are never None
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name or "Admin",  # Default to "Admin" if not provided
            last_name=last_name or ""  # Use empty string if last_name is None
        )

        # Ensure the UserProfile is created (signal should handle this, but to be safe)
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        # Set as admin and approved
        profile.role = 'admin'
        profile.status = 'approved'
        profile.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully created admin user "{username}" with approved status.'))