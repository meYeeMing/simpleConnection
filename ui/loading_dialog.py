import tkinter as tk
from tkinter import ttk

class LoadingDialog(tk.Toplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x150")
        self.resizable(False, False)
        self.configure(bg="#f8f9fa")
        self.transient(parent)
        self.grab_set()

        # Center the dialog on parent
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 350) // 2
        y = parent_y + (parent_h - 150) // 2
        self.geometry(f"+{x}+{y}")

        # Disable close button
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        # Frame
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Message
        self.lbl_msg = ttk.Label(
            frame,
            text=message,
            font=("Segoe UI", 10),
            wraplength=310,
            justify=tk.CENTER,
        )
        self.lbl_msg.pack(pady=(10, 15))

        # Progress bar
        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=280)
        self.progress.pack()
        self.progress.start(10)
