"""Production settings."""

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE

DEBUG = False

# WhiteNoise serves Django admin/DRF static assets from the same Gunicorn
# process; Caddy only terminates TLS and proxies requests.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
WHITENOISE_MAX_AGE = 31536000

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
REFRESH_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# В production обязательно задайте DJANGO_SECRET_KEY, DATABASE_URL,
# DISCORD_CLIENT_ID/SECRET, STRIPE_* и EMAIL_* через переменные окружения.
