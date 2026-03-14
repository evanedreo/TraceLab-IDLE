"""Timeline panel UI for visualizing execution steps and local variables.

This module is intentionally independent of IDLE integration. It provides a
pure-Tkinter panel (TimelinePanel) with two main areas:

- Left: a list of execution steps
- Right: filterable locals and diff tables for the selected step

The panel is designed to consume the step dicts produced by
`idlelib.timeline_pipeline.events_to_steps()`.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from typing import Any


class TimelinePanel(tk.Frame):
    """A Tkinter panel for displaying a variable timeline."""

    def __init__(self, master: tk.Misc | None = None, *, on_select=None) -> None:
        if master is None:
            root = tk.Toplevel()
            super().__init__(root)
            root.title("Timeline")
            root.geometry("900x600")
            self._owns_toplevel = True
        else:
            super().__init__(master)
            self._owns_toplevel = False

        self._on_select = on_select
        self._steps: list[dict[str, Any]] = []
        self._selected_index: int | None = None
        self._selected_step: dict[str, Any] | None = None

        self._build_ui()
        self.pack(fill="both", expand=True)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # Left: step list
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        self._title = ttk.Label(left, text="Steps", font=("TkDefaultFont", 10, "bold"))
        self._title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._list = tk.Listbox(left, activestyle="dotbox", exportselection=False)
        self._list.grid(row=1, column=0, sticky="nsew")
        self._list.bind("<<ListboxSelect>>", self._on_list_select)

        list_scroll = ttk.Scrollbar(left, orient="vertical", command=self._list.yview)
        list_scroll.grid(row=1, column=1, sticky="ns")
        self._list.configure(yscrollcommand=list_scroll.set)

        # Right: details
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        self._header = ttk.Label(right, text="No step selected", font=("TkDefaultFont", 10, "bold"))
        self._header.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._var_filter = tk.StringVar(self)
        self._changed_only = tk.BooleanVar(self, value=False)
        self._hide_private = tk.BooleanVar(self, value=False)

        toolbar = ttk.Frame(right)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        toolbar.columnconfigure(1, weight=1)

        ttk.Label(toolbar, text="Filter").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self._filter_entry = ttk.Entry(toolbar, textvariable=self._var_filter)
        self._filter_entry.grid(row=0, column=1, sticky="ew")
        self._changed_only_cb = ttk.Checkbutton(
            toolbar,
            text="Changed only",
            variable=self._changed_only,
            command=self._refresh_selected_step_views,
        )
        self._changed_only_cb.grid(row=0, column=2, sticky="w", padx=(8, 0))
        self._hide_private_cb = ttk.Checkbutton(
            toolbar,
            text="Hide private",
            variable=self._hide_private,
            command=self._refresh_selected_step_views,
        )
        self._hide_private_cb.grid(row=0, column=3, sticky="w", padx=(8, 0))
        self._var_filter.trace_add("write", self._on_filter_change)

        self._notebook = ttk.Notebook(right)
        self._notebook.grid(row=2, column=0, sticky="nsew")

        locals_tab = ttk.Frame(self._notebook)
        locals_tab.rowconfigure(0, weight=1)
        locals_tab.columnconfigure(0, weight=1)
        self._locals_tree = ttk.Treeview(
            locals_tab,
            columns=("name", "value"),
            show="headings",
        )
        self._locals_tree.heading("name", text="Name")
        self._locals_tree.heading("value", text="Value")
        self._locals_tree.column("name", width=180, anchor="w", stretch=False)
        self._locals_tree.column("value", width=420, anchor="w", stretch=True)
        self._locals_tree.grid(row=0, column=0, sticky="nsew")
        locals_scroll = ttk.Scrollbar(locals_tab, orient="vertical", command=self._locals_tree.yview)
        locals_scroll.grid(row=0, column=1, sticky="ns")
        self._locals_tree.configure(yscrollcommand=locals_scroll.set)
        self._notebook.add(locals_tab, text="Locals")

        diff_tab = ttk.Frame(self._notebook)
        diff_tab.rowconfigure(0, weight=1)
        diff_tab.columnconfigure(0, weight=1)
        self._diff_tree = ttk.Treeview(
            diff_tab,
            columns=("type", "name", "before", "after"),
            show="headings",
        )
        self._diff_tree.heading("type", text="Type")
        self._diff_tree.heading("name", text="Name")
        self._diff_tree.heading("before", text="Before")
        self._diff_tree.heading("after", text="After")
        self._diff_tree.column("type", width=90, anchor="w", stretch=False)
        self._diff_tree.column("name", width=140, anchor="w", stretch=False)
        self._diff_tree.column("before", width=180, anchor="w", stretch=True)
        self._diff_tree.column("after", width=180, anchor="w", stretch=True)
        self._diff_tree.grid(row=0, column=0, sticky="nsew")
        diff_scroll = ttk.Scrollbar(diff_tab, orient="vertical", command=self._diff_tree.yview)
        diff_scroll.grid(row=0, column=1, sticky="ns")
        self._diff_tree.configure(yscrollcommand=diff_scroll.set)
        self._diff_tree.tag_configure("added", background="#2e6a3a", foreground="#f2f2f2")
        self._diff_tree.tag_configure("removed", background="#6d3440", foreground="#f2f2f2")
        self._diff_tree.tag_configure("changed", background="#6b5c26", foreground="#f2f2f2")
        self._locals_tree.tag_configure(
            "changed_local",
            background="#665820",
            foreground="#f2f2f2",
        )
        self._notebook.add(diff_tab, text="Diff")

        self._bind_navigation(self._list)
        self._bind_navigation(self._locals_tree)
        self._bind_navigation(self._diff_tree)

    def clear(self) -> None:
        """Reset the panel, removing all steps and details."""
        self._steps = []
        self._selected_index = None
        self._selected_step = None
        self._list.delete(0, tk.END)
        self._set_header("No step selected")
        self._clear_table(self._locals_tree)
        self._clear_table(self._diff_tree)

    def set_steps(self, steps: list[dict[str, Any]]) -> None:
        """Accept UI-ready step dicts and populate the step list."""
        self._steps = list(steps or [])
        self._selected_index = None
        self._selected_step = None

        self._list.delete(0, tk.END)
        for step in self._steps:
            self._list.insert(tk.END, self._format_step_row(step))

        self._set_header("No step selected")
        self._clear_table(self._locals_tree)
        self._clear_table(self._diff_tree)

    def select_step(self, i: int) -> None:
        """Select step at index i (0-based) and update details panel."""
        if not (0 <= i < len(self._steps)):
            return

        if self._selected_index == i and self._list.curselection() == (i,):
            return

        self._list.selection_clear(0, tk.END)
        self._list.selection_set(i)
        self._list.activate(i)
        self._list.see(i)

        step = self._steps[i]
        self._selected_index = i
        self._selected_step = step
        self._set_header(self._format_step_header(step, i=i))
        self._refresh_selected_step_views()

        cb = self._on_select
        if cb is not None:
            try:
                cb(i, step)
            except Exception:
                pass

    def _on_list_select(self, _event) -> None:
        sel = self._list.curselection()
        if sel:
            self.select_step(int(sel[0]))

    def _on_filter_change(self, *_args) -> None:
        self._refresh_selected_step_views()

    def _bind_navigation(self, widget: tk.Misc) -> None:
        widget.bind("<Up>", self._on_key_prev, add="+")
        widget.bind("<Down>", self._on_key_next, add="+")
        widget.bind("k", self._on_key_prev, add="+")
        widget.bind("j", self._on_key_next, add="+")

    def _on_key_prev(self, _event=None):
        if self.prev_step():
            return "break"
        return None

    def _on_key_next(self, _event=None):
        if self.next_step():
            return "break"
        return None

    def next_step(self) -> bool:
        """Select the next step when possible."""
        if not self._steps:
            return False
        current = self._selected_index if self._selected_index is not None else -1
        nxt = min(current + 1, len(self._steps) - 1)
        if nxt == current:
            return False
        self.select_step(nxt)
        return True

    def prev_step(self) -> bool:
        """Select the previous step when possible."""
        if not self._steps:
            return False
        current = self._selected_index if self._selected_index is not None else 0
        prev = max(current - 1, 0)
        if prev == current:
            return False
        self.select_step(prev)
        return True

    def _set_header(self, header: str) -> None:
        self._header.configure(text=header)

    def _clear_table(self, tree: ttk.Treeview) -> None:
        children = tree.get_children("")
        if children:
            tree.delete(*children)

    def _refresh_selected_step_views(self) -> None:
        step = self._selected_step
        if step is None:
            self._clear_table(self._locals_tree)
            self._clear_table(self._diff_tree)
            return
        self._populate_diff(step)
        self._populate_locals(step)

    def _filtered_local_names(
        self,
        locals_map: dict[str, Any],
        changed_names: set[str],
    ) -> list[str]:
        term = self._var_filter.get().strip().lower()
        changed_only = bool(self._changed_only.get())
        hide_private = bool(self._hide_private.get())

        names: list[str] = []
        for name in sorted(locals_map):
            if hide_private and name.startswith("_"):
                continue
            if changed_only and name not in changed_names:
                continue
            if term and term not in name.lower():
                continue
            names.append(name)
        return names

    def _populate_locals(self, step: dict[str, Any]) -> None:
        locals_map = step.get("locals") if isinstance(step.get("locals"), dict) else {}
        diff_map = step.get("diff") if isinstance(step.get("diff"), dict) else {}
        changed_names = self._changed_names(diff_map)

        self._clear_table(self._locals_tree)
        for name in self._filtered_local_names(locals_map, changed_names):
            tags = ("changed_local",) if name in changed_names else ()
            self._locals_tree.insert("", "end", values=(name, locals_map[name]), tags=tags)

    def _populate_diff(self, step: dict[str, Any]) -> None:
        diff_map = step.get("diff") if isinstance(step.get("diff"), dict) else {}
        added = diff_map.get("added") if isinstance(diff_map.get("added"), dict) else {}
        removed = diff_map.get("removed") if isinstance(diff_map.get("removed"), dict) else {}
        changed = diff_map.get("changed") if isinstance(diff_map.get("changed"), dict) else {}

        self._clear_table(self._diff_tree)

        for name in sorted(added):
            self._diff_tree.insert(
                "",
                "end",
                values=("added", name, "", added[name]),
                tags=("added",),
            )
        for name in sorted(removed):
            self._diff_tree.insert(
                "",
                "end",
                values=("removed", name, removed[name], ""),
                tags=("removed",),
            )
        for name in sorted(changed):
            entry = changed[name]
            before = entry.get("before") if isinstance(entry, dict) else ""
            after = entry.get("after") if isinstance(entry, dict) else ""
            self._diff_tree.insert(
                "",
                "end",
                values=("changed", name, before, after),
                tags=("changed",),
            )

    def _changed_names(self, diff_map: dict[str, Any]) -> set[str]:
        names: set[str] = set()
        added = diff_map.get("added") if isinstance(diff_map.get("added"), dict) else {}
        removed = diff_map.get("removed") if isinstance(diff_map.get("removed"), dict) else {}
        changed = diff_map.get("changed") if isinstance(diff_map.get("changed"), dict) else {}
        names.update(added)
        names.update(removed)
        names.update(changed)
        return names

    def _format_step_row(self, step: dict[str, Any]) -> str:
        index = step.get("index", "?")
        funcname = step.get("funcname", "")
        filename = step.get("filename", "")
        lineno = step.get("lineno", "")

        filepart = os.path.basename(filename) if filename else ""
        if filepart:
            return f"{index:>4}  {funcname}  {filepart}:{lineno}"
        return f"{index:>4}  {funcname}"

    def _format_step_header(self, step: dict[str, Any], *, i: int) -> str:
        index = step.get("index", i)
        funcname = step.get("funcname", "")
        filename = step.get("filename", "")
        lineno = step.get("lineno", "")
        return f"Step {index}  {funcname}()  {filename}:{lineno}"
