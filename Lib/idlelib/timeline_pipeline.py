"""Convert raw tracer events into UI-ready timeline steps.

This module is UI-agnostic. It consumes event dicts from
`idlelib.timeline_tracer.get_events()` (or compatible producers) and produces a
list of plain, pickleable step dictionaries suitable for display.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

try:
    # When imported as part of the `idlelib` package.
    from .timeline_store import TimelineStore, diff  # type: ignore
except Exception:
    try:
        # When imported via a `Lib` root on sys.path.
        from idlelib.timeline_store import TimelineStore, diff
    except Exception:
        # When running standalone with only `Lib/idlelib` on sys.path.
        from timeline_store import TimelineStore, diff  # type: ignore


_NOISY_KEYS = {"__builtins__"}


def _safe_repr(value: Any) -> str:
    try:
        return repr(value)
    except Exception as exc:
        return f"<unreprable {type(value).__name__}: {exc!r}>"


def _sanitize_locals_snapshot(snapshot: Any) -> dict[str, str]:
    """Return a filtered, string-valued locals snapshot."""
    if not isinstance(snapshot, Mapping):
        return {}

    out: dict[str, str] = {}
    for k, v in snapshot.items():
        try:
            name = str(k)
        except Exception:
            name = "<unstringable-key>"

        if name in _NOISY_KEYS:
            continue

        if isinstance(v, str):
            out[name] = v
        else:
            out[name] = _safe_repr(v)

    return out


def events_to_steps(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Convert tracer events to UI-ready step dictionaries.

    Output schema (each step is plain dict / pickleable):
        {
            "index": int,  # 0-based
            "filename": str,
            "lineno": int,
            "funcname": str,
            "locals": dict[str, str],
            "diff": {
                "added": dict[str, str],
                "removed": dict[str, str],
                "changed": dict[str, {"before": str, "after": str}],
            },
        }
    """
    store = TimelineStore(namespace="locals")

    for e in events:
        event = dict(e)
        event["locals"] = _sanitize_locals_snapshot(event.get("locals"))
        store.store_event(event)

    out_steps: list[dict[str, Any]] = []
    prev_locals: dict[str, str] = {}

    for i, event in enumerate(store.get_events()):
        curr_locals = _sanitize_locals_snapshot(event.get("locals"))

        try:
            lineno = int(event.get("lineno") or 0)
        except Exception:
            lineno = 0

        step = {
            "index": i,
            "filename": str(event.get("filename") or ""),
            "lineno": lineno,
            "funcname": str(event.get("funcname") or ""),
            "locals": curr_locals,
            "diff": diff(prev_locals, curr_locals),
        }
        out_steps.append(step)
        prev_locals = curr_locals

    return out_steps

