from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "[::1]"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DATA_RETENTION_DAYS=(int, 365),
    DEFAULT_AUTH_MINUTES=(int, 1440),
    GOOGLE_SHEETS_ENABLED=(bool, False),
    GOOGLE_SHEETS_TIMEOUT_SECONDS=(int, 5),
    GOOGLE_SHEETS_WEBHOOK_SECRET=(str, ""),
    GOOGLE_SHEETS_WEBHOOK_URL=(str, ""),
    OMADA_CONTROLLER_ID=(str, ""),
    OMADA_CONTROLLER_URL=(str, ""),
    OMADA_DEFAULT_SITE=(str, ""),
    OMADA_ENABLED=(bool, False),
    OMADA_OPERATOR_PASSWORD=(str, ""),
    OMADA_OPERATOR_USERNAME=(str, ""),
    OMADA_TIMEOUT_SECONDS=(int, 5),
    OMADA_VERIFY_SSL=(bool, True),
    PORTAL_ALLOWED_REDIRECT_HOSTS=(list, []),
    PORTAL_RATE_LIMIT_ATTEMPTS=(int, 20),
    PORTAL_RATE_LIMIT_ENABLED=(bool, True),
    PORTAL_RATE_LIMIT_WINDOW_SECONDS=(int, 60),
    SECURE_SSL_REDIRECT=(bool, False),
    SUCCESS_REDIRECT_URL=(str, ""),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-local-dev-only-change-before-deploy",
)
DEBUG = env.bool("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

DATA_RETENTION_DAYS = env.int("DATA_RETENTION_DAYS")
PORTAL_ALLOWED_REDIRECT_HOSTS = env.list("PORTAL_ALLOWED_REDIRECT_HOSTS")
PORTAL_RATE_LIMIT_ATTEMPTS = env.int("PORTAL_RATE_LIMIT_ATTEMPTS")
PORTAL_RATE_LIMIT_ENABLED = env.bool("PORTAL_RATE_LIMIT_ENABLED")
PORTAL_RATE_LIMIT_WINDOW_SECONDS = env.int("PORTAL_RATE_LIMIT_WINDOW_SECONDS")
DEFAULT_AUTH_MINUTES = env.int("DEFAULT_AUTH_MINUTES")
SUCCESS_REDIRECT_URL = env("SUCCESS_REDIRECT_URL")
GOOGLE_SHEETS_ENABLED = env.bool("GOOGLE_SHEETS_ENABLED")
GOOGLE_SHEETS_WEBHOOK_URL = env("GOOGLE_SHEETS_WEBHOOK_URL")
GOOGLE_SHEETS_WEBHOOK_SECRET = env("GOOGLE_SHEETS_WEBHOOK_SECRET")
GOOGLE_SHEETS_TIMEOUT_SECONDS = env.int("GOOGLE_SHEETS_TIMEOUT_SECONDS")
OMADA_ENABLED = env.bool("OMADA_ENABLED")
OMADA_CONTROLLER_URL = env("OMADA_CONTROLLER_URL")
OMADA_CONTROLLER_ID = env("OMADA_CONTROLLER_ID")
OMADA_OPERATOR_USERNAME = env("OMADA_OPERATOR_USERNAME")
OMADA_OPERATOR_PASSWORD = env("OMADA_OPERATOR_PASSWORD")
OMADA_VERIFY_SSL = env.bool("OMADA_VERIFY_SSL")
OMADA_DEFAULT_SITE = env("OMADA_DEFAULT_SITE")
OMADA_TIMEOUT_SECONDS = env.int("OMADA_TIMEOUT_SECONDS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wifi_portal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "portal.context_processors.portal_branding",
            ],
        },
    },
]

WSGI_APPLICATION = "wifi_portal.wsgi.application"

database_url = env("DATABASE_URL", default="")
if database_url:
    USING_SQLITE_FALLBACK = False
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    USING_SQLITE_FALLBACK = True
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
if DEBUG or USING_SQLITE_FALLBACK:
    staticfiles_backend = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    staticfiles_backend = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": staticfiles_backend,
    },
}
WHITENOISE_MANIFEST_STRICT = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
