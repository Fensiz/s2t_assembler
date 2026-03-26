from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class AppConfig:
    repo_base_url: str
    workspace_dir: str = "~/.s2t"
    repo_data_subdir: str = "."
    excel_output_dir: str = "."
    writer_config: str = "writer_config.json"
    default_branch: str = "master"
    language: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "AppConfig":
        known = {
            "repo_base_url",
            "workspace_dir",
            "repo_data_subdir",
            "excel_output_dir",
            "writer_config",
            "default_branch",
            "language",
        }
        extra = {key: value for key, value in raw.items() if key not in known}
        return cls(
            repo_base_url=str(raw.get("repo_base_url", "")).strip(),
            workspace_dir=str(raw.get("workspace_dir", "~/.s2t")).strip(),
            repo_data_subdir=str(raw.get("repo_data_subdir", ".")).strip(),
            excel_output_dir=str(raw.get("excel_output_dir", ".")).strip(),
            writer_config=str(raw.get("writer_config", "writer_config.json")).strip(),
            default_branch=str(raw.get("default_branch", "master")).strip(),
            language=str(raw.get("language")).strip() if raw.get("language") else None,
            extra=extra,
        )

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            value = getattr(self, key)
            return default if value is None else value
        return self.extra.get(key, default)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            value = getattr(self, key)
            if value is None:
                raise KeyError(key)
            return value
        return self.extra[key]

    def as_dict(self) -> dict[str, Any]:
        data = {
            "repo_base_url": self.repo_base_url,
            "workspace_dir": self.workspace_dir,
            "repo_data_subdir": self.repo_data_subdir,
            "excel_output_dir": self.excel_output_dir,
            "writer_config": self.writer_config,
            "default_branch": self.default_branch,
        }
        if self.language:
            data["language"] = self.language
        data.update(self.extra)
        return data
