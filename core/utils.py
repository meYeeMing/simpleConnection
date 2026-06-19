import sys
import os

def is_admin() -> bool:
    """
    Checks if the current process runs with administrator privileges (cross-platform).
    """
    if sys.platform == "win32":
        import ctypes
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False
    else:
        try:
            return os.getuid() == 0
        except AttributeError:
            return False

def elevate_privileges():
    """
    Checks if running as administrator. If not, requests elevation and restarts the process.
    Only has effect on Windows — silently returns on other platforms.
    """
    if is_admin():
        return
    if sys.platform != "win32":
        return  # Cannot auto-elevate on non-Windows
    try:
        import ctypes
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join([f'"{arg}"' for arg in sys.argv]),
            current_dir,
            1,
        )
        sys.exit(0)
    except Exception as e:
        print(f"Error requesting administrator privileges: {e}")
        sys.exit(1)
