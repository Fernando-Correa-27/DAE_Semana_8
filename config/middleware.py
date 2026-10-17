"""Project middleware: response headers Django does not add on its own."""
from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """Add the configured ``Content-Security-Policy`` to HTML responses only.

    The API answers JSON and the static files are served by the web server; a CSP
    says nothing useful about either of them, so it is left out of those responses
    (SUI-05).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        if content_type.startswith("text/html"):
            response.headers.setdefault(
                "Content-Security-Policy", settings.CONTENT_SECURITY_POLICY
            )
        return response