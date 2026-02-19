# TraceLab

## Visual Timeline + Test Runner for IDLE

TraceLab is a proposed enhancement to Python’s built in IDLE environment that aims to improve how beginners understand program execution and testing.

---

## Project Overview

TraceLab introduces two major features into IDLE:

1. Visual Variable Timeline
   Records how variables change over time during execution.

2. Live Output + Unit Runner
   Allows students to run unittest tests directly inside IDLE and navigate to failures.

The goal is to help novice programmers:

* Understand how program state evolves
* Debug more effectively
* Develop good testing habits early

---

## Motivation

Many beginners struggle with:

* Understanding what happens between lines of code
* Tracking how variables change
* Connecting failing tests to specific lines

TraceLab aims to make execution visible and testing immediate, directly within the learning environment students already use.

---

## Proposed Features

### Visual Variable Timeline

* Capture per line execution events
* Store variable snapshots
* Show step by step execution history
* Display variable diffs between steps
* Navigate forward and backward through execution
* Performance controls such as snapshot caps

### Live Output + Unit Runner

* Discover unittest tests in current file or project folder
* Run tests in a subprocess
* Stream output to a dedicated panel
* Provide clickable failure traces linked to editor lines

---

## Proposed Architecture

### Likely Integration Points in IDLE

* `debugger.py`
  Integrate tracing and stepping hooks

* `pyshell.py` and `run.py`
  Manage execution, output, and subprocess testing

* `editor.py`
  Add menu items, shortcuts, and UI integration

### Planned New Modules

* `timeline.py`
  Snapshot storage, diffing logic, and timeline model

* `testrunner.py`
  Test discovery, execution, and output parsing

---

## Development Plan

### Week 1, Foundations

* Study IDLE execution flow and debugger hooks
* Implement basic tracing pipeline
* Capture variable snapshots
* Prototype minimal timeline panel

### Week 2, Timeline Feature

* Variable inspector view
* Diff view for changed variables
* Step navigation controls
* Performance safeguards

### Week 3, Test Runner

* unittest discovery for current file
* Subprocess execution
* Live output streaming
* Clickable failure navigation

### Week 4, Integration and Polish

* Menu and shortcut integration
* Preferences panel
* Handle edge cases
* Documentation and demo scenario

---

## Checkpoint Deliverables

### Checkpoint

* Tracing pipeline capturing line events
* Timeline panel listing steps and variables
* Basic unittest runner
* Menu items wired into IDLE

### Final

* Polished UI with navigation and filtering
* Improved test discovery for project folders
* Preferences and shortcuts
* Documentation and evaluation demo

---

## Feasibility Considerations

* Execution tracing will use sys.settrace or existing debugger hooks
* Snapshot storage will be capped for performance
* Test runner will initially rely on Python’s built in unittest
* UI will use Tkinter components already present in IDLE

Scope is intentionally bounded to ensure the project remains realistic within the development timeline.

---

## Intended Audience

* Beginner Python students
* Instructors teaching programming fundamentals
* Learners using IDLE as their primary development environment

---
