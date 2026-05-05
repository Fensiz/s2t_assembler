from __future__ import annotations

from pathlib import Path

from s2t_tool.shared.constants import Logger
from s2t_tool.app.lifecycle import AppLifecycleService, UpdateCheckResult
from s2t_tool.adapters.system.os_runtime import detect_running_app_path, launch_app_detached


class AppUpdateFlowService:
    def __init__(self, lifecycle: AppLifecycleService) -> None:
        self.lifecycle = lifecycle

    def check_updates(self, logger: Logger | None = None) -> UpdateCheckResult:
        self.lifecycle.update_service.logger = logger
        return self.lifecycle.check_updates()

    def install_update(self, logger: Logger | None = None) -> Path:
        self.lifecycle.update_service.logger = logger
        return self.lifecycle.install_update()

    def restart_updated_app(self, app_path: Path, logger: Logger | None = None) -> list[str]:
        return launch_app_detached(app_path, logger=logger)

    def detect_running_app(self) -> Path | None:
        return detect_running_app_path()

    def is_running_from_managed_location(self, app_path: Path | None) -> bool:
        return self.lifecycle.update_service.is_running_from_managed_location(app_path)

    def adopt_external_app(self, app_path: Path, logger: Logger | None = None) -> Path:
        self.lifecycle.update_service.logger = logger
        return self.lifecycle.update_service.adopt_external_app(app_path)
