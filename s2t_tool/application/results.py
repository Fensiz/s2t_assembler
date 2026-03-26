from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GetResult:
    product_name: str
    output_excel: Path
    diff_mode: bool


@dataclass(frozen=True)
class PutResult:
    product_name: str
    repo_dir: Path
    version: str | None
    changed: bool


@dataclass(frozen=True)
class RecentItem:
    product_name: str
    branch: str = ""
