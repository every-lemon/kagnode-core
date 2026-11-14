import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

s = importlib.util.spec_from_file_location(
    "channel_manager",
    Path(__file__).resolve().parents[1] / "packages/python/manager.py",
)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)


class Channels(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        manager = m.Manager(Path(temp.name) / "core", trusted=False)
        manager.ensure()
        manager.app("example").mkdir()
        m.atomic(
            manager.app("example") / "state.json",
            {
                "version": "5.0.9",
                "baseline": "5.0.9",
                "automatic": False,
                "uid": 0,
                "gid": 0,
            },
        )
        return manager

    def test_beta_order_and_no_implicit_downgrade(self):
        self.assertLess(m.version("5.0.10-beta.2"), m.version("5.0.10-beta.10"))
        self.assertLess(m.version("5.0.10-beta.10"), m.version("5.0.10"))
        self.assertLess(m.version("5.0.10"), m.version("5.0.11-beta.1"))
        for v in ("5.1.x", "5.0.10-beta.0", "5.0.10-beta.01", "../5.0.10"):
            with self.assertRaises(ValueError):
                m.version(v)

    def test_channel_and_auto_are_independent(self):
        manager = self.fixture()
        state = manager.policy("example", channel="beta")
        self.assertEqual(state["channel"], "beta")
        self.assertFalse(state["automatic"])
        state = manager.policy("example", automatic=True)
        self.assertEqual(state["channel"], "beta")
        self.assertEqual(state["mode"], "auto")
        for value in ("nightly", True):
            with self.assertRaises(ValueError):
                manager.policy("example", channel=value)

    def test_stable_filters_beta_and_switching_back_does_not_downgrade(self):
        manager = self.fixture()
        releases = [
            {
                "id": 1,
                "tag_name": "v5.0.10-beta.1",
                "prerelease": True,
                "assets": [
                    {"name": "core-manifest.json"},
                    {"name": "core-manifest.sig"},
                ],
            }
        ]
        with patch.object(m, "fetch", return_value=json.dumps(releases).encode()):
            self.assertIsNone(manager.check("example")["candidate"])
        manager.policy("example", channel="beta")
        with (
            patch.object(m, "fetch", return_value=json.dumps(releases).encode()),
            patch.object(
                manager,
                "_release_candidate",
                return_value={"version": "5.0.10-beta.1", "release_id": 1},
            ) as candidate,
        ):
            self.assertEqual(
                manager.check("example")["candidate"]["version"], "5.0.10-beta.1"
            )
            self.assertTrue(candidate.call_args.kwargs["allow_beta"])
        state = manager.state("example")
        m.atomic(
            manager.app("example") / "state.json", {**state, "version": "5.0.11-beta.1"}
        )
        manager.policy("example", channel="stable")
        releases[0].update(tag_name="v5.0.10", prerelease=False)
        with patch.object(m, "fetch", return_value=json.dumps(releases).encode()):
            self.assertIsNone(manager.check("example")["candidate"])
