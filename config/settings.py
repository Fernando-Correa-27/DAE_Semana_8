"""Settings for the headless API lab. Development only: never deploy this as is."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# No credentials in code: the key comes from the environment. The fallback is a
# throwaway value that only makes sense on a classroom machine.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-not-a-secret")
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

INSTALLED_APPS = [
    "django.contrib.auth",
    # Web interface (ADR-0001): session cookie for the browser, flash messages
    # after the POST/redirect pattern and static files served from the app.
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "django.contrib.staticfiles",
    "quiz",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# The browser talks to the UI with a session cookie; the API keeps its own token
# authentication (rest_framework below). The two are never mixed.
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "static/"  # without it, the test server (LiveServerTestCase) answers 500 to every request

# One page size for every listing of the project: the API (below) and the web
# interface use this same number, so «Anterior/Siguiente» means the same thing in
# both presentations (R-UI-03). Change it here and both move together.
PAGE_SIZE = 5

REST_FRAMEWORK = {
    # Identity comes from a token in the Authorization header: no cookies, no sessions.
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    # Two layers: you must be somebody (IsAuthenticated) and the role decides what you may do.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "quiz.permissions.AgentPermission",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": PAGE_SIZE,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API de cuestionarios",
    "DESCRIPTION": "El contrato de la API del laboratorio: lo que usan el cliente de consola y el agente.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# The UI lives at the root of the site and names its routes "quiz_ui:...".
# Without these three, LoginRequiredMixin would send the user to a URL that
# does not exist in this project.
LOGIN_URL = "quiz_ui:login"
LOGIN_REDIRECT_URL = "quiz_ui:dashboard"
LOGOUT_REDIRECT_URL = "quiz_ui:login"
