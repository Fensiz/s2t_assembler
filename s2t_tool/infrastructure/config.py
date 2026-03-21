from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from s2t_tool.shared.resources import load_json_resource


APP_CONFIG_FILE = "app_config.json"


def load_app_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load app config.

    Priority:
    1. explicit external path
    2. bundled app_config.json resource
    """
    if config_path is None:
        return load_json_resource(APP_CONFIG_FILE)

    path = Path(config_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    return load_json_resource(str(config_path))


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


def resolve_repo_url(config: dict[str, Any], product_name: str) -> str:
    base_url = config["repo_base_url"]
    return build_repo_url(base_url, product_name)


def resolve_repo_dir(config: dict[str, Any], product_name: str) -> Path:
    workspace_dir = config.get("workspace_dir", "~/.s2t")
    return build_local_repo_path(workspace_dir, product_name)


def resolve_repo_data_dir(config: dict[str, Any], repo_dir: Path) -> Path:
    """
    Resolve directory inside repo where S2T data is stored.
    """
    subdir = config.get("repo_data_subdir", ".")
    if subdir in ("", "."):
        return repo_dir
    return repo_dir / subdir


def resolve_excel_output_dir(config: dict[str, Any]) -> Path:
    """
    Resolve directory where generated Excel files are written.
    """
    path = expand_user_path(config.get("excel_output_dir", "."))
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_writer_config(config: dict[str, Any]) -> str:
    """
    Resolve writer config file name/path.
    """
    return config.get("writer_config", "writer_config.json")


def ensure_excel_output_dir(path: Path) -> None:
    """
    Ensure output directory for generated Excel exists.
    """
    path.mkdir(parents=True, exist_ok=True)
