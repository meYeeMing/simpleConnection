import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from core.utils import get_resource_path
from ui.styles import load_style_config


class AboutDialog(tk.Toplevel):
    def __init__(self, parent):
        width = 400
        height = 360
        super().__init__(parent)
        self.title("About Simply2Connection")
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)

        # Load style config
        style_cfg = load_style_config()
        colors = style_cfg["colors"]
        fonts = style_cfg["fonts"]

        self.configure(bg=colors["background"])
        self.transient(parent)
        self.grab_set()

        # Center the dialog on parent
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        self.geometry(f"+{x}+{y}")

        # Main frame
        frame = tk.Frame(self, bg=colors["background"], padx=10, pady=10)
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
            lbl_icon = tk.Label(frame, image=self.photo_img, bg=colors["background"])
            lbl_icon.pack(pady=(8, 8))

        # Title & Version Container
        title_frame = tk.Frame(frame, bg=colors["background"])
        title_frame.pack(pady=(0, 8))

        # Title Label
        lbl_title = tk.Label(
            title_frame,
            text="Simply2Connection",
            font=tuple(fonts["about_title"]),
            fg=colors["about_title_fg"],
            bg=colors["background"],
        )
        lbl_title.pack(side=tk.TOP, anchor=tk.W, padx=0, pady=0)

        # Version Label
        lbl_version = tk.Label(
            title_frame,
            text="Version 1.0.0",
            font=tuple(fonts["small"]),
            fg=colors["subheading_fg"],
            bg=colors["background"],
        )
        lbl_version.pack(side=tk.TOP, anchor=tk.W, padx=(2, 0), pady=0)

        # Author Row Container
        author_frame = tk.Frame(title_frame, bg=colors["background"])
        author_frame.pack(side=tk.TOP, anchor=tk.W, pady=(5, 0))

        lbl_author = tk.Label(
            author_frame,
            text="Author :",
            font=tuple(fonts["default"]),
            fg=colors["about_author_fg"],
            bg=colors["background"],
        )
        lbl_author.pack(side=tk.LEFT)

        lbl_owner = tk.Label(
            author_frame,
            text="Simple",
            font=tuple(fonts["default_bold"]),
            fg=colors["about_author_fg"],
            bg=colors["background"],
        )
        lbl_owner.pack(side=tk.LEFT, padx=(0, 10))

        divider = tk.Frame(
            frame, height=1, bg=colors["treeview_selected_bg"], width=330
        )
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
            font=tuple(fonts["small"]),
            wraplength=320,
            fg=colors["warning_fg"],
            bg=colors["background"],
            padx=5,
        )
        lbl_warning.pack(pady=(0, 5))
        # Close Button
        btn_close = ttk.Button(frame, text="Close", command=self.destroy, width=12)
        btn_close.pack()
