"""The contract viewer must stay usable: Swagger UI loads its assets from a CDN."""
from django.test import SimpleTestCase


class ContentSecurityPolicyDocsTests(SimpleTestCase):
    """The strict policy would block /api/docs/, so that page gets its own."""

    def test_the_strict_policy_still_protects_the_interface(self):
        response = self.client.get("/acceso/")
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertNotIn("jsdelivr", policy)

    def test_the_contract_viewer_allows_only_its_cdn(self):
        response = self.client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertIn("cdn.jsdelivr.net", policy)

    def test_the_contract_viewer_is_the_one_page_that_needs_the_cdn(self):
        page = self.client.get("/api/docs/").content.decode()
        self.assertIn("cdn.jsdelivr.net", page)

        for path in ("/acceso/", "/api/docs/"):
            policy = self.client.get(path).headers["Content-Security-Policy"]
            if path == "/api/docs/":
                continue
            self.assertNotIn("jsdelivr", policy, path)