from __future__ import annotations

from dataclasses import dataclass

from s2t_tool.use_cases.service import S2TService
from s2t_tool.use_cases.settings import AppConfig
from s2t_tool.adapters.facades import (
    DefaultPathResolver,
    ExcelArtifactAdapter,
    GitRepositoryAdapter,
    OpenpyxlExcelAdapter,
    RecentItemsAdapter,
)
from s2t_tool.adapters.config.loader import load_app_config
from s2t_tool.adapters.system.update_service import UpdateService


@dataclass(frozen=True)
class AppContainer:
    config: AppConfig
    service: S2TService
    paths: DefaultPathResolver
    artifacts: ExcelArtifactAdapter
    recent_items: RecentItemsAdapter
    update_service: UpdateService


def build_container(config_path: str | None = None, logger=None) -> AppContainer:
    config = load_app_config(config_path)
    paths = DefaultPathResolver()
    service = S2TService(
        config=config,
        get_use_case=None,
        put_use_case=None,
    )
    artifacts = ExcelArtifactAdapter()
    recent_items = RecentItemsAdapter()
    update_service = UpdateService(config, logger=logger)
    return AppContainer(
        config=config,
        service=service,
        paths=paths,
        artifacts=artifacts,
        recent_items=recent_items,
        update_service=update_service,
    )
