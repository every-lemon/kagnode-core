import fcntl
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "packages/python/manager.py"
spec = importlib.util.spec_from_file_location("manager_locks", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
CHILD = """
import importlib.util,json,os,sys,threading
from pathlib import Path
os.umask(0o022)
spec=importlib.util.spec_from_file_location('manager',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
manager=m.Manager(Path(sys.argv[2]),trusted=False)
try:
 if sys.argv[3]=='operation':
  with manager.lock():pass
 else:
  stop=threading.Event();stop.set();m.serve(manager,stop)
 print(json.dumps({'outcome':'accepted'}))
except Exception as error:
 print(json.dumps({'outcome':type(error).__name__,'message':str(error)}))
"""


class ManagerLockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="core-lock-regression-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "core"
        self.manager = m.Manager(self.root, trusted=False)
        self.manager.ensure()

    def target(self, kind):
        return self.root / (
            ".operation.lock" if kind == "operation" else ".daemon.lock"
        )

    def run_manager(self, kind):
        try:
            result = subprocess.run(
                [sys.executable, "-c", CHILD, str(SOURCE), str(self.root), kind],
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            )
        except subprocess.TimeoutExpired:
            self.fail(f"Core {kind} lock blocked; isolated child killed and reaped")
        return json.loads(result.stdout)

    @staticmethod
    def metadata(path):
        value = path.lstat()
        return (
            value.st_dev,
            value.st_ino,
            value.st_uid,
            value.st_gid,
            stat.S_IMODE(value.st_mode),
            value.st_size,
        )

    def test_fifo_operation_fails_without_hanging(self):
        path = self.target("operation")
        os.mkfifo(path, 0o600)
        before = self.metadata(path)
        self.assertEqual(self.run_manager("operation")["outcome"], "ValueError")
        self.assertEqual(self.metadata(path), before)

    def test_fifo_daemon_fails_without_hanging(self):
        path = self.target("daemon")
        os.mkfifo(path, 0o600)
        before = self.metadata(path)
        self.assertEqual(self.run_manager("daemon")["outcome"], "ValueError")
        self.assertEqual(self.metadata(path), before)

    def test_nonregular_and_linked_controls_preserve_targets(self):
        for kind in ("operation", "daemon"):
            for form in ("symlink", "hardlink", "directory", "socket"):
                with self.subTest(kind=kind, form=form):
                    path = self.target(kind)
                    payload = self.root / "payload"
                    payload.write_bytes(b"Keep payload bytes\n")
                    if form == "symlink":
                        path.symlink_to(payload)
                    elif form == "hardlink":
                        os.link(payload, path)
                    elif form == "directory":
                        path.mkdir()
                    else:
                        listener = socket.socket(socket.AF_UNIX)
                        listener.bind(str(path))
                        listener.close()
                    before, original = self.metadata(path), self.metadata(payload)
                    try:
                        self.assertEqual(
                            self.run_manager(kind)["outcome"], "ValueError"
                        )
                        self.assertEqual(self.metadata(path), before)
                        self.assertEqual(self.metadata(payload), original)
                        self.assertEqual(payload.read_bytes(), b"Keep payload bytes\n")
                    finally:
                        if form == "directory":
                            path.rmdir()
                        else:
                            path.unlink()
                        payload.unlink()

    def test_writable_controls_are_rejected_without_repair(self):
        for kind in ("operation", "daemon"):
            for mode in (0o620, 0o602):
                with self.subTest(kind=kind, mode=oct(mode)):
                    path = self.target(kind)
                    path.write_bytes(b"Keep unsafe control\n")
                    path.chmod(mode)
                    before = self.metadata(path)
                    try:
                        self.assertEqual(
                            self.run_manager(kind)["outcome"], "ValueError"
                        )
                        self.assertEqual(self.metadata(path), before)
                        self.assertEqual(path.read_bytes(), b"Keep unsafe control\n")
                    finally:
                        path.unlink()

    @unittest.skipUnless(os.geteuid() == 0, "Ownership fixture requires root")
    def test_foreign_owner_is_rejected_without_chown(self):
        for kind in ("operation", "daemon"):
            with self.subTest(kind=kind):
                path = self.target(kind)
                path.write_bytes(b"Keep foreign-owned control\n")
                path.chmod(0o600)
                os.chown(path, 65534, -1)
                before = self.metadata(path)
                try:
                    self.assertEqual(self.run_manager(kind)["outcome"], "ValueError")
                    self.assertEqual(self.metadata(path), before)
                    self.assertEqual(path.read_bytes(), b"Keep foreign-owned control\n")
                finally:
                    path.unlink()

    def test_existing_regular_control_is_not_replaced_or_reformatted(self):
        for kind in ("operation", "daemon"):
            for mode in (0o600, 0o644):
                with self.subTest(kind=kind, mode=oct(mode)):
                    path = self.target(kind)
                    path.write_bytes(b"Preserve legacy control\n")
                    path.chmod(mode)
                    before = self.metadata(path)
                    try:
                        self.assertEqual(self.run_manager(kind)["outcome"], "accepted")
                        self.assertEqual(self.metadata(path), before)
                        self.assertEqual(
                            path.read_bytes(), b"Preserve legacy control\n"
                        )
                    finally:
                        path.unlink()

    def test_new_controls_are_private_regular_files(self):
        for kind in ("operation", "daemon"):
            with self.subTest(kind=kind):
                path = self.target(kind)
                self.assertEqual(self.run_manager(kind)["outcome"], "accepted")
                self.assertTrue(stat.S_ISREG(path.stat().st_mode))
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                self.assertEqual(path.stat().st_nlink, 1)

    def test_real_contention_remains_busy_and_recovers_after_release(self):
        for kind, outcome in (
            ("operation", "OperationBusy"),
            ("daemon", "BlockingIOError"),
        ):
            with self.subTest(kind=kind):
                path = self.target(kind)
                path.write_bytes(b"Held control\n")
                path.chmod(0o600)
                before = self.metadata(path)
                with path.open("r+") as held:
                    fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.assertEqual(self.run_manager(kind)["outcome"], outcome)
                    self.assertEqual(self.metadata(path), before)
                self.assertEqual(self.run_manager(kind)["outcome"], "accepted")
                self.assertEqual(self.metadata(path), before)
                self.assertEqual(path.read_bytes(), b"Held control\n")

    def test_startup_failure_releases_daemon_lock_with_retained_traceback(self):
        stop = threading.Event()
        stop.set()
        error = None
        with patch.object(
            self.manager, "recover_pending", side_effect=ValueError("fixture")
        ):
            try:
                m.serve(self.manager, stop)
            except ValueError as caught:
                error = caught
        self.assertIsNotNone(error)
        self.assertIsNotNone(error.__traceback__)
        try:
            with self.target("daemon").open("r+") as probe:
                try:
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    self.fail("Failed daemon startup retained its lock descriptor")
        finally:
            error.__traceback__ = None


if __name__ == "__main__":
    unittest.main()
