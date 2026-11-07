import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from flask import Flask, request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "sdk", ROOT / "dist/python/kagnode_core.py"
)
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)


class AdapterTests(unittest.TestCase):
    def test_local_assets_and_authenticated_admin_boundary(self):
        app = Flask(__name__)
        sdk.register_flask(app, "fixture")

        def auth(fn):
            def check(*args, **kwargs):
                if request.headers.get("Session") != "fixture":
                    return {"error": "Sign in"}, 401
                if (
                    request.method == "POST"
                    and request.headers.get("CSRF") != "fixture"
                ):
                    return {"error": "Invalid CSRF"}, 403
                return fn(*args, **kwargs)

            return check

        sdk.register_flask_api(
            app, "fixture", auth, lambda: request.headers.get("Role") == "admin"
        )

        @app.get("/")
        def home():
            return "<html><head><title>Fixture</title></head><body></body></html>"

        client = app.test_client()
        response = client.get("/")
        self.assertIn(b'name="kagnode-core"', response.data)
        self.assertEqual(
            response.headers["Cross-Origin-Opener-Policy"], "same-origin-allow-popups"
        )
        name = sdk.BUNDLE["entrypoints"]["script"]
        self.assertEqual(client.get("/kagnode-core/1.0.0/" + name).status_code, 200)
        self.assertEqual(client.get("/kagnode-core/1.0.0/secret.py").status_code, 404)
        self.assertEqual(client.get("/api/v1/kagnode-core/status").status_code, 401)
        self.assertEqual(
            client.get(
                "/api/v1/kagnode-core/status", headers={"Session": "fixture"}
            ).status_code,
            403,
        )
        with patch.object(
            sdk, "manager_request", return_value={"version": "1.0.0"}
        ) as manager:
            self.assertEqual(
                client.get(
                    "/api/v1/kagnode-core/status",
                    headers={"Session": "fixture", "Role": "admin"},
                ).status_code,
                200,
            )
            self.assertEqual(
                client.get(
                    "/api/v1/kagnode-core/apply",
                    headers={"Session": "fixture", "Role": "admin"},
                ).status_code,
                405,
            )
            self.assertEqual(
                client.post(
                    "/api/v1/kagnode-core/apply",
                    headers={"Session": "fixture", "Role": "admin"},
                    json={},
                ).status_code,
                403,
            )
            self.assertEqual(
                client.post(
                    "/api/v1/kagnode-core/apply",
                    headers={"Session": "fixture", "Role": "admin", "CSRF": "fixture"},
                    json={"release_id": 1},
                ).status_code,
                200,
            )
            self.assertEqual(manager.call_count, 2)
