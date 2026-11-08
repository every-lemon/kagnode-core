import base64
import hashlib
import importlib.util
import io
import http.client
import os
import socket
import threading
import time
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "manager", ROOT / "packages/python/manager.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ManagerTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.path = Path(t.name)
        self.manager = m.Manager(self.path / "core", trusted=False)
        self.manager.ensure()
        p = self.manager.app("example")
        p.mkdir()
        m.atomic(
            p / "state.json",
            {
                "version": "1.0.0",
                "baseline": "1.0.0",
                "automatic": True,
                "uid": 0,
                "gid": 0,
                "previous": None,
            },
        )
        data = b'console.log("Core")'
        self.data = data
        self.manifest = {
            "schema": 1,
            "repository": m.REPOSITORY,
            "version": "1.0.1",
            "ui_api": 1,
            "adapter_api": 1,
            "kind": "ui",
            "source_commit": "a" * 40,
            "entrypoints": {
                "theme": "core.js",
                "script": "core.js",
                "style": "core.js",
            },
            "files": {
                "core.js": {
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                }
            },
        }

    def candidate(self, unsafe=False):
        b = io.BytesIO()
        with tarfile.open(fileobj=b, mode="w:gz") as t:
            item = tarfile.TarInfo(
                "../escape.js" if unsafe else "kagnode-core-1.0.1/core.js"
            )
            item.size = len(self.data)
            t.addfile(item, io.BytesIO(self.data))
        blob = b.getvalue()
        self.manifest["archive"] = {
            "name": "ui.tar.gz",
            "sha256": hashlib.sha256(blob).hexdigest(),
            "size": len(blob),
        }
        raw = json.dumps(self.manifest).encode()
        return {
            "version": "1.0.1",
            "release_id": 7,
            "manifest": self.manifest,
            "signature": base64.b64encode(b"x").decode(),
            "raw": base64.b64encode(raw).decode(),
            "url": "https://github.com/every-lemon/kagnode-core/releases/download/v1.0.1/ui.tar.gz",
            "changed": True,
        }, blob

    def test_atomic_patch_preserves_prior_and_rollback_pauses_auto(self):
        candidate, blob = self.candidate()
        with (
            patch.object(self.manager, "_check", return_value={"candidate": candidate}),
            patch.object(m, "fetch", return_value=blob),
            patch.object(m, "verify_signature"),
        ):
            result = self.manager.install("example", 7)
        self.assertEqual(result["version"], "1.0.1")
        self.assertEqual(result["previous"], "1.0.0")
        self.assertFalse(result["candidate"]["changed"])
        self.assertFalse(self.manager.rollback("example")["automatic"])
        self.assertEqual(self.manager.state("example")["version"], "1.0.0")

    def test_background_check_respects_an_active_manual_operation(self):
        before = self.manager.state("example")
        with self.manager.lock():
            self.manager.cycle()
            self.assertEqual(self.manager.state("example"), before)

    def test_background_failure_is_recorded_under_the_operation_lock(self):
        original = m.atomic

        def guarded_atomic(path, value):
            with self.assertRaisesRegex(ValueError, "Another Core operation"):
                with self.manager.lock():
                    pass
            original(path, value)

        with (
            patch.object(self.manager, "check", side_effect=ValueError("Offline")),
            patch.object(m, "atomic", side_effect=guarded_atomic),
        ):
            self.manager.cycle()
        self.assertEqual(self.manager.state("example")["last_error"], "Offline")

    def test_background_failure_does_not_overwrite_a_new_manual_operation(self):
        before = self.manager.state("example")
        with (
            patch.object(self.manager, "check", side_effect=ValueError("Offline")),
            patch.object(self.manager, "lock", side_effect=m.OperationBusy("Busy")),
        ):
            self.manager.cycle()
        self.assertEqual(self.manager.state("example"), before)

    def test_stale_review_and_unsafe_archive_leave_current_untouched(self):
        candidate, blob = self.candidate(unsafe=True)
        with (
            patch.object(self.manager, "_check", return_value={"candidate": candidate}),
            patch.object(m, "fetch", return_value=blob),
            patch.object(m, "verify_signature"),
        ):
            with self.assertRaisesRegex(ValueError, "reviewed"):
                self.manager.install("example", 8)
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                self.manager.install("example", 7)
        self.assertEqual(self.manager.state("example")["version"], "1.0.0")
        self.assertFalse((self.path / "escape.js").exists())

    def test_backend_payload_and_minor_upgrade_are_rejected(self):
        self.manifest["kind"] = "backend"
        with self.assertRaises(ValueError):
            m.validate_manifest(self.manifest)
        for value in ["1.0.0-preview.1", "../../1.0.0", "1.0", "one"]:
            with self.assertRaises(ValueError):
                m.version(value)

    def test_checksum_failure_retains_old(self):
        candidate, blob = self.candidate()
        with (
            patch.object(self.manager, "_check", return_value={"candidate": candidate}),
            patch.object(m, "fetch", return_value=b"broken"),
            patch.object(m, "verify_signature"),
        ):
            with self.assertRaisesRegex(ValueError, "checksum"):
                self.manager.install("example", 7)
        self.assertEqual(self.manager.state("example")["version"], "1.0.0")

    def test_signature_tampering_rejected(self):
        key = self.path / "key"
        pub = self.path / "pub"
        data = self.path / "data"
        sig = self.path / "sig"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(key)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(key), "-pubout", "-out", str(pub)],
            check=True,
            capture_output=True,
        )
        data.write_bytes(b"original")
        subprocess.run(
            [
                "openssl",
                "pkeyutl",
                "-sign",
                "-rawin",
                "-inkey",
                str(key),
                "-in",
                str(data),
                "-out",
                str(sig),
            ],
            check=True,
            capture_output=True,
        )
        m.verify_signature(b"original", sig.read_bytes(), pub.read_text())
        with self.assertRaisesRegex(ValueError, "signature"):
            m.verify_signature(b"tampered", sig.read_bytes(), pub.read_text())

    def test_redirects_rejected_before_requesting_an_untrusted_host(self):
        with self.assertRaisesRegex(ValueError, "redirect"):
            m.TrustedRedirect().redirect_request(
                None, None, 302, "Found", {}, "http://127.0.0.1/private"
            )
        for invalid in [[], None, {"version": "1.0.0", "files": {"core.js": None}}]:
            with self.assertRaises(ValueError):
                m.validate_manifest(invalid)

    def test_github_api_and_release_downloads_use_their_supported_media_types(self):
        for url, accept in [
            (
                "https://api.github.com/repos/every-lemon/kagnode-core/releases?per_page=50",
                "application/vnd.github+json",
            ),
            (
                "https://github.com/every-lemon/kagnode-core/releases/download/v1.0.1/core-manifest.json",
                "application/octet-stream",
            ),
        ]:
            with patch.object(m.urllib.request, "build_opener") as opener:
                response = opener.return_value.open.return_value.__enter__.return_value
                response.url = url
                response.read.return_value = b"{}"
                self.assertEqual(m.fetch(url), b"{}")
                request = opener.return_value.open.call_args.args[0]
                self.assertEqual(request.get_header("Accept"), accept)

    def test_socket_requests_reject_non_object_json_without_dropping_connection(self):
        state = self.manager.state("example")
        m.atomic(
            self.manager.app("example") / "state.json",
            {**state, "uid": os.getuid(), "gid": os.getgid()},
        )
        stop = threading.Event()
        address = self.manager.root / "run/example.sock"
        errors = []

        def run():
            try:
                m.serve(self.manager, stop)
            except Exception as error:
                errors.append(error)

        class Connection(http.client.HTTPConnection):
            def connect(connection):
                connection.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                connection.sock.settimeout(3)
                connection.sock.connect(str(address))

        with patch.object(m.os, "chown"), patch.object(self.manager, "cycle"):
            thread = threading.Thread(target=run)
            thread.start()
            try:
                deadline = time.monotonic() + 3
                while not address.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(address.exists(), errors)
                for body in [
                    [],
                    ["status"],
                    "status",
                    None,
                    7,
                    True,
                    {"action": "status"},
                    {"action": "adopt", "lock_file": "/unreviewed/core.lock.json"},
                ]:
                    connection = Connection("localhost", timeout=3)
                    try:
                        connection.request(
                            "POST",
                            "/",
                            json.dumps(body),
                            {"Content-Type": "application/json"},
                        )
                        response = connection.getresponse()
                        result = json.loads(response.read())
                        self.assertEqual(
                            response.status,
                            200 if body == {"action": "status"} else 400,
                        )
                        if body == {"action": "status"}:
                            self.assertEqual(result["version"], state["version"])
                        else:
                            self.assertIn("error", result)
                    finally:
                        connection.close()
            finally:
                stop.set()
                thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])

    def test_unknown_hosts_and_state_symlinks_rejected(self):
        for url in [
            "http://github.com/x",
            "https://attacker.test/x",
            "https://github.com/another/repo/releases/a",
        ]:
            with self.assertRaises(ValueError):
                m.fetch(url)
        p = self.manager.app("example") / "state.json"
        p.unlink()
        p.symlink_to(self.path / "outside")
        with self.assertRaises(ValueError):
            self.manager.state("example")


if __name__ == "__main__":
    unittest.main()
