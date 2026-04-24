from __future__ import annotations

from dataclasses import dataclass

from s2t_tool.shared.constants import Logger


@dataclass
class GetCommand:
    product_name: str
    branch_arg: str | None
    version_arg: str | None
    diff_commit_arg: str | None
    logger: Logger | None = None


@dataclass
class PutCommand:
    product_name: str
    branch_arg: str | None
    version_arg: str | None
    keep_version: bool
    format_sql: bool
    excel_arg: str | None
    commit_message_arg: str | None
    logger: Logger | None = None
