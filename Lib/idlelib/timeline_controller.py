"""Orchestrate timeline tracing within IDLE.

This controller glues together the RPC tracing hooks (in run.py's Executive),
the pipeline (timeline_pipeline.events_to_steps), and the UI panel
(timeline_ui.TimelinePanel).  It is owned by the PyShell instance and is
activated when the user toggles "Timeline" in the Debug menu.
"""

from __future__ import annotations

import os
from typing import Any

try:
    from idlelib.timeline_pipeline import events_to_steps
    from idlelib.timeline_ui import TimelinePanel
except Exception:
    from timeline_pipeline import events_to_steps  # type: ignore[no-redef]
    from timeline_ui import TimelinePanel  # type: ignore[no-redef]


_LIB_ROOT = os.path.normcase(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
) + os.sep


class TimelineController:
    """Manage timeline tracing, data fetching, and UI updates."""
    _INTERNAL_MARKERS = (
        os.sep + "lib" + os.sep + "python",
        "site-packages",
        os.sep + "idlelib" + os.sep,
        "importlib",
    )

    def __init__(self, pyshell) -> None:
        self.pyshell = pyshell
        self.panel: TimelinePanel | None = None
        self._tracing = False

    # -- RPC helper ----------------------------------------------------------

    def _rpc(self, method: str, *args, **kwargs) -> Any:
        """Call an Executive method in the subprocess via RPC."""
        rpcclt = self.pyshell.interp.rpcclt
        if rpcclt is not None:
            return rpcclt.remotecall("exec", method, args, kwargs)
        return None

    # -- Panel lifecycle -----------------------------------------------------

    def toggle_panel(self) -> None:
        """Show or hide the timeline window."""
        if self.panel is not None and self.panel.winfo_exists():
            self.close()
        else:
            self.open()

    def open(self) -> None:
        """Create and display the timeline panel."""
        if self.panel is not None and self.panel.winfo_exists():
            self.panel.master.lift()
            return
        self.panel = TimelinePanel(on_select=self._on_step_select)
        self.panel.master.protocol("WM_DELETE_WINDOW", self._on_panel_close)

    def close(self) -> None:
        """Destroy the timeline panel and stop any active tracing."""
        if self._tracing:
            try:
                self._rpc("stop_timeline_tracing")
            except Exception:
                pass
            self._tracing = False
        if self.panel is not None:
            try:
                toplevel = self.panel.master
                self.panel.destroy()
                toplevel.destroy()
            except Exception:
                pass
            self.panel = None

    @property
    def is_open(self) -> bool:
        return self.panel is not None and self.panel.winfo_exists()

    # -- Tracing lifecycle ---------------------------------------------------

    def on_run_start(self) -> None:
        """Called by PyShell.beginexecuting() when timeline is active."""
        if not self.is_open:
            return
        try:
            self._rpc("clear_timeline_events")
            self.panel.clear()
            self._rpc(
                "start_timeline_tracing",
                max_events=2000,
                capture_globals=False,
                trace_threads=False,
            )
            self._tracing = True
        except Exception:
            self._tracing = False

    def on_run_end(self) -> None:
        """Called by PyShell.endexecuting() when timeline is active."""
        if not self._tracing:
            return
        try:
            self._rpc("stop_timeline_tracing")
        except Exception:
            pass
        self._tracing = False
        self._refresh_panel()

    def refresh(self) -> None:
        """Manually re-fetch events and update the panel."""
        self._refresh_panel()

    # -- Internal helpers ----------------------------------------------------

    def _refresh_panel(self) -> None:
        """Fetch events from the subprocess, run pipeline, update UI."""
        if not self.is_open:
            return
        try:
            raw_events = self._rpc("get_timeline_events") or []
        except Exception:
            raw_events = []
        events = self._select_events_for_display(raw_events)
        if not events:
            return
        steps = events_to_steps(events)
        self.panel.set_steps(steps)
        if steps:
            self.panel.select_step(0)

    def _select_events_for_display(self, events):
        """Select user-code events, prioritizing the active script file."""
        target = self._get_target_filename()
        if target:
            wanted = os.path.normcase(os.path.abspath(target))
            matches = []
            for event in events:
                filename = event.get("filename")
                if not isinstance(filename, str) or not filename:
                    continue
                normed = os.path.normcase(os.path.abspath(filename))
                if normed == wanted:
                    matches.append(event)
            if matches:
                return matches
        return self._prefer_user_events(events)

    def _get_target_filename(self) -> str:
        try:
            filename = self._rpc("get_timeline_target_file") or ""
        except Exception:
            filename = ""
        return filename if isinstance(filename, str) else ""

    def _prefer_user_events(self, events):
        """Return only user-code events.

        The tracer currently observes all subprocess activity, including IDLE RPC
        internals. This filter keeps timeline output focused on user scripts by
        excluding events sourced from the repository's `Lib/` tree. If no
        user events are present in this batch, return an empty list so callers
        can skip replacing the UI with internal-only noise.
        """
        user_events = [e for e in events if self._is_user_event(e)]
        return user_events

    def _is_user_event(self, event) -> bool:
        filename = event.get("filename")
        if not isinstance(filename, str) or not filename:
            return False
        if filename.startswith("<"):
            return False
        normed = os.path.normcase(os.path.abspath(filename))
        if normed.startswith(_LIB_ROOT):
            return False
        lower = normed.lower()
        for marker in self._INTERNAL_MARKERS:
            if marker in lower:
                return False
        return True

    def _on_step_select(self, index: int, step: dict) -> None:
        """Callback invoked when the user clicks a step in the panel."""
        pass

    def _on_panel_close(self) -> None:
        """Handle the user closing the timeline window via the [X] button."""
        self.close()
        self.pyshell.setvar("<<toggle-timeline>>", False)
