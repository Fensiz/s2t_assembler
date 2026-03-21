from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable


def open_file_in_os(path: Path) -> None:
    """
    Open file in the default OS application.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def open_directory_in_os(path: Path) -> None:
    """
    Open directory in the OS file manager.
    """
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def run_in_thread(fn: Callable[[], None]) -> None:
    """
    Run function in a daemon thread.
    """
    thread = threading.Thread(target=fn, daemon=True)
    thread.start()


def find_latest_excel_file(
    excel_dir: Path,
    product_name: str,
    diff_mode: bool,
) -> Path | None:
    """
    Find the newest generated Excel file for the product.

    Supports:
    - normal:      S2T_USL_<PRODUCT>_v*.xlsx
    - debug:       S2T_USL_<PRODUCT>_v*_debug.xlsx
    - diff:        S2T_USL_<PRODUCT>_v*_diff.xlsx
    - debug diff:  S2T_USL_<PRODUCT>_v*_debug_diff.xlsx
    """
    product_upper = product_name.upper()

    if diff_mode:
        patterns = [
            f"S2T_USL_{product_upper}_v*_debug_diff.xlsx",
            f"S2T_USL_{product_upper}_v*_diff.xlsx",
        ]
    else:
        patterns = [
            f"S2T_USL_{product_upper}_v*_commit_*.xlsx",
            f"S2T_USL_{product_upper}_v*_debug.xlsx",
            f"S2T_USL_{product_upper}_v*.xlsx",
        ]

    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(excel_dir.glob(pattern))

    if not diff_mode:
        candidates = [p for p in candidates if not p.name.lower().endswith("_diff.xlsx")]

    candidates = sorted(
        candidates,
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return candidates[0] if candidates else None
