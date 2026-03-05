"""Tests for idlelib.timeline_ui."""

from __future__ import annotations

import unittest

from test.support import requires
from tkinter import Tk

from idlelib.timeline_ui import TimelinePanel


def _step(index, lineno, locals_, diff, funcname="target", filename="test.py"):
    return {
        "index": index,
        "lineno": lineno,
        "funcname": funcname,
        "filename": filename,
        "locals": locals_,
        "diff": diff,
    }


class TimelinePanelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        requires("gui")
        cls.root = Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.update_idletasks()
        cls.root.destroy()
        del cls.root

    def setUp(self):
        self.panel = TimelinePanel(self.root)
        self.panel.pack_forget()
        self.steps = [
            _step(
                0,
                10,
                {"_hidden": "0", "__dunder__": "yes", "a": "1", "abc": "x"},
                {"added": {"a": "1", "abc": "x"}, "removed": {}, "changed": {}},
            ),
            _step(
                1,
                11,
                {"_hidden": "1", "a": "2", "b": "3"},
                {
                    "added": {"b": "3"},
                    "removed": {"abc": "x"},
                    "changed": {"a": {"before": "1", "after": "2"}},
                },
            ),
        ]
        self.panel.set_steps(self.steps)

    def tearDown(self):
        self.panel.destroy()

    def _values(self, tree):
        return [tree.item(i, "values") for i in tree.get_children("")]

    def test_select_step_populates_locals_and_diff_tables(self):
        self.panel.select_step(1)

        local_values = self._values(self.panel._locals_tree)
        self.assertEqual(local_values, [("_hidden", "1"), ("a", "2"), ("b", "3")])

        diff_values = self._values(self.panel._diff_tree)
        self.assertEqual(
            diff_values,
            [
                ("added", "b", "", "3"),
                ("removed", "abc", "x", ""),
                ("changed", "a", "1", "2"),
            ],
        )

    def test_filters_update_locals_immediately(self):
        self.panel.select_step(1)

        self.panel._hide_private.set(True)
        self.panel._refresh_selected_step_views()
        self.assertEqual(self._values(self.panel._locals_tree), [("a", "2"), ("b", "3")])

        self.panel._changed_only.set(True)
        self.panel._refresh_selected_step_views()
        self.assertEqual(self._values(self.panel._locals_tree), [("a", "2"), ("b", "3")])

        self.panel._var_filter.set("a")
        self.assertEqual(self._values(self.panel._locals_tree), [("a", "2")])

    def test_hide_private_filter_hides_underscore_names(self):
        self.panel.select_step(0)
        self.assertEqual(
            self._values(self.panel._locals_tree),
            [("__dunder__", "yes"), ("_hidden", "0"), ("a", "1"), ("abc", "x")],
        )

        self.panel._hide_private.set(True)
        self.panel._refresh_selected_step_views()
        self.assertEqual(self._values(self.panel._locals_tree), [("a", "1"), ("abc", "x")])

    def test_next_prev_navigation(self):
        self.assertTrue(self.panel.next_step())
        self.assertEqual(self.panel._selected_index, 0)

        self.assertTrue(self.panel.next_step())
        self.assertEqual(self.panel._selected_index, 1)

        self.assertFalse(self.panel.next_step())
        self.assertTrue(self.panel.prev_step())
        self.assertEqual(self.panel._selected_index, 0)

    def test_changed_rows_receive_tags(self):
        self.panel.select_step(1)

        local_items = self.panel._locals_tree.get_children("")
        local_tags = {
            self.panel._locals_tree.item(i, "values")[0]: self.panel._locals_tree.item(i, "tags")
            for i in local_items
        }
        self.assertEqual(local_tags["a"], ("changed_local",))
        self.assertEqual(local_tags["b"], ("changed_local",))
        self.assertEqual(local_tags["_hidden"], ())

        diff_items = self.panel._diff_tree.get_children("")
        diff_tags = [self.panel._diff_tree.item(i, "tags") for i in diff_items]
        self.assertEqual(diff_tags, [("added",), ("removed",), ("changed",)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
