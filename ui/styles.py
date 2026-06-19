import os
import json
import tkinter as tk

def load_style_config():
    """
    Loads styling parameters from style_config.json.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "style_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def configure_styles(root: tk.Tk, style_obj):
    """
    Sets background colors and styles for standard/ttk widgets.
    """
    config = load_style_config()
    colors = config["colors"]
    fonts = config["fonts"]
    
    # Root Window Styling
    root.configure(bg=colors["background"])
    
    # Base TTK styles
    style_obj.configure(".", background=colors["background"], foreground=colors["foreground"])
    style_obj.configure("TFrame", background=colors["background"])
    
    # Entry Widget Styling (turns disabled entry backgrounds to grey)
    style_obj.map(
        "TEntry",
        fieldbackground=[("disabled", "#e9ecef")],
        foreground=[("disabled", "#868e96")]
    )
    
    # Sidebar Styling
    style_obj.configure("Sidebar.TFrame", background=colors["sidebar_bg"])
    style_obj.configure(
        "Sidebar.TButton",
        background=colors["sidebar_btn_bg"],
        foreground=colors["sidebar_btn_fg"],
        font=tuple(fonts["default"]),
        borderwidth=1,
        focuscolor="none",
    )
    style_obj.map(
        "Sidebar.TButton",
        background=[("active", colors["sidebar_btn_active_bg"]), ("pressed", colors["sidebar_btn_pressed_bg"])],
        foreground=[("active", colors["sidebar_btn_active_fg"])],
    )

    # Heading Styling
    style_obj.configure(
        "Heading.TLabel",
        font=tuple(fonts["heading"]),
        foreground=colors["heading_fg"],
        background=colors["background"],
    )

    style_obj.configure(
        "Subheading.TLabel",
        font=tuple(fonts["subheading"]),
        foreground=colors["subheading_fg"],
        background=colors["background"],
    )

    # Standard Label & Button Styling
    style_obj.configure(
        "TLabel", 
        background=colors["background"], 
        foreground=colors["foreground"], 
        font=tuple(fonts["default"])
    )
    style_obj.configure(
        "Action.TButton",
        background=colors["primary"],
        foreground=colors["primary_fg"],
        font=tuple(fonts["default_bold"]),
        borderwidth=0,
    )
    style_obj.map(
        "Action.TButton", 
        background=[("active", colors["active_green"]), ("pressed", colors["pressed_green"])]
    )

    # Treeview (Tables)
    style_obj.configure(
        "Treeview",
        background=colors["treeview_bg"],
        fieldbackground=colors["treeview_fieldbg"],
        foreground=colors["foreground"],
        font=tuple(fonts["small"]),
    )
    style_obj.configure(
        "Treeview.Heading",
        background=colors["sidebar_bg"],
        foreground=colors["primary"],
        font=tuple(fonts["small_bold"]),
    )
    style_obj.map(
        "Treeview",
        background=[("selected", colors["treeview_selected_bg"])],
        foreground=[("selected", colors["foreground"])],
    )
