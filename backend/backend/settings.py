
import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)


def env_list(name, default=None, merge_default=False):
    value = os.environ.get(name)
    default_list = default or []
    if value is None:
        return default_list

    env_values = [item.strip() for item in value.split(",") if item.strip()]
    if not merge_default:
        return env_values

    # Keep defaults and append env values without duplicates.
    merged = list(default_list)
    for item in env_values:
        if item not in merged:
            merged.append(item)
    return merged


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

DEBUG = env_bool("DJANGO_DEBUG", False)

# No default in production: a missing key must fail loudly, not fall back to a public one.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or (
    "dev-only-insecure-key" if DEBUG else None
)
if not SECRET_KEY:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY in backend/.env")


ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", [
    "137.184.149.59",
    "localhost",
    "127.0.0.1",
    "milliapi.getotech.co.ke",
    "54.164.100.151",
    "millibackend.amilliontechies.com",
], merge_default=True)

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
    'cohorts',
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
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'api.authentication.OptionalJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    # Number of reverse proxies in front of Django (nginx = 1), so throttling uses the address nginx
    # appended instead of a client-supplied X-Forwarded-For.
    'NUM_PROXIES': env_int('NUM_PROXIES', 1),
    'DEFAULT_THROTTLE_RATES': {
        'email': '20/hour',  # endpoints that send email
        'signin_verify': '60/hour',  # redeeming sign-in links
    },
}



from datetime import timedelta

# Short-lived access token; the frontend swaps it using the refresh token.
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

JAZZMIN_SETTINGS = {
    "site_title": "Backend Admin",
    "site_header": "Backend Dashboard",
    "welcome_sign": "Welcome to the Admin Panel",
    "show_sidebar": True,
    "navigation_expanded": True,
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5000",
    "https://amilliontechies.com",
    "http://137.184.149.59",
    "https://millibackend.amilliontechies.com",
    "http://54.164.100.151",
], merge_default=True)

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://localhost(:\d+)?$",
    r"^https?://127\.0\.0\.1(:\d+)?$",
]

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://millibackend.amilliontechies.com",
    "http://137.184.149.59",
    "http://54.164.100.151",
])

AUTHENTICATION_BACKENDS = (
    'api.backends.EmailBackend', 
    'django.contrib.auth.backends.ModelBackend',
    # 'django.contrib.auth.backends.ModelBackend',
    # 'allauth.account.auth_backends.AuthenticationBackend',
)

AUTH_USER_MODEL = 'api.User' 


DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'info@amilliontechies.com')

# Email settings (development)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.zoho.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 10  # seconds; a hung SMTP server must not hang the request
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'info@amilliontechies.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

SITE_DOMAIN = "https://millibackend.amilliontechies.com"
# SITE_DOMAIN = "http://127.0.0.1:5000"


BACKEND_URL = 'https://millibackend.amilliontechies.com'
# BACKEND_URL = 'http:127.0.0.1:5000' 
FRONTEND_URL = 'https://amilliontechies.com'
# FRONTEND_URL = 'http:127.0.0.1:5173'

