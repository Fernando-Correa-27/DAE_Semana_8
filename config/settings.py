"""Settings for the headless API lab. Development only: never deploy this as is."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# Local file that keeps the classroom key between restarts. It is a secret, so it
# is ignored by git and never printed.
SECRET_KEY_FILE = BASE_DIR / ".secret_key"

# Development is the default so the lab keeps working with no environment at all.
# Turn it off with DJANGO_DEBUG=0 (and then the two variables below are mandatory).
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"


def _secret_key_from_file(path):
    """The stored key, generating and saving one the first time.

    Returns an empty string when the file cannot be read or written, and the
    caller decides what to do about it.
    """
    try:
        stored = path.read_text(encoding="utf-8").strip()
    except OSError:
        stored = ""
    if stored:
        return stored
    generated = get_random_secret_key()
    try:
        path.write_text(generated, encoding="utf-8")
        os.chmod(path, 0o600)  # owner only, on the systems that have such permissions
    except OSError:
        return ""
    return generated


def _secret_key():
    """No credential in the code, ever.

    Resolution order (SUI-01): the environment first, then a random key persisted
    in ``.secret_key`` so the sessions of the lab survive a restart. With DEBUG off
    only the environment counts: a key written on disk is not a key of production.
    """
    from_environment = os.environ.get("DJANGO_SECRET_KEY", "").strip()
    if from_environment:
        return from_environment
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set in the environment when DJANGO_DEBUG is off "
            "(a key stored in .secret_key is only good for a classroom machine)."
        )
    stored = _secret_key_from_file(SECRET_KEY_FILE)
    # A read-only checkout still runs: the key is then valid until the process ends.
    return stored or get_random_secret_key()


def _allowed_hosts():
    """Loopback by default while developing, the environment everywhere else (SUI-02)."""
    from_environment = [
        host.strip()
        for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    ]
    if from_environment:
        return from_environment
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS must list, comma separated, the hosts allowed to serve "
            "this site when DJANGO_DEBUG is off."
        )
    return ["localhost", "127.0.0.1", "testserver"]


SECRET_KEY = _secret_key()
ALLOWED_HOSTS = _allowed_hosts()

# The interface is never meant to be embedded in another site (SUI-05). The CSP
# below is the modern half of the same control.
X_FRAME_OPTIONS = "DENY"
CONTENT_SECURITY_POLICY = "default-src 'self'; frame-ancestors 'none'"

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
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.ContentSecurityPolicyMiddleware",
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
