"""Reviewed baseline changes must retain compatible policy and real rollback UI."""

import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import pwd
import tarfile
import tempfile
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "baseline_manager", ROOT / "packages/python/manager.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class BaselineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)
        self.manager = m.Manager(self.path / "core", trusted=False)
        self.manager.ensure()
        app = self.manager.app("example")
        app.mkdir()
        m.atomic(
            app / "state.json",
            {
                "version": "1.0.0",
                "baseline": "1.0.0",
                "adapter": "1.0.0",
                "automatic": True,
                "uid": os.getuid(),
                "gid": os.getgid(),
                "previous": None,
            },
        )

    def declaration(self, baseline="1.1.0", automatic=True, app="example"):
        data = {
            "schema": 1,
            "repository": m.REPOSITORY,
            "application": app,
            "baseline": baseline,
            "adapter": baseline,
            "ui_api": 1,
            "patch_range": ".".join(baseline.split(".")[:2]) + ".x",
            "automatic_ui_patches": automatic,
            "backend_updates": "reviewed",
            "source_commit": "b" * 40,
            "fallback_manifest_sha256": "e" * 64,
        }
        path = self.path / "core.lock.json"
        path.write_text(json.dumps(data))
        return path

    def candidate(self, version="1.0.1", source="a" * 40):
        data = b'console.log("Core")'
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            entry = tarfile.TarInfo("kagnode-core-" + version + "/core.js")
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
        blob = output.getvalue()
        manifest = {
            "schema": 1,
            "repository": m.REPOSITORY,
            "version": version,
            "ui_api": 1,
            "adapter_api": 1,
            "kind": "ui",
            "source_commit": source,
            "entrypoints": {k: "core.js" for k in ["theme", "script", "style"]},
            "files": {
                "core.js": {
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            },
            "archive": {
                "name": "ui.tar.gz",
                "size": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            },
        }
        return {
            "version": version,
            "release_id": 7,
            "manifest": manifest,
            "raw": base64.b64encode(json.dumps(manifest).encode()).decode(),
            "signature": base64.b64encode(b"fixture-signature").decode(),
            "url": "https://github.com/every-lemon/kagnode-core/releases/download/v"
            + version
            + "/ui.tar.gz",
            "changed": True,
        }, blob

    def install_old(self, version="1.0.1"):
        candidate, blob = self.candidate(version)
        with (
            patch.object(self.manager, "_check", return_value={"candidate": candidate}),
            patch.object(m, "fetch", return_value=blob),
            patch.object(m, "verify_signature"),
        ):
            return self.manager.install("example", 7)

    def test_bind_never_silently_chooses_an_old_minor_line(self):
        with self.assertRaisesRegex(ValueError, "baseline|declaration"):
            self.manager.bind("new", pwd.getpwuid(os.getuid()).pw_name)
        self.assertFalse((self.manager.app("new") / "state.json").exists())

    def test_cli_requires_a_baseline_or_application_declaration(self):
        with (
            patch.object(m, "Manager") as constructor,
            patch.object(sys, "argv", ["manager", "bind", "new", "--user", "root"]),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit) as error:
                m.main()
        self.assertEqual(error.exception.code, 2)
        constructor.assert_not_called()

    def test_binding_uses_declared_adapter_and_disabled_automatic_policy(self):
        lock = self.declaration(automatic=False, app="new")
        state = self.manager.bind(
            "new", pwd.getpwuid(os.getuid()).pw_name, lock_file=lock
        )
        self.assertEqual(
            (state["baseline"], state["version"], state["adapter"]), ("1.1.0",) * 3
        )
        self.assertFalse(state["automatic"])

    def test_application_lock_validation_rejects_incompatible_or_unsafe_inputs(self):
        lock = self.declaration(app="new")
        good = json.loads(lock.read_text())
        for field, value in [
            ("schema", True),
            ("repository", "other/repository"),
            ("application", "other"),
            ("baseline", "1.1.0-beta.1"),
            ("adapter", None),
            ("patch_range", "1.0.x"),
            ("automatic_ui_patches", "true"),
            ("source_commit", "bad"),
            ("backend_updates", "automatic"),
        ]:
            lock.write_text(json.dumps({**good, field: value}))
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.manager.bind(
                    "new", pwd.getpwuid(os.getuid()).pw_name, lock_file=lock
                )
        link = self.path / "link.json"
        link.symlink_to(lock)
        with self.assertRaises(ValueError):
            self.manager.bind("new", pwd.getpwuid(os.getuid()).pw_name, lock_file=link)
        lock.write_bytes(b" " * 16385)
        with self.assertRaises(ValueError):
            self.manager.bind("new", pwd.getpwuid(os.getuid()).pw_name, lock_file=lock)
        self.assertFalse((self.manager.app("new") / "state.json").exists())

    def test_manual_apply_can_cache_current_ui_without_erasing_prior_rollback(self):
        state = self.manager.state("example")
        m.atomic(
            self.manager.app("example") / "state.json",
            {**state, "version": "1.0.1", "baseline": "1.0.1", "previous": "1.0.0"},
        )
        candidate, blob = self.candidate()
        candidate["changed"] = False
        with (
            patch.object(self.manager, "_check", return_value={"candidate": candidate}),
            patch.object(m, "fetch", return_value=blob),
            patch.object(m, "verify_signature"),
        ):
            result = self.manager.install("example", 7)
        self.assertTrue(
            (self.manager.root / "releases/1.0.1/core-manifest.sig").is_file()
        )
        self.assertEqual(result["previous"], "1.0.0")
        self.assertEqual(result["version"], "1.0.1")

    def test_reviewed_minor_adoption_has_verified_rollback_and_preserves_pause(self):
        self.install_old()
        self.manager.policy("example", False)
        lock = self.declaration()
        candidate, blob = self.candidate("1.1.0", "b" * 40)
        with (
            patch.object(
                self.manager, "_resolve_version", return_value=candidate, create=True
            ),
            patch.object(m, "fetch", return_value=blob),
            patch.object(m, "verify_signature"),
        ):
            result = self.manager.adopt("example", lock, "1.0.0")
            self.assertEqual(
                (result["version"], result["baseline"], result["adapter"]),
                ("1.1.0",) * 3,
            )
            self.assertEqual(result["previous"], "1.0.1")
            self.assertFalse(result["automatic"])
            reverted = self.manager.rollback("example")
        self.assertEqual(reverted["version"], "1.0.1")
        self.assertEqual(reverted["baseline"], "1.1.0")
        self.assertFalse(reverted["automatic"])
        self.assertEqual(reverted["operation"]["version"], "1.0.1")

    def test_stale_review_and_failed_staging_preserve_active_state(self):
        self.install_old()
        before = self.manager.state("example")
        lock = self.declaration()
        candidate, blob = self.candidate("1.1.0", "b" * 40)
        with (
            patch.object(
                self.manager, "_resolve_version", return_value=candidate, create=True
            ),
            patch.object(m, "fetch", return_value=b"interrupted"),
            patch.object(m, "verify_signature"),
        ):
            with self.assertRaisesRegex(
                ValueError, "baseline.*changed|changed.*baseline"
            ):
                self.manager.adopt("example", lock, "1.0.9")
            with self.assertRaisesRegex(ValueError, "checksum"):
                self.manager.adopt("example", lock, "1.0.0")
        self.assertEqual(self.manager.state("example"), before)

    def test_declaration_drift_and_wrong_source_never_activate_a_baseline(self):
        self.install_old()
        before = self.manager.state("example")
        lock = self.declaration()
        candidate, blob = self.candidate("1.1.0", "b" * 40)

        def changed(*args):
            value = json.loads(lock.read_text())
            value["automatic_ui_patches"] = False
            lock.write_text(json.dumps(value))
            return blob

        with (
            patch.object(
                self.manager, "_resolve_version", return_value=candidate, create=True
            ),
            patch.object(m, "fetch", side_effect=changed),
            patch.object(m, "verify_signature"),
        ):
            with self.assertRaisesRegex(
                ValueError, "declaration.*changed|lock.*changed"
            ):
                self.manager.adopt("example", lock, "1.0.0")
        self.assertEqual(self.manager.state("example"), before)
        value = json.loads(lock.read_text())
        value["source_commit"] = "c" * 40
        lock.write_text(json.dumps(value))
        with patch.object(m, "verify_signature"):
            with self.assertRaisesRegex(ValueError, "source"):
                self.manager.adopt("example", lock, "1.0.0")
        self.assertEqual(self.manager.state("example"), before)

    def test_same_line_adoption_retains_a_newer_installed_patch(self):
        self.install_old()
        self.install_old("1.0.2")
        lock = self.declaration("1.0.1")
        value = json.loads(lock.read_text())
        value["source_commit"] = "a" * 40
        lock.write_text(json.dumps(value))
        with patch.object(m, "verify_signature"):
            result = self.manager.adopt("example", lock, "1.0.0")
        self.assertEqual(result["version"], "1.0.2")
        self.assertEqual(result["baseline"], "1.0.1")
        self.assertEqual(result["previous"], "1.0.1")

    def test_missing_rollback_bundle_blocks_minor_adoption(self):
        before = self.manager.state("example")
        lock = self.declaration()
        with patch.object(
            self.manager,
            "_resolve_version",
            side_effect=ValueError("No signed release"),
        ):
            with self.assertRaisesRegex(ValueError, "rollback"):
                self.manager.adopt("example", lock, "1.0.0")
        self.assertEqual(self.manager.state("example"), before)

    def test_exact_release_resolution_requires_stable_matching_signed_provenance(self):
        candidate, blob = self.candidate("1.1.0", "b" * 40)
        base = "https://github.com/" + m.REPOSITORY + "/releases/download/v1.1.0/"
        release = {
            "id": 7,
            "tag_name": "v1.1.0",
            "assets": [
                {"name": name, "browser_download_url": base + name}
                for name in ["core-manifest.json", "core-manifest.sig", "ui.tar.gz"]
            ],
        }

        def fetch(url, *args):
            if "api.github.com" in url:
                return json.dumps(release).encode()
            if url.endswith("core-manifest.json"):
                return base64.b64decode(candidate["raw"])
            return b"fixture-signature"

        with (
            patch.object(m, "fetch", side_effect=fetch),
            patch.object(m, "verify_signature") as verified,
        ):
            self.assertEqual(self.manager._resolve_version("1.1.0")["version"], "1.1.0")
            self.assertTrue(verified.called)
            release["prerelease"] = True
            with self.assertRaisesRegex(ValueError, "stable"):
                self.manager._resolve_version("1.1.0")
            release["prerelease"] = False
            release["tag_name"] = "v1.0.1"
            with self.assertRaisesRegex(ValueError, "tag"):
                self.manager._resolve_version("1.1.0")

    def test_automatic_install_cannot_cross_minor_lines(self):
        candidate, blob = self.candidate("1.1.0")
        with patch.object(
            self.manager, "_check", return_value={"candidate": candidate}
        ):
            with self.assertRaisesRegex(ValueError, "review"):
                self.manager.install("example", 7)
        self.assertEqual(self.manager.state("example")["version"], "1.0.0")


if __name__ == "__main__":
    unittest.main()
