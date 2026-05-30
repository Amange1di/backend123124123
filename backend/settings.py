"""
Django settings for backend project.
"""

import os
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-change-me-in-production-for-backend1231241231"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False") == "True"

# Разрешённые хосты - для Render разрешаем все
ALLOWED_HOSTS = ["*"]


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "accounts",
    "courses",
    "assignments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "backend.wsgi.application"


# Database - PostgreSQL for Render, SQLite for local
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# PostgreSQL для production (Render)
# Проверяем и DATABASE_URL, и RENDER_POSTGRES (который может быть установлен автоматически)
DATABASE_URL = os.environ.get("DATABASE_URL")
RENDER_POSTGRES = os.environ.get("RENDER_POSTGRES")

if DATABASE_URL:
    try:
        import dj_database_url
        # Пытаемся распарсить URL вручную, если parse не работает
        try:
            DATABASES['default'] = dj_database_url.parse(
                DATABASE_URL,
                conn_max_age=600,
                conn_health_checks=True,
            )
            print(f"DEBUG: PostgreSQL configured from DATABASE_URL")
            print(f"DEBUG: DATABASE engine: {DATABASES['default']['ENGINE']}")
            print(f"DEBUG: DATABASE NAME: {DATABASES['default'].get('NAME', 'N/A')}")
            print(f"DEBUG: DATABASE HOST: {DATABASES['default'].get('HOST', 'N/A')}")
        except Exception as parse_error:
            print(f"DEBUG: dj_database_url.parse() failed: {parse_error}")
            # Ручной парсинг DATABASE_URL
            from urllib.parse import urlparse
            parsed = urlparse(DATABASE_URL)
            DATABASES['default'] = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': parsed.path.lstrip('/'),
                'USER': parsed.username,
                'PASSWORD': parsed.password,
                'HOST': parsed.hostname,
                'PORT': parsed.port or 5432,
                'CONN_MAX_AGE': 600,
            }
            print(f"DEBUG: Manual parse - NAME: {DATABASES['default']['NAME']}")
    except ImportError:
        print("ERROR: dj_database_url not installed. Run: pip install dj-database-url")
    except Exception as e:
        print(f"ERROR: Failed to configure PostgreSQL: {e}")
elif RENDER_POSTGRES:
    # Render автоматически устанавливает RENDER_POSTGRES, но нужны дополнительные переменные
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("RENDER_POSTGRES_DB", "lms_db"),
        "USER": os.environ.get("RENDER_POSTGRES_USER", "lms_user"),
        "PASSWORD": os.environ.get("RENDER_POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("RENDER_POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("RENDER_POSTGRES_PORT", "5432"),
    }
    print(f"DEBUG: PostgreSQL configured from RENDER_POSTGRES")
else:
    print(f"DEBUG: Using SQLite database")


# Password validation
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


# Internationalization
LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Asia/Almaty"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# STATICFILES_DIRS только если папка существует (для локальной разработки)
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    STATICFILES_DIRS = [STATIC_DIR]
else:
    STATICFILES_DIRS = []

# WhiteNoise for static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Custom User Model
AUTH_USER_MODEL = "accounts.User"


# REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# CORS Settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# CSRF Settings - разрешаем все источники для упрощения
CSRF_TRUSTED_ORIGINS = [
    "https://backend1231241231.onrender.com",
    "https://frontend123123123.vercel.app",
    "http://localhost:3000",
    "http://localhost:8000",
]

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"


# DRF Spectacular (Swagger/OpenAPI) settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Backend API",
    "DESCRIPTION": "API для системы управления курсами и заданиями",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
}
