"""Test that prints the data passed at each step of the timeline feature.

Run with the project's Python (e.g. from repo root):
  ./build-macos/python.exe -m idlelib.idle_test.test_timeline_flow_verbose -v

This test runs a minimal timeline flow (tracer -> filter -> pipeline)
and prints the actual structures at each stage so you can see what is passed
around when the user uses the timeline feature.
"""

from __future__ import annotations

import os
import sys
import unittest
from pprint import pprint

# Ensure we can import idlelib when run as __main__ or from different cwds.
if __name__ == "__main__":
    _lib = os.path.join(os.path.dirname(__file__), "..", "..")
    _lib = os.path.abspath(_lib)
    if _lib not in sys.path:
        sys.path.insert(0, _lib)

try:
    from idlelib.timeline_tracer import TimelineTracer
    from idlelib.timeline_pipeline import events_to_steps
except Exception:
    from timeline_tracer import TimelineTracer
    from timeline_pipeline import events_to_steps

# Optional: use controller's filter if available (needs tkinter).
def _filter_user_events(events, script_path: str):
    """Keep events for the given script path (simulates controller selection)."""
    want = os.path.normcase(os.path.abspath(script_path))
    out = []
    for e in events:
        fn = e.get("filename")
        if isinstance(fn, str) and fn and os.path.normcase(os.path.abspath(fn)) == want:
            out.append(e)
    return out if out else events


# Small script that produces a few trace events with changing locals.
# Filename is set to "demo_script.py" so controller treats it as user code.
_DEMO_SCRIPT = """
x = 1
y = 2
z = x + y
def f():
    a = 10
    b = 20
    return a + b
result = f()
"""


class _DummyInterp:
    rpcclt = None


class _DummyPyShell:
    interp = _DummyInterp()


class TimelineFlowVerboseTest(unittest.TestCase):
    """Run timeline flow and print data at each step (for inspection)."""

    def test_timeline_flow_prints_data_at_each_step(self) -> None:
        # Use a real path so controller filter keeps these events
        script_path = os.path.abspath("demo_script.py")

        tracer = TimelineTracer(max_events=500)
        tracer.start()
        try:
            exec(compile(_DEMO_SCRIPT, script_path, "exec"), {})
        finally:
            tracer.stop()

        raw_events = tracer.get_events()
        self.assertGreater(len(raw_events), 0, "tracer should capture events")

        # --- Step 1: Raw events from tracer ---
        print("\n" + "=" * 60)
        print("STEP 1: Raw events from tracer (get_events())")
        print("=" * 60)
        print(f"Count: {len(raw_events)}")
        print("\nFirst event (full):")
        pprint(raw_events[0])
        if len(raw_events) > 1:
            print("\nLast event (full):")
            pprint(raw_events[-1])
        print()

        # --- Step 2: After controller event selection ---
        # (In real IDLE, controller uses _prefer_user_events or target file from RPC.)
        filtered_events = _filter_user_events(raw_events, script_path)
        print("=" * 60)
        print("STEP 2: After controller filter (_prefer_user_events)")
        print("=" * 60)
        print(f"Count: {len(filtered_events)}")
        if filtered_events:
            print("\nFirst filtered event (full):")
            pprint(filtered_events[0])
        print()

        # --- Step 3: Steps from pipeline (what UI receives) ---
        events_for_steps = filtered_events if filtered_events else raw_events
        steps = events_to_steps(events_for_steps)
        self.assertGreater(len(steps), 0, "pipeline should produce at least one step")

        print("=" * 60)
        print("STEP 3: Steps from pipeline (events_to_steps) → same as set_steps(…) in UI")
        print("=" * 60)
        print(f"Count: {len(steps)}")
        print("\nFirst step (full):")
        pprint(steps[0])
        if len(steps) > 1:
            print("\nSecond step (full):")
            pprint(steps[1])
        print("=" * 60 + "\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
