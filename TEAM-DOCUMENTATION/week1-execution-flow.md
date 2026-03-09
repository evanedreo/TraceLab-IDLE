# Week 1: Execution Flow and Tracing Hook Decision

## Goal
Understand where to attach tracing with minimal disruption, decide between direct `sys.settrace` and debugger-hook reuse, and document one primary plan for Issue 2.

## Scope Covered
- Read and sketch path from Run to user code execution in IDLE.
- Identify integration points in `debugger.py`, `pyshell.py`, `run.py`.
- Decide one recommended approach for tracing.
- List required event/snapshot data: line number, filename, frame-derived locals/globals.

## Execution Flow (Run -> Code Execution)
### Run Module path
1. `EditorWindow.__init__` binds `<<run-module>>` to `ScriptBinding.run_module_event` in [editor.py](../Lib/idlelib/editor.py#L291).
2. `ScriptBinding.run_module_event` validates and compiles, then calls interpreter `runcode` in [runscript.py](../Lib/idlelib/runscript.py#L112).
3. `ModifiedInterpreter.runcode` sends async RPC call `exec.runcode` in subprocess mode in [pyshell.py](../Lib/idlelib/pyshell.py#L762).
4. Subprocess `run.main` dispatches RPC requests to `Executive` methods in [run.py](../Lib/idlelib/run.py#L117).
5. `Executive.runcode` executes user code via `exec(code, self.locals)` in [run.py](../Lib/idlelib/run.py#L584).
6. `ModifiedInterpreter.poll_subprocess` receives completion and ends execution state in [pyshell.py](../Lib/idlelib/pyshell.py#L577).

### Shell interactive path
1. `PyShell.runit` calls `self.interp.runsource(...)` in [pyshell.py](../Lib/idlelib/pyshell.py#L1352).
2. `ModifiedInterpreter.runsource` follows same `runcode` path in [pyshell.py](../Lib/idlelib/pyshell.py#L680).

## Candidate Hook Points (Exact Functions/Classes)
- `Lib/idlelib/run.py`
  - `Executive.runcode` in [run.py](../Lib/idlelib/run.py#L584)
  - `Executive.start_timeline_tracing` and related RPC helpers in [run.py](../Lib/idlelib/run.py#L631)
- `Lib/idlelib/debugger.py`
  - `Idb.user_line` and `Idb.user_exception` in [debugger.py](../Lib/idlelib/debugger.py#L36)
  - `Debugger.interaction` in [debugger.py](../Lib/idlelib/debugger.py#L252)
- `Lib/idlelib/pyshell.py`
  - `ModifiedInterpreter.runcode` in [pyshell.py](../Lib/idlelib/pyshell.py#L762)
  - `ModifiedInterpreter.poll_subprocess` in [pyshell.py](../Lib/idlelib/pyshell.py#L577)

## Recommended Approach (Primary Plan)
Use a standalone tracer based on `sys.settrace`, independent of debugger UI, with minimal integration in subprocess execution path.

Chosen patch targets for Issue 2:
1. New tracer module (`Lib/idlelib/timeline_tracer.py`) for start/stop/clear/get-events and capped in-memory storage.
2. Minimal integration stub in `Lib/idlelib/run.py` (`Executive` tracing control methods).

Rationale:
- Minimal disruption to current Run flow.
- No debugger/UI dependency.
- Captures frames in the same process where user code runs.

## Alternatives and Tradeoffs
### A) Reuse debugger hooks (`Idb.user_line` / `Idb.user_exception`)
Pros:
- Uses existing Bdb-based tracing flow.
- Frame access already proven.

Cons:
- Naturally tied to debugger mode.
- Higher coupling to debugger interaction semantics.
- Greater risk of behavior conflicts.

### B) Direct standalone `sys.settrace` tracer (recommended)
Pros:
- Works independently from debugger/UI.
- Fits Issue 2 requirements directly.
- Easier isolated testing and capped storage control.

Cons:
- Must coexist with other trace functions.
- Needs strict caps and bounded repr for performance.

### C) Hybrid (debugger hooks when debugging, standalone otherwise)
Pros:
- Potentially reduces duplicate tracing in debug sessions.

Cons:
- Two behaviors to maintain and test.
- Higher complexity for Week 1 scope.

## Required Event and Snapshot Data
- Core event fields:
  - `filename`
  - `lineno`
  - `funcname`
  - `step` or timestamp (`t_ns`)
- Snapshot fields (shallow):
  - `locals` (from `frame.f_locals`)
  - `globals` (from `frame.f_globals`)
- Runtime state:
  - `running`
  - `overflowed`
  - `event_count`
- Safety controls:
  - `max_events` cap (for example 2000)
  - overflow behavior (`stop` or `drop`)
  - snapshot/repr limits
