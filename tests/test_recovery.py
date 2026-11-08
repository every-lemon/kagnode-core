"""Actual updater process death must not leave misleading live-operation status."""

import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
import test_manager as fixtures

m = fixtures.m
ROOT = Path(__file__).resolve().parents[1]
CHILD = r"""
import importlib.util,json,sys,time
from pathlib import Path
root=Path(sys.argv[1]);mode=sys.argv[2]
spec=importlib.util.spec_from_file_location('child_manager',sys.argv[3]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
manager=m.Manager(root/'core',trusted=False);candidate=json.loads((root/'candidate.json').read_text())
manager._check=lambda name:{'candidate':candidate}
m.verify_signature=lambda *args:None
m.fetch=lambda *args:(root/'archive.bin').read_bytes()
def pause():
 (root/'ready').write_text('held')
 time.sleep(120)
if mode=='staging':
 m.tarfile.open=lambda *args,**kwargs:pause()
else:
 original=m.atomic
 def atomic(path,value):
  original(path,value)
  if path.name=='state.json' and value.get('version')==candidate['version']:pause()
 m.atomic=atomic
manager.install('example',7)
"""


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ManagerTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.path = self.fixture.path
        self.manager = self.fixture.manager

    def child(self, mode):
        candidate, blob = self.fixture.candidate()
        (self.path / "candidate.json").write_text(json.dumps(candidate))
        (self.path / "archive.bin").write_bytes(blob)
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                CHILD,
                str(self.path),
                mode,
                str(ROOT / "packages/python/manager.py"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.addCleanup(self.stop, process)
        deadline = time.monotonic() + 8
        while (
            not (self.path / "ready").exists()
            and process.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        self.assertTrue((self.path / "ready").exists(), process.poll())
        self.assertIsNone(process.poll())
        return process, candidate, blob

    def stop(self, process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def kill(self, process):
        self.assertIsNone(process.poll())
        process.kill()
        self.assertEqual(process.wait(timeout=5), -9)

    def test_killed_staging_recovers_and_retry_keeps_prior_ui_until_activation(self):
        process, candidate, blob = self.child("staging")
        state = self.manager.state("example")
        stages = list((self.manager.root / "releases").glob(".stage-*"))
        self.assertEqual(len(stages), 1)
        live = self.manager.status("example")
        self.assertEqual(live["operation"]["phase"], "downloading")
        self.assertTrue(stages[0].exists())
        self.kill(process)
        recovered = self.manager.status("example")
        self.assertEqual(recovered["operation"]["phase"], "interrupted")
        self.assertEqual(self.manager.state("example"), state)
        self.assertFalse(stages[0].exists())
        self.assertIn("current", recovered["operation"]["message"].lower())
        with (
            patch.object(self.manager, "_check", return_value={"candidate": candidate}),
            patch.object(m, "fetch", return_value=blob),
            patch.object(m, "verify_signature"),
        ):
            retried = self.manager.install("example", 7)
        self.assertEqual(retried["version"], "1.0.1")
        self.assertEqual(retried["previous"], "1.0.0")
        self.assertEqual(retried["operation"]["phase"], "complete")

    def test_killed_after_activation_reports_verified_completion_without_reapplying(
        self,
    ):
        process, candidate, blob = self.child("activated")
        self.kill(process)
        before = self.manager.state("example")
        with (
            patch.object(m, "verify_signature"),
            patch.object(
                m, "fetch", side_effect=AssertionError("Recovery must be offline")
            ),
        ):
            result = self.manager.status("example")
        self.assertEqual(result["operation"]["phase"], "complete")
        self.assertTrue(result["operation"]["recovered"])
        self.assertEqual(result["candidate"]["changed"], False) if result[
            "candidate"
        ] else None
        self.assertEqual(self.manager.state("example"), before)

    def test_cleanup_never_touches_unowned_staging_symlinks_or_release_caches(self):
        root = self.manager.root / "releases"
        owned = root / ".stage-owned"
        owned.mkdir()
        m.atomic(
            owned / ".kagnode-stage.json",
            {"schema": 1, "kind": "ui-cache", "root": str(self.manager.root)},
        )
        (owned / "download.tar.gz").write_bytes(b"incomplete known scratch")
        foreign = root / ".stage-foreign"
        foreign.mkdir()
        (foreign / "keep").write_text("retain")
        wrong = root / ".stage-other-root"
        wrong.mkdir()
        m.atomic(
            wrong / ".kagnode-stage.json",
            {"schema": 1, "kind": "ui-cache", "root": "/other"},
        )
        release = root / "1.0.1"
        release.mkdir()
        (release / "keep").write_text("retain")
        link = root / ".stage-link"
        link.symlink_to(foreign, target_is_directory=True)
        m.atomic(
            self.manager.app("example") / "operation.json",
            {"phase": "downloading", "version": "1.0.1", "at": 1},
        )
        self.manager.status("example")
        self.assertFalse(owned.exists())
        self.assertTrue((foreign / "keep").exists())
        self.assertTrue(wrong.exists())
        self.assertTrue((release / "keep").exists())
        self.assertTrue(link.is_symlink())

    def test_invalid_active_cache_is_not_reported_as_verified_completion(self):
        process, candidate, blob = self.child("activated")
        self.kill(process)
        (self.manager.root / "releases" / "1.0.1" / "core.js").write_bytes(b"tampered")
        before = self.manager.state("example")
        with patch.object(m, "verify_signature"):
            result = self.manager.status("example")
        self.assertEqual(result["operation"]["phase"], "interrupted")
        self.assertEqual(self.manager.state("example"), before)

    def test_startup_recovery_is_offline_and_preserves_disabled_policy(self):
        state = self.manager.state("example")
        state["automatic"] = False
        m.atomic(self.manager.app("example") / "state.json", state)
        m.atomic(
            self.manager.app("example") / "operation.json",
            {"phase": "downloading", "version": "1.0.1"},
        )
        with patch.object(m, "fetch", side_effect=AssertionError("Offline recovery")):
            self.manager.recover_pending()
        self.assertEqual(self.manager.state("example"), state)
        self.assertEqual(
            self.manager.status("example")["operation"]["phase"], "interrupted"
        )

    def test_adoption_requires_committed_declaration_even_if_ui_is_already_cached(self):
        process, candidate, blob = self.child("activated")
        self.kill(process)
        m.atomic(
            self.manager.app("example") / "operation.json",
            {
                "phase": "downloading",
                "action": "adopt",
                "version": "1.0.1",
                "declaration_sha256": "b" * 64,
            },
        )
        before = self.manager.state("example")
        with patch.object(m, "verify_signature"):
            result = self.manager.status("example")
        self.assertEqual(result["operation"]["phase"], "interrupted")
        self.assertEqual(self.manager.state("example"), before)

    def test_unprivileged_status_does_not_repair_root_owned_journal(self):
        m.atomic(
            self.manager.app("example") / "operation.json",
            {"phase": "downloading", "version": "1.0.1"},
        )
        before = (self.manager.app("example") / "operation.json").read_bytes()
        self.manager.trusted = True
        with patch.object(m.os, "geteuid", return_value=1000):
            result = self.manager.status("example")
        self.assertEqual(result["operation"]["phase"], "verification-required")
        self.assertEqual(
            (self.manager.app("example") / "operation.json").read_bytes(), before
        )

    def test_live_lock_prevents_recovery_or_cleanup_by_another_reader(self):
        m.atomic(
            self.manager.app("example") / "operation.json",
            {"phase": "downloading", "version": "1.0.1", "at": 1},
        )
        before = (self.manager.app("example") / "operation.json").read_bytes()
        with self.manager.lock():
            result = self.manager.status("example")
            self.assertEqual(result["operation"]["phase"], "downloading")
            self.assertEqual(
                (self.manager.app("example") / "operation.json").read_bytes(), before
            )
        self.assertEqual(
            self.manager.status("example")["operation"]["phase"], "interrupted"
        )


if __name__ == "__main__":
    unittest.main()
