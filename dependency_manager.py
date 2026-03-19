from __future__ import annotations

import importlib
import subprocess
import sys


REQUIRED_PACKAGES = {
    "openpyxl": "openpyxl",
}


def ensure_dependencies(logger=None) -> None:
    """
    Ensure required Python packages are installed.
    """
    for module_name, package_name in REQUIRED_PACKAGES.items():
        if _module_exists(module_name):
            continue

        _log(logger, f"Installing dependency: {package_name}...")

        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                package_name,
            ]
        )

        _log(logger, f"Installed: {package_name}")


def _module_exists(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def _log(logger, message: str) -> None:
    if logger:
        logger(message)
    else:
        print(message)