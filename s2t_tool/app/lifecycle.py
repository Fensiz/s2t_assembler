from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from s2t_tool.adapters.system.initial_setup import InitialSetupService
from s2t_tool.adapters.system.update_service import UpdateService


@dataclass(frozen=True)
class UpdateCheckResult:
    available: bool
    latest_version: str | None


class AppLifecycleService:
    def __init__(
        self,
        initial_setup_service: InitialSetupService,
        update_service: UpdateService,
    ) -> None:
        self.initial_setup_service = initial_setup_service
        self.update_service = update_service

    def ensure_initial_setup(self) -> None:
        self.initial_setup_service.ensure_initial_setup()

    def check_updates(self) -> UpdateCheckResult:
        available, latest_version = self.update_service.check_update()
        return UpdateCheckResult(available=available, latest_version=latest_version)

    def install_update(self) -> Path:
        return self.update_service.perform_update()
