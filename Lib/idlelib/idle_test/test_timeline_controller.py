"""Tests for idlelib.timeline_controller."""

from __future__ import annotations

import unittest

try:
    from idlelib.timeline_controller import TimelineController
except Exception:
    from timeline_controller import TimelineController  # type: ignore[no-redef]


class _DummyInterp:
    rpcclt = None


class _DummyPyShell:
    interp = _DummyInterp()


class TimelineControllerFilterTest(unittest.TestCase):
    def setUp(self):
        self.controller = TimelineController(_DummyPyShell())

    def test_excludes_idlelib_paths(self):
        event = {"filename": "/repo/Lib/idlelib/rpc.py"}
        self.assertFalse(self.controller._is_user_event(event))

    def test_excludes_stdlib_paths(self):
        event = {"filename": "/opt/homebrew/Cellar/python@3.15/lib/python3.15/threading.py"}
        self.assertFalse(self.controller._is_user_event(event))

    def test_excludes_site_packages(self):
        event = {"filename": "/env/lib/python3.11/site-packages/pkg/mod.py"}
        self.assertFalse(self.controller._is_user_event(event))

    def test_excludes_angle_bracket_filenames(self):
        event = {"filename": "<frozen importlib._bootstrap>"}
        self.assertFalse(self.controller._is_user_event(event))

    def test_keeps_user_script(self):
        event = {"filename": "/Users/me/project/Test_Script.py"}
        self.assertTrue(self.controller._is_user_event(event))

    def test_prefer_user_events_filters_internals(self):
        events = [
            {"filename": "/repo/Lib/idlelib/rpc.py", "lineno": 1},
            {"filename": "/opt/homebrew/lib/python3.15/threading.py", "lineno": 2},
            {"filename": "/Users/me/Test.py", "lineno": 3},
        ]
        out = self.controller._prefer_user_events(events)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["filename"], "/Users/me/Test.py")

    def test_prefer_user_events_returns_empty_when_no_user_events(self):
        events = [{"filename": "/repo/Lib/idlelib/rpc.py", "lineno": 1}]
        out = self.controller._prefer_user_events(events)
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
