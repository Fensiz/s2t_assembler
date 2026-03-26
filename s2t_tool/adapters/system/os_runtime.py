from __future__ import annotations

import os
import subprocess
import sys
import threading
import shutil
from pathlib import Path
from typing import Callable


def open_file_in_os(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def open_directory_in_os(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def run_in_thread(fn: Callable[[], None]) -> None:
    thread = threading.Thread(target=fn, daemon=True)
    thread.start()


def resolve_python_executable() -> str:
    return sys.executable or (
        shutil.which("pythonw")
        or shutil.which("python3")
        or shutil.which("python")
        or "python3"
    )


def launch_app_detached(app_path: Path, logger=None) -> list[str]:
    command = [resolve_python_executable(), str(app_path)]
    if logger:
        logger(f"Launching updated app: {' '.join(command)}")
    subprocess.Popen(command, start_new_session=True, close_fds=True)
    return command
