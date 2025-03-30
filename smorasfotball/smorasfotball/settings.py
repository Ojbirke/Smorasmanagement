"""
Django settings for smorasfotball project.
Generated by 'django-admin startproject' using Django 4.2.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SESSION_SECRET', 'django-insecure-default-key-for-development')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True  # Setting to True for development
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rosetta',  # For translation management in admin
    'teammanager',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Add locale middleware for language selection
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'smorasfotball.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'smorasfotball.wsgi.application'

# Database
import os
import dj_database_url

# ALWAYS use PostgreSQL in production
# Check for DATABASE_URL environment variable
if os.environ.get('DATABASE_URL'):
    print("PostgreSQL detected via DATABASE_URL")
    
    # PostgreSQL configuration with enhanced settings for deployment reliability
    database_config = dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
    
    # Add special options to enhance PostgreSQL connection reliability
    database_config['OPTIONS'] = {
        'sslmode': 'require',
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
    }
    
    # Log the database engine type (without sensitive info)
    print(f"Database engine: {database_config.get('ENGINE', 'unknown')}")
    
    DATABASES = {
        'default': database_config
    }
    
    # Retry connection on failures (helps with Replit deployments)
    DATABASES['default']['CONN_MAX_AGE'] = 0  # Reconnect for each request
    DATABASES['default']['ATOMIC_REQUESTS'] = True  # Wrap requests in transactions
else:
    # If DATABASE_URL is not set, this is a critical error in production
    # We'll still define a fallback SQLite database for testing purposes only
    print("WARNING: No DATABASE_URL found! The application should always use PostgreSQL in production.")
    print("This fallback should only be used for testing environments.")
    
    # Check for production environment marker
    is_production = os.path.exists(os.path.join(os.path.dirname(BASE_DIR), 'deployment', 'IS_PRODUCTION_ENVIRONMENT'))
    if is_production:
        print("ERROR: This appears to be a production environment, but DATABASE_URL is not set!")
        print("This is a critical configuration error that must be fixed.")
        
        # Since this is a production environment, automatically try to create a PostgreSQL database
        try:
            import subprocess
            print("Attempting to create PostgreSQL database and fix configuration...")
            
            # First, try to run our automatic PostgreSQL creation script
            script_path = os.path.join(os.path.dirname(BASE_DIR), 'create_postgres_db.py')
            if os.path.exists(script_path):
                result = subprocess.run(['python', script_path], capture_output=True, text=True)
                print(result.stdout)
                
                # If that worked, DATABASE_URL should be set in environment
                if os.environ.get('DATABASE_URL'):
                    print("Successfully created PostgreSQL database!")
                    
                    # Construct database config from the updated environment variable
                    import dj_database_url
                    database_config = dj_database_url.config(
                        default=os.environ.get('DATABASE_URL'),
                        conn_max_age=600,
                        conn_health_checks=True,
                    )
                    
                    # Add special options to enhance PostgreSQL connection reliability
                    database_config['OPTIONS'] = {
                        'sslmode': 'require',
                        'connect_timeout': 10,
                        'keepalives': 1,
                        'keepalives_idle': 30,
                        'keepalives_interval': 10,
                        'keepalives_count': 5,
                    }
                    
                    print(f"Using dynamically created PostgreSQL database.")
                    DATABASES = {
                        'default': database_config
                    }
                    
                    # Continue with normal initialization - don't use SQLite
                    # This will skip the SQLite configuration below
                    
                    # Also save this URL for future use
                    try:
                        # Save credentials to deployment directory
                        deployment_dir = os.path.join(os.path.dirname(BASE_DIR), 'deployment')
                        os.makedirs(deployment_dir, exist_ok=True)
                        
                        creds_file = os.path.join(deployment_dir, 'postgres_credentials.json')
                        
                        # Save only the DATABASE_URL to avoid saving other sensitive credentials
                        import json
                        with open(creds_file, 'w') as f:
                            json.dump({'DATABASE_URL': os.environ.get('DATABASE_URL')}, f)
                        
                        print(f"PostgreSQL credentials saved for future use")
                    except Exception as e:
                        print(f"Warning: Could not save PostgreSQL credentials: {e}")
                    
                    # Skip the SQLite configuration
                    print("Automatically switched to PostgreSQL - no need for SQLite fallback")
                    
                    # We need to use this to tell the rest of the function to skip SQLite config
                    _USING_POSTGRES_DYNAMIC = True
        except Exception as e:
            print(f"Error attempting to set up PostgreSQL: {e}")
            _USING_POSTGRES_DYNAMIC = False
    
    # Only use SQLite if we didn't dynamically set up PostgreSQL above
    if not locals().get('_USING_POSTGRES_DYNAMIC', False):
        # Fallback to SQLite (for development or testing only)
        DB_DIR = os.environ.get('DATABASE_DIR', os.path.join(os.path.dirname(BASE_DIR), 'deployment'))
        os.makedirs(DB_DIR, exist_ok=True)
        
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(DB_DIR, 'db.sqlite3'),
            }
        }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
from django.utils.translation import gettext_lazy as _
LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Available languages
LANGUAGES = [
    ('en', _('English')),
    ('no', _('Norwegian')),
]

# Path to the translation files
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'teammanager/static'),
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login redirect
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# CSRF settings - allow Replit domains
CSRF_TRUSTED_ORIGINS = [
    'https://*.repl.co',
    'https://*.replit.app',
    'https://*.repl.dev',
]