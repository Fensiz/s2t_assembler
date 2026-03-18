from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app_info import APP_VERSION


class UpdateService:
    def __init__(self, config: dict[str, Any], logger=None) -> None:
        self.config = config
        self.logger = logger

        self.base_dir = Path.home() / ".s2t"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.repo_name = config["pyz_repo"]
        self.branch = str(config.get("pyz_branch", "master")).strip()
        self.repo_url = f"{config['repo_base_url'].rstrip('/')}/{self.repo_name}.git"

        self.repo_dir = self.base_dir / self.repo_name

        self.app_dir = self.base_dir / "app"
        self.versions_dir = self.app_dir / "versions"
        self.current_link = self.app_dir / "current.pyz"

        self.is_windows = os.name == "nt"

        # launcher нужен только на Unix-like системах
        self.launcher_path = self.base_dir / "s2t-tool.command"
        self.desktop_shortcut_path = (
            Path.home() / "Desktop" / ("s2t-tool.lnk" if self.is_windows else "s2t-tool.command")
        )

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def check_update(self) -> tuple[bool, str | None]:
        """
        Returns:
            (is_update_available, latest_version)
        """
        self._ensure_repo()

        latest_json = self.repo_dir / "latest.json"
        if not latest_json.exists():
            self._log("latest.json not found")
            return False, None

        data = json.loads(latest_json.read_text(encoding="utf-8"))
        latest_version = str(data.get("version", "")).strip()

        if not latest_version:
            return False, None

        if self._is_newer(latest_version, APP_VERSION):
            return True, latest_version

        return False, latest_version

    def perform_update(self) -> Path:
        """
        Install update into managed app directory and return path to current.pyz.
        """
        self._ensure_repo()

        manifest_path = self.repo_dir / "latest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))

        version = str(data.get("version", "")).strip()
        if not version:
            raise RuntimeError("Update manifest does not contain 'version'")

        relative_path = data.get("path") or data.get("filename")
        if not relative_path:
            raise RuntimeError("Update manifest does not contain 'path' or 'filename'")

        source_file = self.repo_dir / relative_path
        self._log(f"Looking for update file: {source_file}")

        if not source_file.exists():
            raise RuntimeError(f"Update file not found: {source_file}")

        installed_version_file = self._install_version(source_file, version)
        self._update_current_pointer(installed_version_file)

        if not self.is_windows:
            self._ensure_launcher()

        self._ensure_desktop_shortcut()

        self._log("Update installed.")
        return self.current_link

    # ---------------------------------------------------------
    # Internal: repo sync
    # ---------------------------------------------------------

    def _ensure_repo(self) -> None:
        if not self.repo_dir.exists():
            self._log("Cloning updates repository...")
            self._run_git(["clone", "--branch", self.branch, self.repo_url, str(self.repo_dir)])
        else:
            self._log("Updating releases repository...")
            self._run_git(["fetch"], cwd=self.repo_dir)
            self._run_git(["reset", "--hard", f"origin/{self.branch}"], cwd=self.repo_dir)

    def _run_git(self, args: list[str], cwd: Path | None = None) -> str:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"

        self._log(f"Running: git {' '.join(args)}")

        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if stdout:
            self._log(stdout)
        if stderr:
            self._log(stderr)

        if result.returncode != 0:
            raise RuntimeError(
                f"Git command failed: git {' '.join(args)}\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )

        return stdout

    # ---------------------------------------------------------
    # Internal: install layout
    # ---------------------------------------------------------

    def _install_version(self, source_file: Path, version: str) -> Path:
        """
        Copy versioned pyz into managed versions directory.
        """
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        target_file = self.versions_dir / f"s2t-tool-{version}.pyz"
        temp_file = self.versions_dir / f"s2t-tool-{version}.new.pyz"

        self._log(f"Installing version {version}...")
        temp_file.write_bytes(source_file.read_bytes())
        temp_file.replace(target_file)

        self._log(f"Installed version file: {target_file}")
        return target_file

    def _update_current_pointer(self, target: Path) -> None:
        """
        Update managed current app pointer.

        On Unix-like systems use symlink.
        On Windows use file copy because symlink often requires elevated privileges.
        """
        self.app_dir.mkdir(parents=True, exist_ok=True)

        if self.current_link.exists() or self.current_link.is_symlink():
            self.current_link.unlink()

        if self.is_windows:
            temp_file = self.app_dir / "current.new.pyz"
            temp_file.write_bytes(target.read_bytes())
            temp_file.replace(self.current_link)
            self._log(f"Updated current file: {self.current_link}")
        else:
            self.current_link.symlink_to(target)
            self._log(f"Updated current symlink: {self.current_link} -> {target}")

    def _ensure_launcher(self) -> None:
        """
        Create/update stable launcher script for Unix-like systems.
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)

        python_executable = os.environ.get("PYTHON_EXECUTABLE_OVERRIDE") or sys.executable
        if not python_executable:
            python_executable = "python3"

        content = (
            "#!/bin/bash\n"
            f"exec \"{python_executable}\" \"{self.current_link}\"\n"
        )

        self.launcher_path.write_text(content, encoding="utf-8")
        self._chmod_if_possible(self.launcher_path, 0o755)

        self._log(f"Launcher ready: {self.launcher_path}")

    def _ensure_desktop_shortcut(self) -> None:
        """
        Create/update desktop shortcut.
        """
        desktop_dir = self.desktop_shortcut_path.parent
        if not desktop_dir.exists():
            self._log("Desktop directory not found. Skipping shortcut creation.")
            return

        if self.is_windows:
            self._create_windows_shortcut()
        else:
            if self.desktop_shortcut_path.exists() or self.desktop_shortcut_path.is_symlink():
                self.desktop_shortcut_path.unlink()

            self.desktop_shortcut_path.symlink_to(self.launcher_path)
            self._log(f"Desktop shortcut ready: {self.desktop_shortcut_path}")

    def _create_windows_shortcut(self) -> None:
        """
        Create Windows .lnk shortcut on Desktop via PowerShell.
        No extra Python package is required.
        """
        if self.desktop_shortcut_path.exists():
            self.desktop_shortcut_path.unlink()

        python_executable = os.environ.get("PYTHON_EXECUTABLE_OVERRIDE") or sys.executable
        if not python_executable:
            python_executable = "python"

        target_path = str(Path(python_executable))
        arguments = f'"{self.current_link}"'
        working_directory = str(self.base_dir)
        shortcut_path = str(self.desktop_shortcut_path)
        icon_location = f"{target_path},0"

        # Одинарные кавычки в PowerShell-строках нужно экранировать удвоением
        def ps_escape(value: str) -> str:
            return value.replace("'", "''")

        ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{ps_escape(shortcut_path)}')
$Shortcut.TargetPath = '{ps_escape(target_path)}'
$Shortcut.Arguments = '{ps_escape(arguments)}'
$Shortcut.WorkingDirectory = '{ps_escape(working_directory)}'
$Shortcut.IconLocation = '{ps_escape(icon_location)}'
$Shortcut.Save()
"""

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_script,
            ],
            capture_output=True,
            text=True,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if stdout:
            self._log(stdout)
        if stderr:
            self._log(stderr)

        if result.returncode != 0:
            raise RuntimeError(
                "Failed to create Windows shortcut.\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )

        self._log(f"Desktop shortcut ready: {self.desktop_shortcut_path}")

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    def _is_newer(self, latest: str, current: str) -> bool:
        def parse(v: str) -> list[int]:
            parts: list[int] = []
            for part in v.split("."):
                part = part.strip()
                if part.isdigit():
                    parts.append(int(part))
                else:
                    break
            return parts

        return parse(latest) > parse(current)

    def _log(self, msg: str) -> None:
        if self.logger:
            self.logger(msg)
        else:
            print(msg)

    @staticmethod
    def _chmod_if_possible(path: Path, mode: int) -> None:
        try:
            os.chmod(path, mode)
        except OSError:
            pass