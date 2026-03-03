"""Timeline panel UI for visualizing execution steps and local variables.

This module is intentionally independent of IDLE integration. It provides a
pure-Tkinter panel (TimelinePanel) with two main areas:

- Left: a list of execution steps
- Right: locals snapshot and a diff summary for the selected step

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
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self._header = ttk.Label(right, text="No step selected", font=("TkDefaultFont", 10, "bold"))
        self._header.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._details = tk.Text(right, wrap="none", height=10)
        self._details.grid(row=1, column=0, sticky="nsew")
        self._details.configure(state="disabled")

        details_scroll = ttk.Scrollbar(right, orient="vertical", command=self._details.yview)
        details_scroll.grid(row=1, column=1, sticky="ns")
        self._details.configure(yscrollcommand=details_scroll.set)

    def set_steps(self, steps: list[dict[str, Any]]) -> None:
        """Accept UI-ready step dicts and populate the step list."""
        self._steps = list(steps or [])

        self._list.delete(0, tk.END)
        for step in self._steps:
            self._list.insert(tk.END, self._format_step_row(step))

        self._set_details(header="No step selected", body="")

    def select_step(self, i: int) -> None:
        """Select step at index i (0-based) and update details panel."""
        if not (0 <= i < len(self._steps)):
            return

        self._list.selection_clear(0, tk.END)
        self._list.selection_set(i)
        self._list.see(i)

        step = self._steps[i]
        header = self._format_step_header(step, i=i)
        body = self._format_step_details(step)
        self._set_details(header=header, body=body)

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

    def _set_details(self, *, header: str, body: str) -> None:
        self._header.configure(text=header)
        self._details.configure(state="normal")
        self._details.delete("1.0", tk.END)
        if body:
            self._details.insert("1.0", body)
        self._details.configure(state="disabled")

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

    def _format_step_details(self, step: dict[str, Any]) -> str:
        locals_map = step.get("locals") if isinstance(step.get("locals"), dict) else {}
        diff_map = step.get("diff") if isinstance(step.get("diff"), dict) else {}

        lines: list[str] = []

        lines.append("Locals")
        lines.append("-" * 60)
        if locals_map:
            for name in sorted(locals_map):
                lines.append(f"{name} = {locals_map[name]}")
        else:
            lines.append("(empty)")

        lines.append("")
        lines.append("Diff vs previous step")
        lines.append("-" * 60)
        lines.extend(self._format_diff(diff_map))

        return "\n".join(lines).rstrip() + "\n"

    def _format_diff(self, diff_map: dict[str, Any]) -> list[str]:
        added = diff_map.get("added") if isinstance(diff_map.get("added"), dict) else {}
        removed = diff_map.get("removed") if isinstance(diff_map.get("removed"), dict) else {}
        changed = diff_map.get("changed") if isinstance(diff_map.get("changed"), dict) else {}

        out: list[str] = []

        if not (added or removed or changed):
            return ["(no changes)"]

        if added:
            out.append("Added")
            for name in sorted(added):
                out.append(f"  + {name} = {added[name]}")
            out.append("")

        if removed:
            out.append("Removed")
            for name in sorted(removed):
                out.append(f"  - {name} = {removed[name]}")
            out.append("")

        if changed:
            out.append("Changed")
            for name in sorted(changed):
                entry = changed[name]
                before = entry.get("before") if isinstance(entry, dict) else None
                after = entry.get("after") if isinstance(entry, dict) else None
                out.append(f"  * {name}: {before}  ->  {after}")
            out.append("")

        # Trim trailing blank
        while out and out[-1] == "":
            out.pop()
        return out

