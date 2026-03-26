from __future__ import annotations

from dataclasses import dataclass

from s2t_tool.app.lifecycle import AppLifecycleService
from s2t_tool.app.operations import AppOperationsService
from s2t_tool.use_cases.service import S2TService
from s2t_tool.use_cases.settings import AppConfig
from s2t_tool.adapters.facades import (
    DefaultPathResolver,
    GitRepositoryAdapter,
    OpenpyxlExcelAdapter,
    RecentItemsAdapter,
)
from s2t_tool.adapters.config.loader import load_app_config
from s2t_tool.adapters.system.initial_setup import InitialSetupService
from s2t_tool.adapters.system.update_service import UpdateService


@dataclass(frozen=True)
class AppContainer:
    config: AppConfig
    service: S2TService
    operations: AppOperationsService
    paths: DefaultPathResolver
    recent_items: RecentItemsAdapter
    lifecycle: AppLifecycleService


def build_container(config_path: str | None = None, logger=None) -> AppContainer:
    config = load_app_config(config_path)
    paths = DefaultPathResolver()
    service = S2TService(
        config=config,
        get_use_case=None,
        put_use_case=None,
    )
    operations = AppOperationsService(service)
    recent_items = RecentItemsAdapter()
    update_service = UpdateService(config, logger=logger)
    initial_setup_service = InitialSetupService(config, logger=logger)
    lifecycle = AppLifecycleService(
        initial_setup_service=initial_setup_service,
        update_service=update_service,
    )
    return AppContainer(
        config=config,
        service=service,
        operations=operations,
        paths=paths,
        recent_items=recent_items,
        lifecycle=lifecycle,
    )
