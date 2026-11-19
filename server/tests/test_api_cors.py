import unittest
from fastapi.testclient import TestClient

from app.api.main import app, _allowed_origins


class CorsMiddlewareTests(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_default_origins_include_common_dev_ports(self):
        origins = _allowed_origins()
        self.assertIn("http://localhost:3000", origins)
        self.assertIn("http://localhost:5173", origins)
        self.assertIn("http://127.0.0.1:3000", origins)
        self.assertIn("http://127.0.0.1:5173", origins)

    def test_preflight_options_for_allowed_origin(self):
        response = self.client.options(
            "/healthz",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3000")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("GET", response.headers.get("access-control-allow-methods", ""))

    def test_get_request_includes_cors_header_for_allowed_origin(self):
        response = self.client.get(
            "/healthz",
            headers={"Origin": "http://localhost:5173"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_disallowed_origin_does_not_get_cors_headers(self):
        response = self.client.get(
            "/healthz",
            headers={"Origin": "http://untrusted-site.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
