from __future__ import annotations

import json
import os
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SetupState:
    version: int = 1
    ssh_setup_prompt_shown: bool = False


class InitialSetupService:
    def __init__(self, app_config: dict, logger=None) -> None:
        self.app_config = app_config
        self.logger = logger

        self.s2t_dir = Path.home() / ".s2t"
        self.state_file = self.s2t_dir / "setup.json"

        self.ssh_dir = Path.home() / ".ssh"
        self.bitbucket_ssh_page_url = self._build_bitbucket_ssh_page_url()

    def ensure_initial_setup(self) -> None:
        state = self._load_state()
        if state.ssh_setup_prompt_shown:
            return

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
        base_url = str(self.app_config["repo_base_url"]).strip()
        host = self._extract_host(base_url)
        return f"https://{host}/plugins/servlet/ssh/account/keys"

    def _extract_host(self, repo_url: str) -> str:
        # ssh://git@host:7999/project/repo.git
        if repo_url.startswith("ssh://"):
            without_scheme = repo_url[len("ssh://"):]
            if "@" in without_scheme:
                without_scheme = without_scheme.split("@", 1)[1]
            host_port = without_scheme.split("/", 1)[0]
            if ":" in host_port:
                return host_port.split(":", 1)[0]
            return host_port

        # git@host:project/repo.git
        if "@" in repo_url and ":" in repo_url:
            after_at = repo_url.split("@", 1)[1]
            return after_at.split(":", 1)[0]

        raise RuntimeError(f"Unsupported repoUrl format: {repo_url}")

    def _ensure_local_public_key(self) -> Path:
        self.ssh_dir.mkdir(parents=True, exist_ok=True)
        self._chmod_if_possible(self.ssh_dir, 0o700)

        for candidate in self._candidate_public_keys():
            if candidate.exists():
                return candidate

        ssh_keygen = shutil.which("ssh-keygen")
        if not ssh_keygen:
            raise RuntimeError("ssh-keygen not found in PATH")

        private_key = self.ssh_dir / "id_ed25519"
        public_key = self.ssh_dir / "id_ed25519.pub"

        subprocess.run(
            [
                ssh_keygen,
                "-t", "ed25519",
                "-N", "",
                "-C", "s2t-auto-key",
                "-f", str(private_key),
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
        try:
            webbrowser.open(self.bitbucket_ssh_page_url)
            self._log(f"Открыта страница Bitbucket: {self.bitbucket_ssh_page_url}")
        except Exception as exc:
            self._log(f"Не удалось открыть браузер автоматически: {exc}")
            self._log(f"Откройте вручную: {self.bitbucket_ssh_page_url}")

    def _load_state(self) -> SetupState:
        if not self.state_file.exists():
            return SetupState()

        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            return SetupState(**data)
        except Exception:
            return SetupState()

    def _save_state(self, state: SetupState) -> None:
        self.s2t_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _log(self, message: str) -> None:
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