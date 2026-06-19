import os
import shutil
import subprocess
import sys
import time

WORKPATH = "./build_pyinstaller"
SPECPATH = WORKPATH + "/spec"
DISTPATH = "./dist_win"


def build_app():
    print("Starting PyInstaller build...")
    start_time = time.perf_counter()
    # Clean previous builds
    for path in [WORKPATH, SPECPATH, DISTPATH]:
        if os.path.exists(path):
            print(f"Cleaning existing {path} directory...")
            try:
                shutil.rmtree(path)
            except PermissionError:
                print(
                    f"\n[ERROR] Permission denied while trying to clean directory: {path}"
                )
                print(
                    "This usually means RouteConfigurator.exe or SimpleConnection.exe is still running."
                )
                print(
                    "Please close the application window or end the tasks in Task Manager, then try again.\n"
                )
                sys.exit(1)

    for spec_name in ["RouteConfigurator.spec", "SimpleConnection.spec"]:
        spec_path = (
            os.path.join(SPECPATH, spec_name) if os.path.exists(SPECPATH) else spec_name
        )
        if os.path.exists(spec_path):
            try:
                os.remove(spec_path)
            except Exception:
                pass

    config_abs_path = os.path.abspath("config.yaml")
    ui_abs_path = os.path.abspath("ui")
    doc_abs_path = os.path.abspath("README.md")
    icon_abs_path = os.path.abspath("ui/statics/simpleconnection.ico")

    # We include --uac-admin to automatically request administrator access on launch
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--workpath=" + WORKPATH,
        "--specpath=" + SPECPATH,
        "--distpath=" + DISTPATH,
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--uac-admin",
        "--name=Simply2Connection",
        f"--icon={icon_abs_path}",
        f"--add-data={config_abs_path};.",
        f"--add-data={ui_abs_path};ui",
        f"--add-data={doc_abs_path};.",
        "main.py",
        # --- SIZE REDUCTION FLAGS ---
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=PyQt5",
        "--exclude-module=PySide2",
        "--exclude-module=PySide6",
        "--exclude-module=IPython",
        "--exclude-module=notebook",
        "--exclude-module=jupyter",
        "--exclude-module=pytest",
        "--exclude-module=jinja2",
        "--exclude-module=pysqlite2",
        "--exclude-module=MySQLdb",
        "--exclude-module=pymysql",
        "--exclude-module=psycopg2",
        "--exclude-module=pyodbc",
        "--exclude-module=sqlalchemy.ext.asyncio",
        "--exclude-module=sqlalchemy.ext.compiler",
        "--exclude-module=sqlalchemy.ext.hybrid",
        "--exclude-module=sqlalchemy.ext.mutable",
        "--exclude-module=sqlalchemy.ext.orderinglist",
        "--exclude-module=pandas",
        "--exclude-module=numpy",
    ]

    print(f"Running command: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0:
        print("\nBuild completed successfully!")

        # Copy config.yaml and README.md to dist_win so they are visible next to the executable
        print("Copying config.yaml and README.md to output directory...")
        try:
            shutil.copy("config.yaml", os.path.join(DISTPATH, "config.yaml"))
            shutil.copy("README.md", os.path.join(DISTPATH, "README.md"))
            print("Successfully copied config.yaml and README.md.")
        except Exception as e:
            print(
                f"Warning: Could not copy configuration/readme to output directory: {e}"
            )

        print(f"Executable directory can be found at: {os.path.abspath(DISTPATH)}")
        print(
            f"Executable file: {os.path.join(os.path.abspath(DISTPATH), 'SimpleConnection.exe')}"
        )
        end_time = time.perf_counter()
        print(f"Build completed in {end_time - start_time:.2f} seconds.")
        # Clean up temporary PyInstaller build directories
        print("Cleaning up temporary build artifacts...")
        if os.path.exists(WORKPATH):
            try:
                shutil.rmtree(WORKPATH)
                print("Removed build workpath successfully.")
            except Exception as e:
                print(f"Warning: Could not remove build workpath: {e}")
    else:
        print("\nBuild failed with the following error:")
        print(res.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        build_app()
    except KeyboardInterrupt:
        print("\n\nBuild aborted by user (KeyboardInterrupt).")
        # Clean up temporary PyInstaller build directories if they exist
        if os.path.exists(WORKPATH):
            print("Cleaning up temporary build artifacts...")
            try:
                shutil.rmtree(WORKPATH)
                print("Removed build workpath successfully.")
            except Exception as e:
                print(f"Warning: Could not remove build workpath: {e}")
        sys.exit(1)
