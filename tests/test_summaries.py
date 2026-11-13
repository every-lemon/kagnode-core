"""Public summaries require real verified automatic activation and local subjects."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
import test_manager as fixtures

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "notice_sdk", ROOT / "dist/python/kagnode_core.py"
)
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)
m = fixtures.m
NOTICE = {
    "id": "a" * 64,
    "version": "5.0.7",
    "title": "A clearer interface",
    "items": ["Improved navigation."],
}


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ManagerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.manager = self.fixture.manager

    def install(self, automatic=True, notes=True):
        f = self.fixture
        if notes:
            f.manifest["user_summary"] = {
                "title": "Clearer controls",
                "items": ["Improved navigation."],
            }
        candidate, blob = f.candidate()
        with (
            patch.object(self.manager, "_check", return_value={"candidate": candidate}),
            patch.object(m, "fetch", return_value=blob),
            patch.object(m, "verify_signature"),
        ):
            self.manager.install("example", 7, automatic=automatic)

    def test_only_changed_automatic_activation_emits_signed_public_summary(self):
        self.assertIsNone(self.manager.summary("example")["notice"])
        self.install()
        with patch.object(m, "verify_signature") as verify:
            value = self.manager.summary("example")
            self.assertTrue(verify.called)
        self.assertEqual(set(value["notice"]), {"id", "version", "title", "items"})
        self.assertEqual(value["notice"]["version"], "1.0.1")
        self.manager.policy("example", summaries=False)
        self.assertIsNone(self.manager.summary("example")["notice"])
        self.manager.policy("example", summaries=True)
        with patch.object(m, "verify_signature"):
            self.assertIsNotNone(self.manager.summary("example")["notice"])
        self.manager.rollback("example")
        self.assertIsNone(self.manager.summary("example")["notice"])

    def test_manual_activation_and_legacy_manifest_never_invent_a_notice(self):
        self.install(automatic=False)
        self.assertIsNone(self.manager.summary("example")["notice"])

    def test_old_signed_manifest_without_notes_is_supported(self):
        self.install(notes=False)
        with patch.object(m, "verify_signature"):
            self.assertIsNone(self.manager.summary("example")["notice"])

    def test_failed_activation_does_not_create_notice(self):
        candidate, _ = self.fixture.candidate()
        with (
            patch.object(self.manager, "_check", return_value={"candidate": candidate}),
            patch.object(
                self.manager, "_cache", side_effect=ValueError("Broken download")
            ),
        ):
            with self.assertRaises(ValueError):
                self.manager.install("example", 7, automatic=True)
        self.assertIsNone(self.manager.summary("example")["notice"])

    def test_summary_requires_completed_activation_and_valid_signature(self):
        self.install()
        operation = self.manager.app("example") / "operation.json"
        m.atomic(operation, {"phase": "failed", "version": "1.0.1"})
        self.assertIsNone(self.manager.summary("example")["notice"])
        m.atomic(operation, {"phase": "complete", "version": "1.0.1"})
        with patch.object(
            m, "verify_signature", side_effect=ValueError("bad signature")
        ):
            with self.assertRaises(ValueError):
                self.manager.summary("example")

    def test_public_note_metadata_rejects_html_private_fields_and_unbounded_text(self):
        for value in [
            {"title": "<script>", "items": ["No"]},
            {"title": "Fine", "items": ["x" * 241]},
            {"title": "Fine", "items": ["Fine"], "path": "/secret"},
            {"title": "Fine", "items": []},
        ]:
            with self.assertRaises(ValueError):
                m.validate_summary(value)

    def test_public_sdk_is_subject_scoped_and_never_relays_admin_errors(self):
        receipts = set()
        with patch.object(
            sdk, "manager_request", return_value={"available": True, "notice": NOTICE}
        ):
            self.assertEqual(
                sdk.read_notice("example", "user-a", lambda u, i: (u, i) in receipts)[
                    "notice"
                ],
                NOTICE,
            )
            sdk.dismiss_notice(
                "example", "user-a", NOTICE["id"], lambda u, i: receipts.add((u, i))
            )
            self.assertIsNone(
                sdk.read_notice("example", "user-a", lambda u, i: (u, i) in receipts)[
                    "notice"
                ]
            )
            self.assertEqual(
                sdk.read_notice("example", "user-b", lambda u, i: (u, i) in receipts)[
                    "notice"
                ],
                NOTICE,
            )
            with self.assertRaises(ValueError):
                sdk.dismiss_notice("example", "user-a", "b" * 64, lambda *_: None)
        with patch.object(
            sdk, "manager_request", side_effect=ValueError("/private/root/state.json")
        ):
            self.assertEqual(
                sdk.read_notice("example", "user-a", lambda *_: False),
                {"available": False, "notice": None},
            )

    def test_flask_ordinary_dismissal_uses_auth_and_csrf_not_admin_stepup(self):
        from flask import Flask, request

        app = Flask(__name__)
        saved = []

        def authenticated(fn):
            def guarded(*args, **kw):
                if request.headers.get("Session") != "user":
                    return {"error": "Sign in"}, 401
                if request.method == "POST" and request.headers.get("CSRF") != "token":
                    return {"error": "CSRF"}, 403
                return fn(*args, **kw)

            return guarded

        def admin_guard(fn):
            return lambda: ({"error": "Admin only"}, 403)

        sdk.register_flask_api(
            app,
            "example",
            authenticated,
            lambda: False,
            admin_guard,
            notice_subject=lambda: "user-a",
            notice_is_dismissed=lambda *_: False,
            notice_dismiss=lambda u, i: saved.append((u, i)),
        )
        client = app.test_client()
        with patch.object(
            sdk, "manager_request", return_value={"available": True, "notice": NOTICE}
        ):
            self.assertEqual(
                client.get("/api/v1/kagnode-core/whats-new").status_code, 401
            )
            self.assertEqual(
                client.get(
                    "/api/v1/kagnode-core/whats-new", headers={"Session": "user"}
                ).json["notice"],
                NOTICE,
            )
            self.assertEqual(
                client.post(
                    "/api/v1/kagnode-core/whats-new/dismiss",
                    json={"id": NOTICE["id"]},
                    headers={"Session": "user"},
                ).status_code,
                403,
            )
            self.assertEqual(
                client.post(
                    "/api/v1/kagnode-core/whats-new/dismiss",
                    json={"id": NOTICE["id"]},
                    headers={"Session": "user", "CSRF": "token"},
                ).status_code,
                200,
            )
            self.assertEqual(saved, [("user-a", NOTICE["id"])])
            self.assertEqual(
                client.post(
                    "/api/v1/kagnode-core/apply",
                    json={},
                    headers={"Session": "user", "CSRF": "token"},
                ).status_code,
                403,
            )
