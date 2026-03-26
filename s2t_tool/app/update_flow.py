from __future__ import annotations

from pathlib import Path

from s2t_tool.app.lifecycle import AppLifecycleService, UpdateCheckResult
from s2t_tool.adapters.system.os_runtime import launch_app_detached


class AppUpdateFlowService:
    def __init__(self, lifecycle: AppLifecycleService) -> None:
        self.lifecycle = lifecycle

    def check_updates(self, logger=None) -> UpdateCheckResult:
        self.lifecycle.update_service.logger = logger
        return self.lifecycle.check_updates()

    def install_update(self, logger=None) -> Path:
        self.lifecycle.update_service.logger = logger
        return self.lifecycle.install_update()

    def restart_updated_app(self, app_path: Path, logger=None) -> list[str]:
        return launch_app_detached(app_path, logger=logger)
