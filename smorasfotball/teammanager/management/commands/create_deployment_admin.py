import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from teammanager.models import UserProfile

class Command(BaseCommand):
    help = 'Creates a deployment admin user for the deployed application'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin')
        parser.add_argument('--password', type=str, default='admin123')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        
        try:
            # Check if user exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f'User {username} already exists, updating password'))
                user = User.objects.get(username=username)
                user.set_password(password)
                user.save()
            else:
                # Create superuser
                user = User.objects.create_superuser(
                    username=username,
                    email='admin@smorasfotball.no',
                    password=password
                )
                self.stdout.write(self.style.SUCCESS(f'Created superuser: {username}'))
            
            # Create or update user profile with admin role
            try:
                profile, created = UserProfile.objects.get_or_create(user=user)
                # For the UserProfile model, we need to set the appropriate roles
                profile.role = 'admin'  # Set as admin
                profile.status = 'approved'  # Auto-approve the admin
                profile.save()
                self.stdout.write(self.style.SUCCESS('Admin user profile set up successfully'))
            except Exception as profile_error:
                self.stdout.write(self.style.WARNING(f'User profile creation failed: {str(profile_error)}'))
                # Try alternative approach if the UserProfile schema is different
                try:
                    # Maybe the model uses older attributes
                    profile, created = UserProfile.objects.get_or_create(user=user)
                    profile.is_coach = True
                    profile.is_approved = True
                    profile.save()
                    self.stdout.write(self.style.SUCCESS('Admin user profile set up successfully (legacy format)'))
                except Exception as alt_error:
                    self.stdout.write(self.style.ERROR(f'Alternative profile setup also failed: {str(alt_error)}'))
            
            self.stdout.write(self.style.SUCCESS(f'Admin user setup completed for deployment environment'))
            
            # Create a .env file with the admin credentials to avoid losing them
            try:
                env_path = os.path.join(os.path.dirname(settings.BASE_DIR), '.env')
                with open(env_path, 'a') as f:
                    f.write(f'\n# Deployment admin credentials\n')
                    f.write(f'DEPLOYMENT_ADMIN_USERNAME="{username}"\n')
                    f.write(f'DEPLOYMENT_ADMIN_PASSWORD="{password}"\n')
                
                self.stdout.write(self.style.SUCCESS(f'Admin credentials saved to .env file'))
            except Exception as env_error:
                self.stdout.write(self.style.WARNING(f'Failed to save credentials to .env file: {str(env_error)}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating deployment admin: {str(e)}'))
            # Even if we have an error, we should try to ensure there's at least one superuser
            if not User.objects.filter(is_superuser=True).exists():
                try:
                    # Fall back to creating a basic superuser
                    User.objects.create_superuser(
                        username='emergency_admin',
                        email='emergency@smorasfotball.no',
                        password='emergencyadmin123'
                    )
                    self.stdout.write(self.style.SUCCESS('Created emergency superuser: emergency_admin'))
                except Exception as emergency_error:
                    self.stdout.write(self.style.ERROR(f'Failed to create emergency admin: {str(emergency_error)}'))