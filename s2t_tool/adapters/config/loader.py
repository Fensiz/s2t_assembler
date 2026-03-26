from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Any

from s2t_tool.use_cases.settings import AppConfig
from s2t_tool.shared.resources import load_json_resource


APP_CONFIG_FILE = "app_config.json"


def load_app_config(config_path: str | Path | None = None) -> AppConfig:
    """
    Load app config.

    Priority:
    1. explicit external path
    2. bundled app_config.json resource
    """
    if config_path is None:
        return AppConfig.from_mapping(load_json_resource(APP_CONFIG_FILE))

    path = Path(config_path)
    if path.exists():
        return AppConfig.from_mapping(json.loads(path.read_text(encoding="utf-8")))

    return AppConfig.from_mapping(load_json_resource(str(config_path)))


def _coerce_config(config: AppConfig | Mapping[str, Any]) -> AppConfig:
    if isinstance(config, AppConfig):
        return config
    return AppConfig.from_mapping(config)


def expand_user_path(path: str) -> Path:
    """
    Expand '~' and return absolute resolved path.
    """
    return Path(path).expanduser().resolve()


def build_repo_url(base_url: str, product_name: str) -> str:
    """
    Build repo URL from base URL and product name.
    """
    return f"{base_url.rstrip('/')}/{product_name}.git"


def build_local_repo_path(workspace_dir: str, product_name: str) -> Path:
    """
    Build local repo path inside workspace directory.
    """
    return expand_user_path(workspace_dir) / product_name


def resolve_repo_url(config: AppConfig | Mapping[str, Any], product_name: str) -> str:
    config = _coerce_config(config)
    return build_repo_url(config.repo_base_url, product_name)


def resolve_repo_dir(config: AppConfig | Mapping[str, Any], product_name: str) -> Path:
    config = _coerce_config(config)
    return build_local_repo_path(config.workspace_dir, product_name)


def resolve_repo_data_dir(config: AppConfig | Mapping[str, Any], repo_dir: Path) -> Path:
    """
    Resolve directory inside repo where S2T data is stored.
    """
    config = _coerce_config(config)
    subdir = config.repo_data_subdir
    if subdir in ("", "."):
        return repo_dir
    return repo_dir / subdir


def resolve_excel_output_dir(config: AppConfig | Mapping[str, Any]) -> Path:
    """
    Resolve directory where generated Excel files are written.
    """
    config = _coerce_config(config)
    path = expand_user_path(config.excel_output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_writer_config(config: AppConfig | Mapping[str, Any]) -> str:
    """
    Resolve writer config file name/path.
    """
    config = _coerce_config(config)
    return config.writer_config


def ensure_excel_output_dir(path: Path) -> None:
    """
    Ensure output directory for generated Excel exists.
    """
    path.mkdir(parents=True, exist_ok=True)
