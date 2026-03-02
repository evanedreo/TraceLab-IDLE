#!/usr/bin/env python3
"""Standalone harness for timeline_ui panel demo.

This script demonstrates the TimelinePanel UI with mock execution steps.

Recommended: Run with the built Python in the repo (uses configured Tkinter):

  ./python demo_timeline_ui.py

Or with system python (requires PYTHONPATH):

  PYTHONPATH=./Lib python3 demo_timeline_ui.py

Or via one-liner from repo root:

  python3 -c "import sys; sys.path.insert(0,'./Lib'); import demo_timeline_ui; demo_timeline_ui.main()"
"""

from tkinter import Tk


def main():
    """Launch timeline UI panel with mock steps."""
    
    # Ensure Lib is in path for idlelib imports (deferred to here)
    import sys
    if './Lib' not in sys.path:
        sys.path.insert(0, './Lib')
    
    from idlelib.timeline_ui import TimelinePanel
    
    # Create hidden root window; panel uses Toplevel
    root = Tk()
    root.withdraw()
    
    # Create panel (uses on_select callback for demo)
    def on_select(idx, step):
        print(f"Selected step {idx}: {step['funcname']}() at {step['filename']}:{step['lineno']}")
    
    panel = TimelinePanel(on_select=on_select)
    
    # Mock execution steps (exact tracer dict format)
    mock_steps = [
        {
            "step": 1,
            "filename": "test.py",
            "lineno": 5,
            "funcname": "main",
            "locals": {"x": "0", "result": "None"},
            "globals": None,
            "t_ns": 1000000,
        },
        {
            "step": 2,
            "filename": "test.py",
            "lineno": 6,
            "funcname": "main",
            "locals": {"x": "1", "result": "None"},
            "globals": None,
            "t_ns": 2000000,
        },
        {
            "step": 3,
            "filename": "test.py",
            "lineno": 7,
            "funcname": "helper",
            "locals": {"a": "10", "b": "20"},
            "globals": None,
            "t_ns": 3000000,
        },
        {
            "step": 4,
            "filename": "test.py",
            "lineno": 8,
            "funcname": "helper",
            "locals": {"a": "10", "b": "20", "c": "30"},
            "globals": None,
            "t_ns": 4000000,
        },
        {
            "step": 5,
            "filename": "test.py",
            "lineno": 9,
            "funcname": "main",
            "locals": {"x": "1", "result": "30"},
            "globals": None,
            "t_ns": 5000000,
        },
        {
            "step": 6,
            "filename": "test.py",
            "lineno": 10,
            "funcname": "main",
            "locals": {"x": "2", "result": "30"},
            "globals": None,
            "t_ns": 6000000,
        },
        {
            "step": 7,
            "filename": "other.py",
            "lineno": 15,
            "funcname": "process",
            "locals": {"data": "[1, 2, 3]", "count": "3"},
            "globals": None,
            "t_ns": 7000000,
        },
        {
            "step": 8,
            "filename": "other.py",
            "lineno": 16,
            "funcname": "process",
            "locals": {"data": "[1, 2, 3]", "count": "3", "total": "6"},
            "globals": None,
            "t_ns": 8000000,
        },
        {
            "step": 9,
            "filename": "test.py",
            "lineno": 11,
            "funcname": "main",
            "locals": {"x": "2", "result": "30", "final": "'done'"},
            "globals": None,
            "t_ns": 9000000,
        },
        {
            "step": 10,
            "filename": "test.py",
            "lineno": 12,
            "funcname": "main",
            "locals": {},  # Empty locals
            "globals": None,
            "t_ns": 10000000,
        },
    ]
    
    # Populate panel with mock steps
    panel.set_steps(mock_steps)
    
    # Auto-select first step for demonstration
    panel.select_step(0)
    
    # Start Tkinter event loop
    root.mainloop()


if __name__ == "__main__":
    main()
