#!/usr/bin/env python3
"""Standalone timeline demo: tracer -> pipeline -> UI.

This script demonstrates the full end-to-end flow outside of IDLE integration:

- Start tracing
- Run a small target function
- Stop tracing
- Convert tracer events to UI-ready steps (locals + diff)
- Launch the Tkinter timeline panel

Recommended: run with the repo's built Python (uses configured Tkinter):

  ./python demo_timeline_ui.py

Or with system python (requires PYTHONPATH):

  PYTHONPATH=./Lib python3 demo_timeline_ui.py

Or via one-liner from repo root:

  python3 -c "import sys; sys.path.insert(0,'./Lib'); import demo_timeline_ui; demo_timeline_ui.main()"
"""

from tkinter import Tk


def target() -> int:
    a = 1
    b = 2
    c = a + b
    b = 10
    return c + b


def main():
    """Launch timeline UI panel with traced steps."""

    # Avoid putting this repo's full `Lib/` on sys.path (it may not match the
    # running interpreter version). We only add `Lib/idlelib` so we can import
    # the timeline modules without shadowing unrelated stdlib modules.
    import sys
    idlelib_dir = "./Lib/idlelib"
    if idlelib_dir not in sys.path:
        sys.path.insert(0, idlelib_dir)

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
