from __future__ import annotations

from pathlib import Path

from s2t_tool.use_cases.ports import PathResolver
from s2t_tool.use_cases.settings import AppConfig
from s2t_tool.adapters.config.loader import (
    resolve_excel_output_dir,
    resolve_repo_data_dir,
    resolve_repo_dir,
    resolve_repo_url,
    resolve_writer_config,
)


class DefaultPathResolver(PathResolver):
    def repo_url(self, config: AppConfig, product_name: str) -> str:
        return resolve_repo_url(config, product_name)

    def repo_dir(self, config: AppConfig, product_name: str) -> Path:
        return resolve_repo_dir(config, product_name)

    def repo_data_dir(self, config: AppConfig, repo_dir: Path) -> Path:
        return resolve_repo_data_dir(config, repo_dir)

    def excel_output_dir(self, config: AppConfig) -> Path:
        return resolve_excel_output_dir(config)

    def writer_config(self, config: AppConfig) -> str:
        return resolve_writer_config(config)
