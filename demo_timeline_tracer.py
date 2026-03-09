"""Small standalone demo for idlelib.timeline_tracer.

Run from the repo root, for example:

    ./python demo_timeline_tracer.py

or with your system python (as long as it can import this repo's Lib/):

    PYTHONPATH=./Lib python3 demo_timeline_tracer.py
"""

from __future__ import annotations


def target(n: int) -> int:
    total = 0
    for i in range(n):
        total += i
    return total


def main() -> None:
    from idlelib import timeline_tracer

    timeline_tracer.clear()
    timeline_tracer.start(max_events=2000)
    try:
        target(5)
    finally:
        timeline_tracer.stop()

    events = timeline_tracer.get_events()
    print(f"Captured {len(events)} events (overflowed={timeline_tracer.overflowed()}).")
    for e in events[:10]:
        print(f"{e['step']:>4} {e['filename']}:{e['lineno']} {e['funcname']}()")
        if "locals" in e:
            print("     locals:", e["locals"])


if __name__ == "__main__":
    main()

