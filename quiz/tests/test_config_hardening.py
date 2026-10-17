"""Endurecimiento de la configuración: clave secreta, DEBUG y cabeceras.

Estas pruebas fijan en el código lo que hasta ahora solo estaba comprobado a mano
en ``docs/seguridad-interfaz.md`` (SUI-01, SUI-02 y SUI-05). Lo que ocurre al
arrancar se comprueba en un proceso aparte, porque lo que falla es la carga de
los settings.
"""
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from . import helpers

BOOTSTRAP = "import django; django.setup(); print('settings loaded')"
BASE_DIR = Path(settings.BASE_DIR)


def boot(**environment):
    """Load the settings in a fresh interpreter and return the completed process."""
    env = {k: v for k, v in os.environ.items() if k not in {
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
    }}
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    env.update(environment)
    return subprocess.run(
        [sys.executable, "-c", BOOTSTRAP],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


class SecretKeyTests(SimpleTestCase):
    """SUI-01: no credential of this project may live in the repository."""

    def test_secret_key_is_not_the_published_fallback(self):
        self.assertNotEqual(settings.SECRET_KEY, "dev-only-not-a-secret")

    def test_secret_key_is_a_real_random_key(self):
        self.assertGreaterEqual(len(settings.SECRET_KEY), 32)

    def test_secret_key_file_is_not_tracked_by_git(self):
        ignored = (BASE_DIR / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".secret_key", [line.strip() for line in ignored])


class StartupGuardTests(SimpleTestCase):
    """SUI-02: with DEBUG off the startup must fail closed, not guess."""

    def test_debug_off_without_secret_key_is_refused(self):
        process = boot(DJANGO_DEBUG="0")
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("ImproperlyConfigured", process.stderr)
        self.assertIn("DJANGO_SECRET_KEY", process.stderr)

    def test_debug_off_without_allowed_hosts_is_refused(self):
        process = boot(
            DJANGO_DEBUG="0",
            DJANGO_SECRET_KEY="from-the-environment-only-for-this-test",
            DJANGO_ALLOWED_HOSTS="",
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("ImproperlyConfigured", process.stderr)
        self.assertIn("DJANGO_ALLOWED_HOSTS", process.stderr)

    def test_debug_off_with_both_variables_starts(self):
        process = boot(
            DJANGO_DEBUG="0",
            DJANGO_SECRET_KEY="from-the-environment-only-for-this-test",
            DJANGO_ALLOWED_HOSTS="quiz.example",
        )
        self.assertEqual(process.returncode, 0, msg=process.stderr)
        self.assertIn("settings loaded", process.stdout)

    def test_debug_reads_the_environment(self):
        process = boot(DJANGO_DEBUG="1", DJANGO_SECRET_KEY="a-key-from-the-environment")
        self.assertEqual(process.returncode, 0, msg=process.stderr)


class ResponseHeaderTests(TestCase):
    """SUI-05: the HTML pages carry the anti-clickjacking headers."""

    def setUp(self):
        helpers.seed()
        self.person = User.objects.get(username="profe")

    def test_login_page_has_both_headers(self):
        response = self.client.get("/acceso/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)

    def test_authenticated_page_has_both_headers(self):
        self.client.force_login(self.person)
        response = self.client.get("/examenes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_error_page_has_both_headers(self):
        self.client.force_login(self.person)
        response = self.client.get("/examenes/999999/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("Content-Security-Policy", response.headers)

    def test_json_responses_have_no_content_security_policy(self):
        response = self.client.get("/api/exams/")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("Content-Security-Policy", response.headers)

    def test_no_inline_script_is_needed_by_the_policy(self):
        """'default-src self' blocks inline scripts: the only one lives in a file."""
        response = self.client.get("/acceso/")
        body = response.content.decode()
        self.assertNotIn("<script>", body)
        self.assertIn("quiz/js/app.js", body)


class SeedOutputTests(TestCase):
    """SUI-04: the tokens are printed only when they are asked for."""

    def setUp(self):
        self.out = StringIO()
        call_command("seed_quiz", stdout=self.out)

    def test_tokens_are_not_printed_by_default(self):
        human = helpers.seed()
        output = self.out.getvalue()
        for key in human:
            self.assertNotIn(key, output)
        self.assertIn("--show-tokens", output)

    def test_tokens_are_printed_with_the_flag(self):
        human = helpers.seed()
        out = StringIO()
        call_command("seed_quiz", show_tokens=True, stdout=out)
        for key in human:
            self.assertIn(key, out.getvalue())

    def test_password_is_never_printed(self):
        out = StringIO()
        call_command("seed_quiz", password="S3cr3ta-de-prueba", show_tokens=True, stdout=out)
        self.assertNotIn("S3cr3ta-de-prueba", out.getvalue())