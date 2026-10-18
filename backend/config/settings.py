"""
Django settings for AI Describer Medical project.
"""
import os
import secrets
from pathlib import Path

from django.core.management.utils import get_random_secret_key

# Load environment variables from .env file
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file
load_dotenv(BASE_DIR / '.env')

# SECRET_KEY management: auto-generate and persist
SECRET_KEY_FILE = BASE_DIR / '.secret_key'

if SECRET_KEY_FILE.exists():
    with open(SECRET_KEY_FILE, 'r') as f:
        SECRET_KEY = f.read().strip()
else:
    SECRET_KEY = get_random_secret_key()
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(SECRET_KEY)
    os.chmod(SECRET_KEY_FILE, 0o600)  # Read/write for owner only

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# ALLOWED_HOSTS configuration
# Automatically adds localhost and 127.0.0.1 for healthchecks
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()]
if 'localhost' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('localhost')
if '127.0.0.1' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('127.0.0.1')

# Application definition
INSTALLED_APPS = [
    'daphne',  # ASGI server for Django Channels (must be first)
    # 'django.contrib.admin',  # Not using Django Admin
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Third-party apps
    'channels',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    
    # Local apps
    'backend.core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'backend.core.middleware.SetupRedirectMiddleware',  # Custom middleware for setup redirect
]

ROOT_URLCONF = 'backend.config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'backend' / 'templates'],
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

WSGI_APPLICATION = 'backend.config.wsgi.application'
ASGI_APPLICATION = 'backend.config.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'aimedical_db'),
        'USER': os.getenv('POSTGRES_USER', 'aimedical'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Redis for Django Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('REDIS_HOST', 'redis'), int(os.getenv('REDIS_PORT', '6379')))],
        },
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'backend' / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django Sites Framework (required by allauth)
SITE_ID = 1

# django-allauth settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_AUTHENTICATION_METHOD = 'username'
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_SESSION_REMEMBER = True

# Disable user self-registration and password reset
ACCOUNT_ADAPTER = 'backend.core.adapters.NoSignupAccountAdapter'
ACCOUNT_FORMS = {
    'signup': 'allauth.account.forms.SignupForm',  # Will be blocked by adapter
}

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = int(os.getenv('SESSION_TIMEOUT_HOURS', '3')) * 3600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF settings
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False  # Must be False to allow JavaScript access for AJAX requests
CSRF_COOKIE_SAMESITE = 'Lax'

# Security settings (production)
# Note: TLS termination and HSTS headers are handled by reverse proxy (Nginx)
# Django listens on HTTP, but recognizes HTTPS from X-Forwarded-Proto header
if not DEBUG:
    # Trust X-Forwarded-Proto header from reverse proxy
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# AmiVoice API settings
AMIVOICE_API_URL = os.getenv('AMIVOICE_API_URL', 'wss://acp-api.amivoice.com/v1/nolog/')
AMIVOICE_API_KEY = os.getenv('AMIVOICE_API_KEY', '')
AMIVOICE_GRAMMAR = os.getenv('AMIVOICE_GRAMMAR', '-a-medical')

# LLM settings
LLM_MODEL = os.getenv('LLM_MODEL', 'bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0')
LITELLM_API_BASE = os.getenv('LITELLM_API_BASE', '')
# Upper bound on prompt length accepted over the LLM WebSocket (limits cost abuse)
LLM_MAX_PROMPT_CHARS = int(os.getenv('LLM_MAX_PROMPT_CHARS', '20000'))

# AWS settings (for Bedrock)
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')

# Security - HMAC secret for user ID hashing in logging
HMAC_SECRET = os.getenv('HMAC_SECRET', '')
if not HMAC_SECRET and not DEBUG:
    raise ValueError('HMAC_SECRET must be set in production')

# Password generation settings
PASSWORD_GEN_LENGTH = int(os.getenv('PASSWORD_GEN_LENGTH', '12'))
PASSWORD_GEN_CHARS = os.getenv(
    'PASSWORD_GEN_CHARS',
    'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
)

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'backend': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
