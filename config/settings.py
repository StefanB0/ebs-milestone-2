"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 5.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
import environ

from pathlib import Path
from typing import List, Tuple
from datetime import timedelta

# Django-environ
# Required services to run application: postgres, mailhog
env = environ.Env(
    ELASTICSEARCH_ACTIVE=(bool, True),
    CELERY_ALWAYS_EAGER=(bool, False),
    OAUTH_CLIENT_ID_GITHUB=(str, ""),
    OAUTH_CLIENT_SECRET_GITHUB=(str, ""),
    DATABASE_URL=(str, "postgresql://postgres:postgres@localhost:5432/postgres"),
    CACHE_URL=(str, "redis://localhost:6379/1"),  # redis: redis://localhost:6379/1 | local: "locmemcache:"
    MESSAGE_BROKER_URL=(str, "pyamqp://admin:admin@localhost"),
    EMAIL_HOST=(str, "localhost"),
    S3_HOST=(str, "localhost"),
    S3_BACKEND=(str, "minio"),  # options: none, minio
    S3_EXTERNAL_HOST=(str, "localhost"),
    ELASTICSEARCH_HOST=(str, "localhost"),
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-cug=50j#8tv^tw!dvg@e!0snq^p+#ikhwv$6q6zslmt@pp$x0f"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost"])

# Application definition

INSTALLED_APPS = [
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
    "django_celery_results",
    "django_celery_beat",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "apps.common",
    "apps.users",
    "apps.tasks",
]

if env("S3_BACKEND") == "minio":
    INSTALLED_APPS.append("django_minio_backend")

if env("ELASTICSEARCH_ACTIVE"):
    INSTALLED_APPS.append("django_elasticsearch_dsl")


MIDDLEWARE = [
    # Default Django middleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # Third party middleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Third Party
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates/"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

CORS_ORIGIN_ALLOW_ALL = env.bool("CORS_ORIGIN_ALLOW_ALL", default=False)

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

CORS_ALLOWED_ORIGIN_REGEXES = [r".*://localhost:.*", r".*://127.0.0.1:.*"]

CORS_ALLOWED_ORIGIN_REGEXES += list(map(lambda host: f".*://{host}:.*", ALLOWED_HOSTS))

CORS_ALLOW_HEADERS = (
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "token",
    "cache-control",
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# Parse database connection url strings like psql://user:pass@127.0.0.1:8458/db

DATABASES = {
    "default": env.db(),
}

# Cache

CACHES = {
    "default": env.cache(),
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if env("S3_BACKEND") == "minio":
    STATICFILES_STORAGE = "django_minio_backend.models.MinioBackendStatic"
    DEFAULT_FILE_STORAGE = "django_minio_backend.models.MinioBackend"

    MINIO_ACCESS_KEY = "admin"
    MINIO_SECRET_KEY = "admin-admin"
    MINIO_CONSISTENCY_CHECK_ON_START = False
    MINIO_BUCKET_CHECK_ON_SAVE = True  # Default: True // Creates bucket if missing, then save
    MINIO_URL_EXPIRY_HOURS = timedelta(days=1)  # Default is 7 days (longest) if not defined
    MINIO_POLICY_HOOKS: List[Tuple[str, dict]] = []

    MINIO_MEDIA_FILES_BUCKET = "django-media-files-bucket"  # replacement for MEDIA_ROOT
    MINIO_STATIC_FILES_BUCKET = "django-static-files-bucket"  # replacement for STATIC_ROOT

    MINIO_PRIVATE_BUCKETS = []
    MINIO_PUBLIC_BUCKETS = [MINIO_MEDIA_FILES_BUCKET, MINIO_STATIC_FILES_BUCKET]

    MINIO_ENDPOINT = f"{env("S3_HOST")}:9000"
    MINIO_USE_HTTPS = False
    MINIO_EXTERNAL_ENDPOINT = f"{env("S3_EXTERNAL_HOST")}:9000"  # Default is same as MINIO_ENDPOINT
    MINIO_EXTERNAL_ENDPOINT_USE_HTTPS = False  # Default is same as MINIO_USE_HTTPS

    STATIC_URL = f"http://{MINIO_EXTERNAL_ENDPOINT}/{MINIO_STATIC_FILES_BUCKET}/"

    STORAGES = {
        "staticfiles": {
            "BACKEND": "django_minio_backend.models.MinioBackendStatic",
        },
        "default": {
            "BACKEND": "django_minio_backend.models.MinioBackend",
        },
    }
else:
    STATIC_URL = "static/"
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SPECTACULAR_SETTINGS = {
    "TITLE": "EBS Internship Test",
    "DESCRIPTION": "EBS Internship Test API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": True,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser", "rest_framework.permissions.IsAuthenticated"],
}

# Email settings

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")

EMAIL_PORT = 1025
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""

DEFAULT_FROM_EMAIL = "example@mail.com"

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

# Celery settings

CELERY_ALWAYS_EAGER = env("CELERY_ALWAYS_EAGER")

CELERY_BROKER_URL = env("MESSAGE_BROKER_URL")
CELERY_CACHE_BACKEND = "default"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_BACKEND = "django-db"

CELERY_TASK_SERIALIZER = "json"

# Elastic search

ELASTICSEARCH_ACTIVE = env("ELASTICSEARCH_ACTIVE")

ELASTICSEARCH_DSL = {
    "default": {
        "hosts": f"http://{env("ELASTICSEARCH_HOST")}:9200",
    }
}

# AllAuth

SITE_ID = 1
ACCOUNT_LOGOUT_ON_GET = True
LOGIN_REDIRECT_URL = "/users/profile/"
LOGOUT_REDIRECT_URL = "/users/profile/"

SOCIALACCOUNT_PROVIDERS = {
    "github": {
        "VERIFIED_EMAIL": True,
        "APPS": [
            {
                "client_id": env("OAUTH_CLIENT_ID_GITHUB"),
                "secret": env("OAUTH_CLIENT_SECRET_GITHUB"),
                "key": "",
            },
        ],
        "SCOPE": ["user"],
    }
}
