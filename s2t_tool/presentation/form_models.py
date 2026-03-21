from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GetRequest:
    product_name: str
    branch: str | None
    diff_commit: str | None


@dataclass
class PutRequest:
    product_name: str
    branch: str | None
    commit_message: str | None
    version: str | None
