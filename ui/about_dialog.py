import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from core.utils import get_resource_path


class AboutDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About Simply2Connection")
        self.geometry("400x350")
        self.resizable(False, False)
        self.configure(bg="#f8f9fa")
        self.transient(parent)
        self.grab_set()

        # Center the dialog on parent
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 380) // 2
        y = parent_y + (parent_h - 350) // 2
        self.geometry(f"+{x}+{y}")

        # Main frame
        frame = tk.Frame(self, bg="#f8f9fa", padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Load and resize icon
        icon_path = get_resource_path("ui/statics/simpleconnection.png")
        self.photo_img = None
        try:
            img = Image.open(icon_path)
            img = img.resize((96, 96), Image.Resampling.LANCZOS)
            self.photo_img = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error loading about dialog icon: {e}")

        # Icon Label
        if self.photo_img:
            lbl_icon = tk.Label(frame, image=self.photo_img, bg="#f8f9fa")
            lbl_icon.pack(pady=(8, 8))

        # Title & Version Container
        title_frame = tk.Frame(frame, bg="#f8f9fa")
        title_frame.pack(pady=(0, 8))

        # Title Label
        lbl_title = tk.Label(
            title_frame,
            text="Simply2Connection",
            font=("Copperplate Gothic Bold", 18, "bold"),
            fg="#cc9941",
            bg="#f8f9fa",
        )
        lbl_title.pack(side=tk.TOP, anchor=tk.W, padx=0, pady=0)

        # Version Label
        lbl_version = tk.Label(
            title_frame,
            text="Version 1.0.0",
            font=("Segoe UI", 8),
            fg="#6c757d",
            bg="#f8f9fa",
        )
        lbl_version.pack(side=tk.TOP, anchor=tk.W, padx=(2, 0), pady=0)

        # Author Row Container
        author_frame = tk.Frame(title_frame, bg="#f8f9fa")
        author_frame.pack(side=tk.TOP, anchor=tk.W, pady=(5, 0))

        lbl_author = tk.Label(
            author_frame,
            text="Author :",
            font=("Segoe UI", 10),
            fg="#0f4c81",
            bg="#f8f9fa",
        )
        lbl_author.pack(side=tk.LEFT)

        lbl_owner = tk.Label(
            author_frame,
            text="Simple",
            font=("Segoe UI", 10, "bold"),
            fg="#0f4c81",
            bg="#f8f9fa",
        )
        lbl_owner.pack(side=tk.LEFT, padx=(0, 10))

        divider = tk.Frame(frame, height=1, bg="#dee2e6", width=330)
        divider.pack(pady=(0, 5))
        try:
            warning_img = Image.open(get_resource_path("ui/statics/warning.png"))
            warning_img = warning_img.resize((20, 20), Image.Resampling.LANCZOS)
            self.warning_icon = ImageTk.PhotoImage(warning_img)
        except Exception as e:
            print(f"Error loading warning icon: {e}")
            self.warning_icon = None

        lbl_warning = tk.Label(
            frame,
            image=self.warning_icon,
            compound=tk.TOP,
            text="The Tools has been granted privileges to modify the system network connection and route table. \n Changing may lead to connectively issues or unexpcted network behaviour",
            font=("Segoe UI", 8),
            wraplength=320,
            fg="#d00f0f",
            bg="#f8f9fa",
            padx=10,
        )
        lbl_warning.pack(pady=(0, 5))
        # Close Button
        btn_close = ttk.Button(frame, text="Close", command=self.destroy, width=12)
        btn_close.pack()
