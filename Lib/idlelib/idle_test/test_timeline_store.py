"""Tests for idlelib.timeline_store."""

from __future__ import annotations

import unittest

from idlelib.timeline_store import TimelineStore, diff


class _BadEq:
    def __eq__(self, other):
        raise RuntimeError("cannot compare")


class _BadRepr:
    def __repr__(self):
        raise RuntimeError("cannot repr")

    def __eq__(self, other):
        raise RuntimeError("cannot compare")


class TimelineStoreTest(unittest.TestCase):
    def test_store_event_and_get_step_ordering(self):
        store = TimelineStore()
        first = {"step": 1, "locals": {"a": "1"}}
        second = {"step": 2, "locals": {"a": "2"}}

        store.store_event(first)
        store.store_event(second)

        self.assertEqual(store.get_step(0)["step"], 1)
        self.assertEqual(store.get_step(1)["step"], 2)

    def test_get_step_out_of_range_raises_index_error(self):
        store = TimelineStore()
        store.store_event({"step": 1, "locals": {"a": "1"}})

        with self.assertRaises(IndexError):
            store.get_step(99)

    def test_diff_detects_added_removed_changed(self):
        prev = {"a": "1", "b": "2"}
        curr = {"b": "3", "c": "4"}

        result = diff(prev, curr)
        self.assertEqual(result["added"], {"c": "4"})
        self.assertEqual(result["removed"], {"a": "1"})
        self.assertEqual(result["changed"], {"b": {"before": "2", "after": "3"}})

    def test_diff_steps_uses_locals_snapshot(self):
        store = TimelineStore()
        store.store_event({"step": 1, "locals": {"x": "10", "y": "20"}})
        store.store_event({"step": 2, "locals": {"x": "11", "z": "30"}})

        result = store.diff_steps(0, 1)
        self.assertEqual(result["added"], {"z": "30"})
        self.assertEqual(result["removed"], {"y": "20"})
        self.assertEqual(result["changed"], {"x": {"before": "10", "after": "11"}})

    def test_diff_steps_handles_missing_or_non_mapping_locals(self):
        store = TimelineStore()
        store.store_event({"step": 1, "locals": None})
        store.store_event({"step": 2, "locals": 123})

        result = store.diff_steps(0, 1)
        self.assertEqual(result["added"], {})
        self.assertEqual(result["removed"], {})
        self.assertEqual(result["changed"], {})

    def test_diff_handles_unusual_values_without_crashing(self):
        result = diff({"k": _BadEq()}, {"k": _BadRepr()})
        self.assertIn("k", result["changed"])
        self.assertIn("before", result["changed"]["k"])
        self.assertIn("after", result["changed"]["k"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

