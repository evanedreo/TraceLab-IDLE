"""Minimal per-line execution tracer (no UI dependency).

This module provides a tiny tracing pipeline that can be consumed by the rest
of the system via an in-memory event list and/or a callback.

Events are captured from Python's tracing hooks (sys.settrace) and include:
- filename, line number, function name
- timestamp (perf_counter_ns) and monotonic step index
- shallow locals and globals snapshots (repr-limited)
"""

from __future__ import annotations

import reprlib
import sys
import threading
import time
from collections.abc import Callable, Mapping


Event = dict  # Intentionally simple + pickleable for future RPC use.


def _safe_repr(obj, *, _r: reprlib.Repr) -> str:
    try:
        return _r.repr(obj)
    except Exception as exc:
        return f"<unreprable {type(obj).__name__}: {exc!r}>"


def _snapshot_namespace(
    ns: Mapping,
    *,
    max_items: int,
    _r: reprlib.Repr,
) -> dict[str, str]:
    if not ns:
        return {}
    out: dict[str, str] = {}
    for i, (k, v) in enumerate(ns.items()):
        if i >= max_items:
            break
        try:
            key = str(k)
        except Exception:
            key = "<unstringable-key>"
        out[key] = _safe_repr(v, _r=_r)
    return out


class TimelineTracer:
    """Capture per-line events into an in-memory list and optional callback."""

    def __init__(
        self,
        *,
        callback: Callable[[Event], None] | None = None,
        max_events: int = 2000,
        on_overflow: str = "stop",  # "stop" or "drop"
        capture_locals: bool = True,
        capture_globals: bool = True,
        max_snapshot_items: int = 25,
        max_repr: int = 200,
        trace_threads: bool = False,
    ) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be > 0")
        if on_overflow not in {"stop", "drop"}:
            raise ValueError("on_overflow must be 'stop' or 'drop'")

        self._callback = callback
        self._max_events = int(max_events)
        self._on_overflow = on_overflow
        self._capture_locals = bool(capture_locals)
        self._capture_globals = bool(capture_globals)
        self._max_snapshot_items = int(max_snapshot_items)
        self._trace_threads = bool(trace_threads)

        r = reprlib.Repr()
        # Keep snapshots shallow and bounded.
        r.maxstring = max(10, max_repr)
        r.maxother = max(10, max_repr)
        r.maxbytes = max(10, max_repr)
        r.maxlist = 10
        r.maxtuple = 10
        r.maxset = 10
        r.maxdict = 10
        self._repr = r

        self._events: list[Event] = []
        self._lock = threading.Lock()
        self._step = 0
        self._running = False
        self._overflowed = False

        self._prev_sys_trace = None
        self._prev_threading_trace = None
        self._trace_func = None

    def is_running(self) -> bool:
        return self._running

    def overflowed(self) -> bool:
        return self._overflowed

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._step = 0
            self._overflowed = False

    def get_events(self) -> list[Event]:
        with self._lock:
            return list(self._events)

    def set_callback(self, callback: Callable[[Event], None] | None) -> None:
        self._callback = callback

    def start(self) -> None:
        if self._running:
            return

        self._prev_sys_trace = sys.gettrace()
        self._prev_threading_trace = threading.gettrace()

        trace = self._build_trace(self._prev_sys_trace)
        self._trace_func = trace
        sys.settrace(trace)
        if self._trace_threads:
            threading.settrace(trace)

        self._running = True

    def stop(self) -> None:
        if not self._running:
            return

        # Restore previous tracing state.
        sys.settrace(self._prev_sys_trace)
        if self._trace_threads:
            threading.settrace(self._prev_threading_trace)

        self._running = False
        self._trace_func = None

    def _build_trace(self, prev_trace):
        if prev_trace is None:
            return self._trace
        return _ChainedTrace(prev_trace, self._trace).trace

    def _record_line_event(self, frame) -> None:
        code = frame.f_code
        filename = code.co_filename
        if filename == __file__:
            return  # Avoid internal noise / self-tracing.

        with self._lock:
            if len(self._events) >= self._max_events:
                self._overflowed = True
                if self._on_overflow == "stop":
                    # Disable tracing ASAP to prevent runaway overhead.
                    # We intentionally restore the previous trace immediately.
                    self.stop()
                return

            self._step += 1
            event: Event = {
                "step": self._step,
                "t_ns": time.perf_counter_ns(),
                "filename": filename,
                "lineno": frame.f_lineno,
                "funcname": code.co_name,
            }

            if self._capture_locals:
                event["locals"] = _snapshot_namespace(
                    frame.f_locals,
                    max_items=self._max_snapshot_items,
                    _r=self._repr,
                )
            if self._capture_globals:
                event["globals"] = _snapshot_namespace(
                    frame.f_globals,
                    max_items=self._max_snapshot_items,
                    _r=self._repr,
                )

            self._events.append(event)

        cb = self._callback
        if cb is not None:
            try:
                cb(event)
            except Exception:
                # Tracing must not crash user code.
                pass

    def _trace(self, frame, event, arg):
        if event == "call":
            return self._trace
        if event == "line":
            self._record_line_event(frame)
            return self._trace
        return self._trace


class _ChainedTrace:
    """Chain two trace functions while respecting per-frame local traces."""

    def __init__(self, a, b):
        self._a = a
        self._b = b
        self._locals: dict[int, tuple[Callable | None, Callable | None]] = {}

    def trace(self, frame, event, arg):
        fid = id(frame)
        a_local, b_local = self._locals.get(fid, (self._a, self._b))

        next_a = a_local(frame, event, arg) if a_local else None
        next_b = b_local(frame, event, arg) if b_local else None
        self._locals[fid] = (next_a, next_b)

        if event == "return":
            self._locals.pop(fid, None)

        return self.trace if (next_a or next_b) else None


_default: TimelineTracer | None = None
_default_lock = threading.Lock()


def start(
    callback: Callable[[Event], None] | None = None,
    *,
    max_events: int = 2000,
    on_overflow: str = "stop",
    capture_locals: bool = True,
    capture_globals: bool = True,
    max_snapshot_items: int = 25,
    max_repr: int = 200,
    trace_threads: bool = False,
) -> TimelineTracer:
    """Start (or reuse) the default tracer instance."""
    global _default
    with _default_lock:
        if _default is None:
            _default = TimelineTracer(
                callback=callback,
                max_events=max_events,
                on_overflow=on_overflow,
                capture_locals=capture_locals,
                capture_globals=capture_globals,
                max_snapshot_items=max_snapshot_items,
                max_repr=max_repr,
                trace_threads=trace_threads,
            )
        else:
            _default.set_callback(callback)
        _default.start()
        return _default


def stop() -> None:
    """Stop the default tracer if running."""
    with _default_lock:
        if _default is not None:
            _default.stop()


def clear() -> None:
    with _default_lock:
        if _default is not None:
            _default.clear()


def get_events() -> list[Event]:
    with _default_lock:
        return [] if _default is None else _default.get_events()


def is_running() -> bool:
    with _default_lock:
        return False if _default is None else _default.is_running()


def overflowed() -> bool:
    with _default_lock:
        return False if _default is None else _default.overflowed()

