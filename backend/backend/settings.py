
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-yj&iq=svp^7kl9=e%!$)29^r&)6o9az8v8(c9-id%b)fmw672a'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    "137.184.149.59",
    "localhost",
    "127.0.0.1",
    "milliapi.getotech.co.ke",
    "54.164.100.151",
    "millibackend.amilliontechies.com",
]


# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Manually added packages files
    'rest_framework',
    'drf_yasg',
    'corsheaders',
    'allauth',
    # Custom Project apps
    'api',
    'joinus',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}



JAZZMIN_SETTINGS = {
    "site_title": "Backend Admin",
    "site_header": "Backend Dashboard",
    "welcome_sign": "Welcome to the Admin Panel",
    "show_sidebar": True,
    "navigation_expanded": True,
}

CORS_ALLOW_ALL_ORIGINS = True  # Allows all domains to access your API

# OR for specific domains (recommended for production)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000", 
    "http://127.0.0.1:5000", 
    "https://amilliontechies.com", 
    "http://137.184.149.59",
    "https://millibackend.amilliontechies.com",
    "http://54.164.100.151"
]

CSRF_TRUSTED_ORIGINS = [
    "https://millibackend.amilliontechies.com",
    "http://137.184.149.59",
    "http://54.164.100.151",
]

AUTHENTICATION_BACKENDS = (
    'api.backends.EmailBackend', 
    'django.contrib.auth.backends.ModelBackend',
    # 'django.contrib.auth.backends.ModelBackend',
    # 'allauth.account.auth_backends.AuthenticationBackend',
)

AUTH_USER_MODEL = 'api.User' 


DEFAULT_FROM_EMAIL = 'info@getotech.co.ke'

# Email settings (development)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.zoho.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'info@getotech.co.ke'
EMAIL_HOST_PASSWORD = 'vxzYiUKaYkqZ'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIAFILES_DIRS = [MEDIA_ROOT]

SITE_DOMAIN = "https://millibackend.amilliontechies.com"
# SITE_DOMAIN = "http://127.0.0.1:5000"


BACKEND_URL = 'https://millibackend.amilliontechies.com'
# BACKEND_URL = 'http:127.0.0.1:5000' 
FRONTEND_URL = 'https://amilliontechies.com'
# FRONTEND_URL = 'http:127.0.0.1:5173'
