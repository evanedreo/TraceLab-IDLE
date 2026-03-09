# TraceLab — Code Comprehension, Navigation, and Plan

## 1. Code Comprehension

### How IDLE Runs Your Code (High Level)

- The user runs code via **Run → Run Module** or by typing in the shell.
- **PyShell** (`pyshell.py`) is the main window; it uses **ModifiedInterpreter** for interactive execution.
- When you run a script, IDLE usually runs it in a **separate Python process** (a subprocess). The main IDLE window (menus, editor, shell) is one process; your script runs in another.
- The **Executive** (`run.py`) is the code in that subprocess that **receives commands from the IDLE window** (over a socket) and runs them—e.g. "run this code," "start the debugger," "get a call tip." So when we say "RPC handler" or "the handler," we mean: **the part of the subprocess that listens for those commands and executes them**. The Executive is what actually runs your code via `exec(code, self.locals)` in `runcode()`.

### How Tracing / Debugging Works

- IDLE's debugger is built on **bdb.Bdb** (in `Lib/bdb.py`). Bdb installs a trace by calling `sys.settrace(self.trace_dispatch)`.
- **Idb** (`debugger.py`) extends `bdb.Bdb` and implements `user_line()` and `user_exception()`. Each time execution hits a line (or an exception), the trace calls these; Idb then calls `gui.interaction(message, frame)` so the Debugger window can update.
- From a frame you can get: `frame.f_code.co_filename`, `frame.f_lineno`, `frame.f_locals`, `frame.f_globals`. That's enough to build a timeline of "where we are" and "what variables exist."

### Key Files and Their Roles

| File | Role |
|------|------|
| `Lib/idlelib/debugger.py` | **Idb** (extends bdb.Bdb) and **Debugger** GUI. Defines `user_line()`, `user_exception()`, `_frame2message()`. |
| `Lib/idlelib/debugger_r.py` | Remote debugger when IDLE uses a subprocess (proxies between GUI and subprocess Idb). |
| `Lib/idlelib/run.py` | **Executive** (runs in subprocess; runs user code, starts debugger). Defines `runcode()`, `start_the_debugger()`. Subprocess entry point. |
| `Lib/idlelib/pyshell.py` | **PyShell** window, `open_debugger()`, execution state. |
| `Lib/idlelib/editor.py` | **EditorWindow** base, menus, bindings. |
| `Lib/idlelib/runscript.py` | **ScriptBinding** — "Run Module," "Check Module"; `run_module_event()`, `check_module_event()`. |
| `Lib/idlelib/mainmenu.py` | **menudefs** — defines Run, Debug, etc. |
| `Lib/bdb.py` | Base debugger; `trace_dispatch`, `sys.settrace`. |

---

## 2. Code Navigation

### Where Things Live

```
Lib/
├── idlelib/
│   ├── debugger.py      # Idb + Debugger window
│   ├── debugger_r.py    # Remote debugger (subprocess)
│   ├── run.py           # Subprocess + Executive (run/debug handler)
│   ├── pyshell.py       # Main shell window
│   ├── editor.py        # Editor window base
│   ├── runscript.py     # Run Module, Check Module
│   ├── mainmenu.py      # Menu definitions
│   ├── stackviewer.py   # Stack browser (good UI reference)
│   ├── timeline.py      # [NEW] Snapshot storage, diffing, timeline model
│   ├── timeline_ui.py   # [NEW, optional] Timeline panel UI
│   ├── testrunner.py    # [NEW] unittest discovery, execution, output parsing
│   └── ...
└── bdb.py               # Base debugger (settrace)
```

### Where to Look For…

- **Tracing:** `bdb.Bdb.trace_dispatch`; `Idb.user_line` in `debugger.py`.
- **Variable inspection:** Debugger's locals/globals viewers in `debugger.py`; `stackviewer.py` VariablesTreeItem.
- **Where execution is triggered:** `run.py` `Executive.runcode()`.
- **Menus:** `mainmenu.py` `menudefs`; EditorWindow/PyShell `createmenubar()`.
- **Run Module:** `runscript.py` `ScriptBinding.run_module_event()`.

---

## 3. Where Code Changes Go

### New Files to Add (Proposition)

| File | Purpose |
|------|---------|
| **`Lib/idlelib/timeline.py`** | Timeline model: snapshot storage, diffing logic, step list. Captured data feeds the timeline panel. |
| **`Lib/idlelib/testrunner.py`** | Test discovery (unittest), subprocess execution, output streaming, pass/fail parsing, clickable traceback links. |
| **`Lib/idlelib/timeline_ui.py`** (optional) | Timeline panel UI: step list, variable inspector, prev/next controls. Can live in `timeline.py` instead if preferred. |

