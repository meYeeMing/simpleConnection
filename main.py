from core.utils import elevate_privileges

elevate_privileges()

# Main application imports
import tkinter as tk
from ui.app import App

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
