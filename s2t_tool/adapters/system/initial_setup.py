from __future__ import annotations

import json
import os
import shutil
import subprocess
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from s2t_tool.adapters.system.dependency_manager import ensure_dependencies


@dataclass
class SetupState:
    version: int = 1
    ssh_setup_prompt_shown: bool = False


class InitialSetupService:
    def __init__(self, app_config: dict[str, Any], logger=None) -> None:
        self.app_config = app_config
        self.logger = logger

        self.s2t_dir = Path.home() / ".s2t"
        self.state_file = self.s2t_dir / "setup.json"

        self.ssh_dir = Path.home() / ".ssh"
        self.known_hosts_file = self.ssh_dir / "known_hosts"

        self.bitbucket_ssh_page_url = self._build_bitbucket_ssh_page_url()

    def ensure_initial_setup(self) -> None:
        """
        Ensure first-run SSH setup is completed:

        1. Add Bitbucket host to known_hosts
        2. Ensure local SSH public key exists
        3. Open Bitbucket SSH keys page
        4. Log public key so user can copy it
        """
        state = self._load_state()
        if state.ssh_setup_prompt_shown:
            self._log("Initial setup already completed.")
            return

        ensure_dependencies(logger=self.logger)

        self._ensure_known_host()

        public_key_path = self._ensure_local_public_key()
        public_key = public_key_path.read_text(encoding="utf-8").strip()

        self._log("SSH-ключ найден или создан.")
        self._log(f"Публичный ключ: {public_key_path}")

        self._open_bitbucket_ssh_keys_page()

        self._log("=" * 80)
        self._log("Добавьте этот публичный SSH-ключ в Bitbucket:")
        self._log("")
        self._log(public_key)
        self._log("")
        self._log("Страница Bitbucket для добавления ключа была открыта в браузере.")
        self._log("=" * 80)

        state.ssh_setup_prompt_shown = True
        self._save_state(state)

    def _build_bitbucket_ssh_page_url(self) -> str:
        """
        Build Bitbucket page URL where user can add SSH keys.
        """
        base_url = str(self.app_config["repo_base_url"]).strip()
        host, _ = self._extract_host_and_port(base_url)
        return f"https://{host}/plugins/servlet/ssh/account/keys"

    def _extract_host_and_port(self, repo_url: str) -> tuple[str, int | None]:
        """
        Extract host and optional SSH port from supported repository/base URL formats.

        Supported examples:
            https://stash.corp.com/scm/project
            https://stash.corp.com:8443/scm/project
            ssh://git@stash.corp.com:7999/project/repo.git
            git@stash.corp.com:project/repo.git
        """
        # https://host/... or https://host:port/...
        if repo_url.startswith("https://"):
            without_scheme = repo_url[len("https://"):]
            host_part = without_scheme.split("/", 1)[0]
            if ":" in host_part:
                host, port_str = host_part.split(":", 1)
                try:
                    return host, int(port_str)
                except ValueError:
                    return host, None
            return host_part, None

        # http://host/... or http://host:port/...
        if repo_url.startswith("http://"):
            without_scheme = repo_url[len("http://"):]
            host_part = without_scheme.split("/", 1)[0]
            if ":" in host_part:
                host, port_str = host_part.split(":", 1)
                try:
                    return host, int(port_str)
                except ValueError:
                    return host, None
            return host_part, None

        # ssh://git@host:7999/project/repo.git
        if repo_url.startswith("ssh://"):
            without_scheme = repo_url[len("ssh://"):]
            if "@" in without_scheme:
                without_scheme = without_scheme.split("@", 1)[1]

            host_port = without_scheme.split("/", 1)[0]
            if ":" in host_port:
                host, port_str = host_port.split(":", 1)
                try:
                    return host, int(port_str)
                except ValueError:
                    return host, None

            return host_port, None

        # git@host:project/repo.git
        # Здесь двоеточие после host не означает порт, а разделяет путь репозитория.
        if "@" in repo_url and ":" in repo_url:
            after_at = repo_url.split("@", 1)[1]
            host = after_at.split(":", 1)[0]
            return host, None

        raise RuntimeError(f"Unsupported repo URL format: {repo_url}")

    def _known_hosts_lookup_name(self, host: str, port: int | None) -> str:
        """
        Build host key lookup name for known_hosts.

        For non-default SSH port OpenSSH uses:
            [host]:port
        """
        if port is None or port == 22:
            return host
        return f"[{host}]:{port}"

    def _ensure_known_host(self) -> None:
        """
        Ensure Bitbucket host key is present in ~/.ssh/known_hosts.
        """
        self.ssh_dir.mkdir(parents=True, exist_ok=True)
        self._chmod_if_possible(self.ssh_dir, 0o700)

        repo_base_url = str(self.app_config["repo_base_url"]).strip()
        host, port = self._extract_host_and_port(repo_base_url)
        lookup_name = self._known_hosts_lookup_name(host, port)

        if self._known_host_exists(lookup_name):
            self._log(f"Host already exists in known_hosts: {lookup_name}")
            return

        ssh_keyscan = shutil.which("ssh-keyscan")
        if not ssh_keyscan:
            raise RuntimeError("ssh-keyscan not found in PATH")
        ssh_keyscan = str(ssh_keyscan)

        self._log(f"Scanning SSH host key for: {lookup_name}")

        cmd = [ssh_keyscan, "-H"]
        if port is not None and port != 22:
            cmd.extend(["-p", str(port)])
        cmd.append(host)

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        output = result.stdout.strip()
        error_output = result.stderr.strip()

        if result.returncode != 0 or not output:
            raise RuntimeError(
                f"Failed to scan SSH host key for '{lookup_name}'. "
                f"stderr: {error_output}"
            )

        file_exists = self.known_hosts_file.exists()
        file_has_content = file_exists and self.known_hosts_file.stat().st_size > 0

        self.known_hosts_file.parent.mkdir(parents=True, exist_ok=True)
        with self.known_hosts_file.open("a", encoding="utf-8") as f:
            if file_has_content:
                f.write("\n")
            f.write(output)
            f.write("\n")

        self._chmod_if_possible(self.known_hosts_file, 0o644)

        if self._known_host_exists(lookup_name):
            self._log(f"Host added to known_hosts: {lookup_name}")
        else:
            self._log(
                f"SSH host key was written to known_hosts, but lookup by name "
                f"'{lookup_name}' did not confirm it."
            )

    def _known_host_exists(self, lookup_name: str) -> bool:
        """
        Check whether host is already present in ~/.ssh/known_hosts.

        Works with hashed entries too when ssh-keygen is available.
        """
        if not self.known_hosts_file.exists():
            return False

        ssh_keygen = shutil.which("ssh-keygen")
        if ssh_keygen:
            ssh_keygen = str(ssh_keygen)
            result = subprocess.run(
                [ssh_keygen, "-F", lookup_name, "-f", str(self.known_hosts_file)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return result.returncode == 0 and bool(result.stdout.strip())

        # Fallback: plain text search only works reliably for non-hashed entries.
        content = self.known_hosts_file.read_text(encoding="utf-8", errors="ignore")
        return lookup_name in content

    def _ensure_local_public_key(self) -> Path:
        """
        Ensure local SSH public key exists. If not, create ed25519 keypair.
        """
        self.ssh_dir.mkdir(parents=True, exist_ok=True)
        self._chmod_if_possible(self.ssh_dir, 0o700)

        for candidate in self._candidate_public_keys():
            if candidate.exists():
                return candidate

        ssh_keygen = shutil.which("ssh-keygen")
        if not ssh_keygen:
            raise RuntimeError("ssh-keygen not found in PATH")
        ssh_keygen = str(ssh_keygen)

        private_key = self.ssh_dir / "id_ed25519"
        public_key = self.ssh_dir / "id_ed25519.pub"

        subprocess.run(
            [
                ssh_keygen,
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "s2t-auto-key",
                "-f",
                str(private_key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        self._chmod_if_possible(private_key, 0o600)
        self._chmod_if_possible(public_key, 0o644)

        if not public_key.exists():
            raise RuntimeError("Failed to generate SSH public key")

        return public_key

    def _candidate_public_keys(self) -> list[Path]:
        return [
            self.ssh_dir / "id_ed25519.pub",
            self.ssh_dir / "id_rsa.pub",
        ]

    def _open_bitbucket_ssh_keys_page(self) -> None:
        """
        Open Bitbucket SSH keys page in browser.
        """
        try:
            webbrowser.open(self.bitbucket_ssh_page_url)
            self._log(f"Открыта страница Bitbucket: {self.bitbucket_ssh_page_url}")
        except Exception as exc:
            self._log(f"Не удалось открыть браузер автоматически: {exc}")
            self._log(f"Откройте вручную: {self.bitbucket_ssh_page_url}")

    def _load_state(self) -> SetupState:
        """
        Load persisted initial setup state.
        """
        if not self.state_file.exists():
            return SetupState()

        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            return SetupState(**data)
        except Exception:
            return SetupState()

    def _save_state(self, state: SetupState) -> None:
        """
        Save persisted initial setup state.
        """
        self.s2t_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _log(self, message: str) -> None:
        """
        Send message to UI logger if provided, otherwise print to console.
        """
        if self.logger is not None:
            try:
                self.logger(message)
                return
            except Exception:
                pass
        print(message)

    @staticmethod
    def _chmod_if_possible(path: Path, mode: int) -> None:
        try:
            os.chmod(path, mode)
        except OSError:
            pass