All new modules will live under **`Lib/idlelib/`** so IDLE can import them like the rest of idlelib.

### Existing Files to Modify

| File | Changes |
|------|---------|
| **`Lib/idlelib/mainmenu.py`** | Add menu items (e.g. TraceLab → Timeline, Run Tests). |
| **`Lib/idlelib/editor.py`** | Add keybindings and any editor hooks for Timeline / Test runner. |
| **`Lib/idlelib/pyshell.py`** | Wire in Timeline panel and Test runner; open panel, pass execution context. |
| **`Lib/idlelib/run.py`** | Optional: hook for "run with timeline" or feeding execution into the tracer. |
| **`Lib/idlelib/runscript.py`** | Optional: "Run with timeline" or "Run tests" entry points from Run menu. |
| **`Lib/idlelib/configdialog.py`** or config | Optional: preferences (e.g. max timeline steps). |

**Note:** `Lib/bdb.py` would only be modified if we extend the base debugger; otherwise we leave it unchanged.

---

## 4. Initial Plan and Approach

### Timeline Feature

**Tracing pipeline (dev/timeline-tracing)**  
- Add a tracer that records line events and variable snapshots.  
- Either extend Idb and record in `user_line()`, or install a separate `sys.settrace` callback (must coordinate with existing debugger so only one trace is active when needed).  
- Capture: filename, lineno, and a snapshot of `frame.f_locals` / `frame.f_globals` (or a safe subset).

**Storage and diffing (dev/timeline-storage-diff)**  
- New module `Lib/idlelib/timeline.py`: store snapshots in an ordered structure (e.g. list of step records).  
- Implement diffing between consecutive snapshots so we can show "what changed" between steps.  
- Cap total steps (or memory) for performance.

**UI panel (dev/timeline-ui-panel)**  
- New panel (Toplevel or pane) with: step list, variable inspector, prev/next step controls.  
- Hook into PyShell or EditorWindow; open via menu/shortcut.  
- Reuse patterns from `debugger.py` and `stackviewer.py`.

### Test Runner Feature

**feature/test-runner**  
- New module `Lib/idlelib/testrunner.py`.  
- Use `unittest.loader.TestLoader().discover()` or load from current file.  
- Run tests in a subprocess (same pattern as `run.py`), stream output, parse pass/fail and tracebacks.  
- Parse traceback lines to get file:line for clickable "go to line" in the editor.

### Integration

**feature/idle-integration**  
- Add menu items in `mainmenu.py` (e.g. TraceLab → Timeline, Run Tests).  
- Add keybindings in editor/pyshell.  
- Wire Timeline panel and Test Runner into Editor and PyShell.  
- Optional: basic preferences (e.g. max timeline steps) in existing config.

### UI Definition and Layout

- **Stack:** Same as IDLE — **Tkinter** (and `tkinter.ttk` where useful). No new UI framework.
- **Where it lives:**  
  - **Timeline:** A separate window (Toplevel) or a pane that can be shown/hidden (like the Debugger and Stack Viewer).  
  - **Test runner:** A dedicated output area (e.g. a text widget or second pane) for test output and clickable failure lines, similar to existing IDLE output windows.
- **How we define it:**  
  - No separate mockup phase; layout is defined by implementing against existing IDLE patterns (menus, bindings, window creation).  
  - **Reference UIs:** **Debugger** (`debugger.py`) for window layout and "current line" style UI; **Stack Viewer** (`stackviewer.py`) for a tree/list of items (steps or variables); **OutputWindow**-style flows for test output.
- **Timeline UI elements:**  
  1. **Step list** — List or tree of execution steps (step index, file:line, optional function name).  
  2. **Variable inspector** — List or tree of variable names and values for the selected step.  
  3. **Diff view (optional)** — Only show variables that changed from the previous step.  
  4. **Navigation** — Previous / Next step (and optionally "go to step N").
- **Test runner UI elements:**  
  1. **Run control** — "Run tests" for current file or current directory.  
  2. **Output area** — Streamed test log (pass/fail, tracebacks).  
  3. **Clickable tracebacks** — Same "go to file/line" mechanism as the rest of IDLE.
- **Placement:** Both features are exposed via **menus and shortcuts** (e.g. under Run/Debug or a "TraceLab" menu); exact names and shortcuts can be decided in the integration branch.

### Suggested Order of Work

1. Tracing pipeline + minimal snapshot capture.  
2. Storage + diffing, then timeline UI.  
3. Test runner, then integration (menus, shortcuts, preferences).
