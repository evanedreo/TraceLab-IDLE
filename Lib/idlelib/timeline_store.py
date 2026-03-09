"""Timeline store and diff helpers for TraceLab.

This module is intentionally UI-agnostic and consumes plain event dictionaries
from idlelib.timeline_tracer (or compatible producers).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


DiffResult = dict[str, dict[str, Any]]


def _safe_repr(value: Any) -> str:
    try:
        return repr(value)
    except Exception as exc:
        return f"<unreprable {type(value).__name__}: {exc!r}>"


def _values_equal(left: Any, right: Any) -> bool:
    """Compare two values without allowing unusual __eq__ to crash diffing."""
    try:
        return left == right
    except Exception:
        return _safe_repr(left) == _safe_repr(right)


def _snapshot_from_event(event: Mapping[str, Any], *, namespace: str) -> dict[str, Any]:
    raw = event.get(namespace, {})
    if isinstance(raw, Mapping):
        return dict(raw)
    return {}


def diff(prev: Mapping[str, Any] | None, curr: Mapping[str, Any] | None) -> DiffResult:
    """Compute added/removed/changed keys between two snapshots.

    Returns:
        {
            "added": {name: value},
            "removed": {name: value},
            "changed": {name: {"before": old, "after": new}},
        }
    """
    prev_map = dict(prev or {})
    curr_map = dict(curr or {})

    prev_keys = set(prev_map)
    curr_keys = set(curr_map)

    added = {name: curr_map[name] for name in curr_keys - prev_keys}
    removed = {name: prev_map[name] for name in prev_keys - curr_keys}

    changed: dict[str, Any] = {}
    for name in prev_keys & curr_keys:
        before = prev_map[name]
        after = curr_map[name]
        if not _values_equal(before, after):
            changed[name] = {"before": before, "after": after}

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
    }


class TimelineStore:
    """Store timeline events and provide step retrieval + diff access."""

    def __init__(self, *, namespace: str = "locals") -> None:
        self._events: list[dict[str, Any]] = []
        self._namespace = namespace

    def clear(self) -> None:
        self._events.clear()

    def store_event(self, event: Mapping[str, Any]) -> None:
        self._events.append(dict(event))

    def get_step(self, i: int) -> dict[str, Any]:
        # Uses list indexing semantics; raises IndexError when out of range.
        return self._events[i]

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def diff_steps(self, i: int, j: int) -> DiffResult:
        prev_event = self.get_step(i)
        curr_event = self.get_step(j)
        prev_snapshot = _snapshot_from_event(prev_event, namespace=self._namespace)
        curr_snapshot = _snapshot_from_event(curr_event, namespace=self._namespace)
        return diff(prev_snapshot, curr_snapshot)

