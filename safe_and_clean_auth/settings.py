import os
import environ
from datetime import timedelta
from celery.schedules import crontab

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')


# Application definition

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

PROJECT_APPS = [
    'apps.core',
    'apps.accounts',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'channels',
    'channels_redis',
    'djoser',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_celery_results',
    'django_celery_beat',
]

INSTALLED_APPS = DJANGO_APPS + PROJECT_APPS + THIRD_PARTY_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'safe_and_clean_auth.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'safe_and_clean_auth.wsgi.application'
ASGI_APPLICATION = 'safe_and_clean_auth.asgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DATABASE_NAME'),
        'USER': env('DATABASE_USER'),
        'PASSWORD': env('DATABASE_PASSWORD'),
        'HOST': env('DATABASE_HOST'),
        'PORT': env('DATABASE_PORT'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]


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

AUTH_USER_MODEL = 'accounts.CustomUser'

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Mexico_City'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_LOCATION = 'static'
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, STATIC_LOCATION)

MEDIA_LOCATION = 'media'
MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, MEDIA_LOCATION)

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email — Resend
EMAIL_BACKEND = 'apps.core.email_backend.ResendEmailBackend'
RESEND_API_KEY = env('RESEND_API_KEY')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Twilio
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN')
TWILIO_VERIFY_SERVICE_SID = env('TWILIO_VERIFY_SERVICE_SID')
TWILIO_FROM_NUMBER = env('TWILIO_FROM_NUMBER')

# Rate limiting (Redis-backed counters)
# Employees use SMS; admins and clients use email.
SMS_RATE_LIMITS = {
    'per_user': {'1h': 3,   '6h': 6,   '1d': 10},
    'global':   {'1h': 50,  '6h': 150, '1d': 500},
}
EMAIL_RATE_LIMITS = {
    'per_user': {'1h': 5,   '6h': 10,  '1d': 20},
    'global':   {'1h': 100, '6h': 300, '1d': 1000},
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('JWT',),
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=2),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'SIGNING_KEY': env('SECRET_KEY'),   
    'TOKEN_OBTAIN_SERIALIZER': 'apps.accounts.serializers.CustomTokenObtainPairSerializer',
    'UPDATE_LAST_LOGIN': True,
}

DOMAIN = env('FRONTEND_DOMAIN', default='localhost:3000') 
SITE_NAME = 'Safe & Clean Querétaro'

DJOSER = {
    'LOGIN_FIELD': 'email',
    'USER_CREATE_PASSWORD_RETYPE': True,
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': True,
    'SEND_CONFIRMATION_EMAIL': True,
    'SEND_ACTIVATION_EMAIL': True,
    'SET_PASSWORD_RETYPE': True,

    'PASSWORD_RESET_CONFIRM_URL': 'email/password_reset_confirm/{uid}/{token}',
    'ACTIVATION_URL': 'email/activate/{uid}/{token}',

    'EMAIL': {
        'activation': 'apps.accounts.emails.ActivationEmail',
        'confirmation': 'apps.accounts.emails.ConfirmationEmail',
        'password_reset': 'apps.accounts.emails.PasswordResetEmail',
        'password_changed_confirmation': 'apps.accounts.emails.PasswordChangedConfirmationEmail',
    },

    'SERIALIZERS': {
        'user_create': 'apps.accounts.serializers.UserCreateSerializer',
        'user_create_password_retype': 'apps.accounts.serializers.UserCreateSerializer',
        'user': 'apps.accounts.serializers.UserSerializer',
        'current_user': 'apps.accounts.serializers.UserSerializer',
        'user_delete': 'djoser.serializers.UserDeleteSerializer',
        'password_reset': 'apps.accounts.serializers.CustomPasswordResetSerializer',
    },

    'TEMPLATES': {
        'activation': 'email/auth/activation.html',
        'confirmation': 'email/auth/confirmation.html',
        'password_reset': 'email/auth/password_reset.html',
        'password_reset_confirm': 'email/auth/password_reset_confirm.html',
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [env('REDIS_URL')],
        },
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
}

CHANNELS_ALLOWED_ORIGINS = [
    "http://localhost:3000"
]

# Celery
CELERY_BROKER_URL = env('REDIS_URL')
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,
}
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'default'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'

CELERY_BEAT_SCHEDULE = {
    'notify-contracts-expiring-soon': {
        'task': 'apps.accounts.tasks.notify_contracts_expiring_soon',
        'schedule': crontab(hour=9, minute=0),
    },
    'notify-contracts-expired': {
        'task': 'apps.accounts.tasks.notify_contracts_expired',
        'schedule': crontab(hour=9, minute=5),
    },
}
