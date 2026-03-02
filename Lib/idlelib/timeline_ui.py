"""Timeline panel UI for visualizing execution steps and local variables.

This module provides a standalone Tkinter panel (TimelinePanel) that displays
a list of execution steps captured by the timeline tracer, and shows local
variables for the currently selected step.

No external dependencies; uses only stdlib Tkinter.
Data format agnostic — designed to integrate with timeline_tracer.py later.
"""

from tkinter import Tk, Toplevel, Frame, Label, Listbox, Text, Scrollbar
from tkinter import END, BOTH, LEFT, RIGHT, VERTICAL, DISABLED, NORMAL, Y


class TimelinePanel:
    """Standalone Tkinter panel for timeline step visualization.
    
    Displays a list of execution steps and details (locals) for the selected step.
    
    Args:
        master: Optional parent Tkinter widget. If None, creates own Toplevel window.
        on_select: Optional callback fn(step_index, step_dict) fired on step selection.
    
    Public methods:
        set_steps(steps): Replace internal step list and reset selection.
        select_step(i): Select step at index i, update details, fire callback.
        clear(): Clear all steps and details (optional).
    """
    
    def __init__(self, master=None, on_select=None):
        """Initialize TimelinePanel.
        
        Args:
            master: Parent widget or None (creates Toplevel).
            on_select: Optional selection callback(index, step_dict).
        """
        # Set up root window
        if master is None:
            self.root = Toplevel()
            self.root.title("Timeline View")
            self.root.geometry("700x500")
        else:
            self.root = master
        
        # State
        self.steps = []
        self.current_index = -1
        self.on_select = on_select
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the panel layout: header + list + details."""
        # Top frame: step counter label
        self.top_frame = Frame(self.root)
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.step_label = Label(self.top_frame, text="Steps: 0 / 0", font=("TkDefaultFont", 10))
        self.step_label.pack(side=LEFT)
        
        # List frame: Listbox + Scrollbar
        self.list_frame = Frame(self.root)
        self.list_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        self.listbox = Listbox(
            self.list_frame,
            width=80,
            height=15,
            exportselection=0,
            background="white"
        )
        self.listbox.pack(side=LEFT, fill=BOTH, expand=True)
        
        self.vbar = Scrollbar(self.list_frame, orient=VERTICAL)
        self.vbar.pack(side=RIGHT, fill=Y)
        
        # Link scrollbar to listbox
        self.listbox.config(yscrollcommand=self.vbar.set)
        self.vbar.config(command=self.listbox.yview)
        
        # Bind listbox selection event
        self.listbox.bind("<<ListboxSelect>>", self._on_step_select)
        
        # Details frame: label + Text widget
        self.details_frame = Frame(self.root)
        self.details_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        self.details_label = Label(self.details_frame, text="Locals:", font=("TkDefaultFont", 10, "bold"))
        self.details_label.pack(side=LEFT, anchor="nw")
        
        # Text widget for details (readonly)
        self.details_text = Text(
            self.details_frame,
            width=80,
            height=10,
            background="white",
            state=DISABLED
        )
        self.details_text.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Configure grid weights for resizing
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
    
    def set_steps(self, steps):
        """Replace internal step list with new steps and reset selection.
        
        Args:
            steps: list[dict] where each dict has:
                - step (int): execution step number
                - filename (str): source file path
                - lineno (int): line number
                - funcname (str): function name
                - locals (dict[str, str] or None): variable name -> repr'd value
                - globals (dict[str, str] or None): reserved (not displayed week 1)
                - t_ns (int, optional): nanosecond timestamp
        """
        self.steps = steps if steps else []
        self.current_index = -1
        
        # Clear listbox
        self.listbox.delete(0, END)
        
        # Populate listbox with formatted step strings
        for idx, step in enumerate(self.steps):
            display_str = self._format_step_display(step)
            self.listbox.insert(END, display_str)
        
        # Update label
        self.step_label.config(text=f"Steps: 0 / {len(self.steps)}")
        
        # Clear details
        self._clear_details()
    
    def select_step(self, i):
        """Select step at index i and update details panel.
        
        Args:
            i: int, 0-indexed step number. Out-of-range calls are no-ops.
        """
        if not (0 <= i < len(self.steps)):
            return  # Silent no-op for out-of-range
        
        self.current_index = i
        
        # Update listbox selection
        self.listbox.selection_clear(0, END)
        self.listbox.selection_set(i)
        self.listbox.see(i)  # Autoscroll to visible
        
        # Update details panel
        self._update_details()
        
        # Fire callback if set
        if self.on_select:
            self.on_select(i, self.steps[i])
    
    def clear(self):
        """Clear all steps and reset details (optional utility)."""
        self.set_steps([])
    
    def _on_step_select(self, event):
        """Event handler for Listbox selection (<<ListboxSelect>>)."""
        sel = self.listbox.curselection()
        if sel:
            self.select_step(sel[0])
    
    def _update_details(self):
        """Update details panel with locals from current step."""
        if self.current_index < 0 or self.current_index >= len(self.steps):
            self._clear_details()
            return
        
        step = self.steps[self.current_index]
        
        # Update header label with step info
        step_num = step.get("step", self.current_index + 1)
        funcname = step.get("funcname", "(unknown)")
        filename = step.get("filename", "(unknown file)")
        lineno = step.get("lineno", "?")
        
        self.step_label.config(
            text=f"Step {step_num} / {len(self.steps)} | {funcname}() at {filename}:{lineno}"
        )
        
        # Extract and format locals
        locals_dict = step.get("locals")
        
        if locals_dict is None:
            details_text = "(no locals captured)"
        elif not isinstance(locals_dict, dict):
            details_text = "(locals not a dict)"
        elif not locals_dict:
            details_text = "(locals empty)"
        else:
            # Format as "key = value" per line
            lines = []
            for key in sorted(locals_dict.keys()):
                value = locals_dict[key]
                lines.append(f"{key} = {value}")
            details_text = "\n".join(lines)
        
        # Update Text widget (enable → clear → insert → disable)
        self.details_text.config(state=NORMAL)
        self.details_text.delete(1.0, END)
        self.details_text.insert(1.0, details_text)
        self.details_text.config(state=DISABLED)
    
    def _clear_details(self):
        """Clear details panel."""
        self.step_label.config(text=f"Steps: 0 / {len(self.steps)}")
        self.details_text.config(state=NORMAL)
        self.details_text.delete(1.0, END)
        self.details_text.config(state=DISABLED)
    
    def _format_step_display(self, step):
        """Format step dict into a display string for the listbox.
        
        Args:
            step: dict with step info
        
        Returns:
            str formatted as "Step X | funcname() at filename:lineno"
        """
        try:
            step_num = step.get("step", "?")
            funcname = step.get("funcname", "(unknown)")
            filename = step.get("filename", "(unknown file)")
            lineno = step.get("lineno", "?")
            return f"Step {step_num} | {funcname}() at {filename}:{lineno}"
        except Exception:
            return "Step ? | (malformed)"


def main():
    """Standalone demo: create window and show TimelinePanel."""
    root = Tk()
    root.withdraw()  # Hide root, use only Toplevel panel
    
    panel = TimelinePanel()
    
    # Mock steps (exact tracer dict format)
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
    
    # Set steps in panel
    panel.set_steps(mock_steps)
    
    # Optional: select first step
    panel.select_step(0)
    
    # Start mainloop
    root.mainloop()


if __name__ == "__main__":
    main()
