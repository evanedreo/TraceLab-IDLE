"""Tests for idlelib.timeline_pipeline."""

from __future__ import annotations

import unittest

from idlelib.timeline_pipeline import events_to_steps


def _make_event(step, lineno, funcname="target", filename="test.py",
                locals_=None):
    return {
        "step": step,
        "lineno": lineno,
        "funcname": funcname,
        "filename": filename,
        "locals": locals_ if locals_ is not None else {},
    }


class EventsToStepsTest(unittest.TestCase):

    def test_empty_events_returns_empty_list(self):
        self.assertEqual(events_to_steps([]), [])

    def test_single_event_produces_correct_schema(self):
        events = [_make_event(0, 1, locals_={"a": 1})]
        steps = events_to_steps(events)

        self.assertEqual(len(steps), 1)
        s = steps[0]
        self.assertEqual(s["index"], 0)
        self.assertEqual(s["filename"], "test.py")
        self.assertEqual(s["lineno"], 1)
        self.assertEqual(s["funcname"], "target")
        self.assertIsInstance(s["locals"], dict)
        self.assertIn("diff", s)
        for key in ("added", "removed", "changed"):
            self.assertIn(key, s["diff"])

    def test_multiple_events_produce_correct_diffs(self):
        events = [
            _make_event(0, 1, locals_={"a": 1}),
            _make_event(1, 2, locals_={"a": 1, "b": 2}),
            _make_event(2, 3, locals_={"a": 1, "b": 10}),
        ]
        steps = events_to_steps(events)

        self.assertEqual(len(steps), 3)

        self.assertEqual(steps[1]["diff"]["added"], {"b": "2"})
        self.assertEqual(steps[1]["diff"]["removed"], {})
        self.assertEqual(steps[1]["diff"]["changed"], {})

        self.assertEqual(steps[2]["diff"]["added"], {})
        self.assertEqual(steps[2]["diff"]["removed"], {})
        self.assertEqual(
            steps[2]["diff"]["changed"],
            {"b": {"before": "2", "after": "10"}},
        )

    def test_builtins_filtered_from_locals(self):
        events = [
            _make_event(0, 1, locals_={"x": 1, "__builtins__": {...}}),
        ]
        steps = events_to_steps(events)

        self.assertNotIn("__builtins__", steps[0]["locals"])
        self.assertIn("x", steps[0]["locals"])

    def test_non_dict_locals_handled_gracefully(self):
        events = [_make_event(0, 1, locals_=None)]
        steps = events_to_steps(events)

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["locals"], {})

    def test_removed_variable_appears_in_diff(self):
        events = [
            _make_event(0, 1, locals_={"a": 1, "b": 2}),
            _make_event(1, 2, locals_={"a": 1}),
        ]
        steps = events_to_steps(events)

        self.assertEqual(steps[1]["diff"]["removed"], {"b": "2"})

    def test_locals_values_are_string_reprs(self):
        events = [_make_event(0, 1, locals_={"x": [1, 2, 3]})]
        steps = events_to_steps(events)

        self.assertEqual(steps[0]["locals"]["x"], "[1, 2, 3]")

    def test_many_events_do_not_crash(self):
        events = [
            _make_event(i, i + 1, locals_={"counter": i})
            for i in range(1000)
        ]
        steps = events_to_steps(events)

        self.assertEqual(len(steps), 1000)
        self.assertEqual(steps[999]["locals"]["counter"], "999")


if __name__ == "__main__":
    unittest.main(verbosity=2)
