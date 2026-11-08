"""Pinned fallback metadata must describe the adapter copied during review."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vendor", ROOT / "tools/vendor.py")
vendor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vendor)


class VendorTests(unittest.TestCase):
    def test_reviewed_adapter_version_tracks_copied_bundle_and_preserves_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "example").mkdir()
            (root / "core.lock.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "application": "example",
                        "baseline": "1.0.0",
                        "adapter": "1.0.0",
                        "automatic_ui_patches": False,
                        "backend_updates": "reviewed",
                    }
                )
            )
            with contextlib.redirect_stdout(io.StringIO()):
                vendor.vendor("example", root, "example")
            value = json.loads((root / "core.lock.json").read_text())
            bundle = json.loads((ROOT / "dist/bundle.json").read_text())
            self.assertEqual(value["adapter"], bundle["version"])
            self.assertEqual(value["baseline"], bundle["version"])
            self.assertFalse(value["automatic_ui_patches"])
            self.assertEqual(value["backend_updates"], "reviewed")
            self.assertEqual(
                (root / "example/kagnode_core.py").read_bytes(),
                (ROOT / "dist/python/kagnode_core.py").read_bytes(),
            )
            self.assertEqual(
                value["fallback_manifest_sha256"],
                hashlib.sha256((ROOT / "dist/bundle.json").read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
