from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GetCommand:
    product_name: str
    branch_arg: str | None
    version_arg: str | None
    diff_commit_arg: str | None
    config: dict[str, Any]
    logger: Any = None


@dataclass
class PutCommand:
    product_name: str
    branch_arg: str | None
    version_arg: str | None
    keep_version: bool
    format_sql: bool
    excel_arg: str | None
    commit_message_arg: str | None
    config: dict[str, Any]
    logger: Any = None
