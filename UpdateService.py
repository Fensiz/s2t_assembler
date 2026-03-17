from __future__ import annotations

import json
import os
import subprocess
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

        self.launcher_path = self.base_dir / "s2t-tool.command"
        self.desktop_shortcut_path = (Path.home() / "Desktop" / "s2t-tool.command")

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
        self._update_current_symlink(installed_version_file)
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

    def _update_current_symlink(self, target: Path) -> None:
        """
        Update ~/.s2t/app/current.pyz symlink to point to installed version.
        """
        self.app_dir.mkdir(parents=True, exist_ok=True)

        if self.current_link.exists() or self.current_link.is_symlink():
            self.current_link.unlink()

        self.current_link.symlink_to(target)
        self._log(f"Updated current symlink: {self.current_link} -> {target}")

    def _ensure_launcher(self) -> None:
        """
        Create/update stable launcher script:
            ~/.s2t/s2t-tool.command
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)

        python_executable = os.environ.get("PYTHON_EXECUTABLE_OVERRIDE") or os.sys.executable or "/usr/bin/env python3"

        script = (
            "#!/bin/bash\n"
            f'exec "{python_executable}" "{self.current_link}"\n'
        )

        self.launcher_path.write_text(script, encoding="utf-8")
        self._chmod_if_possible(self.launcher_path, 0o755)

        self._log(f"Launcher ready: {self.launcher_path}")

    def _ensure_desktop_shortcut(self) -> None:
        """
        Create/update desktop shortcut that points to launcher.
        """
        desktop_dir = self.desktop_shortcut_path.parent
        if not desktop_dir.exists():
            self._log("Desktop directory not found. Skipping shortcut creation.")
            return

        if self.desktop_shortcut_path.exists() or self.desktop_shortcut_path.is_symlink():
            self.desktop_shortcut_path.unlink()

        self.desktop_shortcut_path.symlink_to(self.launcher_path)
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