"""Development settings."""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# The development server starts a new thread for each request. Close that
# thread's database connection at the end of the request.
DATABASES["default"]["CONN_MAX_AGE"] = 0

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# В разработке refresh-cookie можно не помечать Secure, чтобы работать по http.
REFRESH_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
