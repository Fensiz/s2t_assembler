from __future__ import annotations

from typing import Any


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_newlines(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def slugify_dir_name(value: str) -> str:
    sanitized = value.strip()
    for ch in ["/", "\\", ":", "*", "?", "\"", "<", ">", "|"]:
        sanitized = sanitized.replace(ch, "_")
    return sanitized


def split_lines(text: str) -> list[str]:
    return [item.strip() for item in text.splitlines() if item.strip()]


def is_row_empty(values: list[str]) -> bool:
    return all(v == "" for v in values)


def excel_to_repo_header(name: str) -> str:
    normalized = normalize_cell(name).lower().replace(" ", "_")
    if normalized == "is_a_key":
        return "is_key"
    return normalized

