"""Tests for idlelib.timeline_tracer."""

from __future__ import annotations

import sys
import unittest

from idlelib import timeline_tracer


class TimelineTracerTest(unittest.TestCase):
    def tearDown(self):
        timeline_tracer.stop()
        timeline_tracer.clear()

    def test_captures_line_events_for_short_function(self):
        prev_trace = sys.gettrace()

        def target():
            a = 1
            b = 2
            c = a + b
            return c

        timeline_tracer.clear()
        timeline_tracer.start(max_events=2000)
        try:
            target()
        finally:
            timeline_tracer.stop()

        self.assertIs(sys.gettrace(), prev_trace)

        events = timeline_tracer.get_events()
        target_events = [
            e for e in events
            if e.get("filename") == __file__ and e.get("funcname") == "target"
        ]
        self.assertTrue(target_events, "Expected at least one event for target()")

        linenos = {e["lineno"] for e in target_events}
        first = target.__code__.co_firstlineno
        # Body lines should be traced.
        self.assertIn(first + 1, linenos)  # a = 1
        self.assertIn(first + 2, linenos)  # b = 2
        self.assertIn(first + 3, linenos)  # c = a + b


if __name__ == "__main__":
    unittest.main(verbosity=2)

