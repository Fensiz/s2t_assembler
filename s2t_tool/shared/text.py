from __future__ import annotations

import re
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
    sanitized = normalize_newlines(str(value))
    sanitized = re.sub(r"[\x00-\x1f]", " ", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    for ch in ["/", "\\", ":", "*", "?", "\"", "<", ">", "|"]:
        sanitized = sanitized.replace(ch, "_")
    sanitized = sanitized.rstrip(" .")

    reserved = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }
    if not sanitized:
        return "_"
    if sanitized.upper() in reserved:
        return f"_{sanitized}"
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
