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

        self.workspace = Path.home() / ".s2t"
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.repo_name = config["pyz_repo"]
        self.branch = config.get("pyz_branch", "master")
        self.repo_url = f"{config['repo_base_url'].rstrip('/')}/{self.repo_name}.git"

        self.repo_dir = self.workspace / self.repo_name

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
        latest_version = data.get("version")

        if not latest_version:
            return False, None

        if self._is_newer(latest_version, APP_VERSION):
            return True, latest_version

        return False, latest_version

    def perform_update(self) -> Path:
        """
        Install update and return path to the updated application file.
        """
        self._ensure_repo()

        manifest_path = self.repo_dir / "latest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))

        relative_path = data.get("path") or data.get("filename")
        if not relative_path:
            raise RuntimeError("Update manifest does not contain 'path' or 'filename'")

        source_file = self.repo_dir / relative_path
        self._log(f"Looking for update file: {source_file}")

        if not source_file.exists():
            raise RuntimeError(f"Update file not found: {source_file}")

        target_dir = Path.home() / ".s2t" / "app"
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / "s2t.pyz"
        temp_file = target_dir / "s2t.new.pyz"

        self._log("Copying update...")
        temp_file.write_bytes(source_file.read_bytes())
        temp_file.replace(target_file)

        self._log("Update installed.")
        return target_file

    # ---------------------------------------------------------
    # Internal
    # ---------------------------------------------------------

    def _ensure_repo(self) -> None:
        if not self.repo_dir.exists():
            self._log("Cloning updates repository...")
            self._run_git(["clone", self.repo_url, str(self.repo_dir)])
        else:
            self._log("Updating releases repository...")
            self._run_git(["fetch"], cwd=self.repo_dir)
            self._run_git(["reset", "--hard", f"origin/{self.branch}"], cwd=self.repo_dir)

    def _run_git(self, args: list[str], cwd: Path | None = None) -> str:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"

        if self.logger:
            self.logger(f"Running: git {' '.join(args)}")

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

        if self.logger:
            if stdout:
                self.logger(stdout)
            if stderr:
                self.logger(stderr)

        if result.returncode != 0:
            raise RuntimeError(
                f"Git command failed: git {' '.join(args)}\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )

        return stdout

    def _is_newer(self, latest: str, current: str) -> bool:
        def parse(v: str) -> list[int]:
            return [int(x) for x in v.split(".") if x.isdigit()]

        return parse(latest) > parse(current)

    def _log(self, msg: str) -> None:
        if self.logger:
            self.logger(msg)
        else:
            print(msg)