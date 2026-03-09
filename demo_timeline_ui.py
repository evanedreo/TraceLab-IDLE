#!/usr/bin/env python3
"""Standalone timeline demo: tracer -> pipeline -> UI.

This script demonstrates the full end-to-end flow outside of IDLE integration:

- Start tracing
- Run a small target function
- Stop tracing
- Convert tracer events to UI-ready steps (locals + diff)
- Launch the Tkinter timeline panel

Run from the repo root with a Python that has Tkinter support:

  python3.11 demo_timeline_ui.py
  python3.10 demo_timeline_ui.py

If the default python3 has tkinter, you can also use:

  python3 demo_timeline_ui.py
"""

import os
import sys

# Ensure idlelib modules are importable when running from the repo root.
_idlelib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Lib", "idlelib")
if _idlelib_dir not in sys.path:
    sys.path.insert(0, _idlelib_dir)

try:
    from tkinter import Tk
except ImportError:
    _hint = (
        "Tkinter is not available in this Python ({}).\n"
        "Try running with a Python that includes Tkinter, e.g.:\n"
        "  python3.11 demo_timeline_ui.py\n"
        "  python3.10 demo_timeline_ui.py"
    ).format(sys.executable)
    print(_hint, file=sys.stderr)
    raise SystemExit(1)


def target() -> int:
    a = 1
    b = 2
    c = a + b
    b = 10
    return c + b


def main():
    """Launch timeline UI panel with traced steps."""

    import timeline_tracer
    from timeline_pipeline import events_to_steps
    from timeline_ui import TimelinePanel

    timeline_tracer.clear()
    timeline_tracer.start(max_events=2000, capture_globals=False)
    try:
        target()
    finally:
        timeline_tracer.stop()

    events = timeline_tracer.get_events()
    steps = events_to_steps(events)
    print(f"Captured {len(events)} events -> {len(steps)} steps.")

    # Create hidden root window; panel uses a Toplevel.
    root = Tk()
    root.withdraw()

    def on_select(idx, step) -> None:
        print(
            f"Selected step {idx}: {step.get('funcname')}() "
            f"at {step.get('filename')}:{step.get('lineno')}"
        )

    panel = TimelinePanel(on_select=on_select)

    panel.set_steps(steps)
    if steps:
        panel.select_step(0)

    # Start Tkinter event loop
    root.mainloop()


if __name__ == "__main__":
    main()
