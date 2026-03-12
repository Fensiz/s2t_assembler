from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
import sys
import zipfile

JOIN_SOURCE_SQL = "source_tables_join.sql"
PACKAGE_NAME = "s2t_tool"


def load_text_resource(filename: str) -> str:
    # 1. обычный запуск из файловой системы
    file_path = Path(__file__).resolve().parent / filename
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")

    # 2. запуск из zipapp (.pyz)
    archive_path = Path(sys.argv[0]).resolve()
    if archive_path.exists() and archive_path.suffix == ".pyz":
        with zipfile.ZipFile(archive_path, "r") as archive:
            try:
                with archive.open(filename, "r") as f:
                    return f.read().decode("utf-8")
            except KeyError:
                pass

    raise FileNotFoundError(f"Resource not found: {filename}")


def load_json_resource(filename: str) -> dict[str, Any]:
    return json.loads(load_text_resource(filename))


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_newlines(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text_file(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_json_file(path: Path, payload: dict | list) -> None:
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_json_file(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv_rows(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers)
        writer.writerows(rows)


def read_csv_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        return [], []

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)

    if not rows:
        return [], []

    return rows[0], rows[1:]


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

def read_repo_version(version_path: Path) -> str:
    payload = read_json_file(version_path, default={}) or {}
    return str(payload.get("version", "0.0.0.0"))


def write_repo_version(version_path: Path, version: str) -> None:
    payload = read_json_file(version_path, default={}) or {}
    payload["version"] = version
    write_json_file(version_path, payload)

def bump_version(version: str) -> str:
    parts = [p.strip() for p in version.split(".") if p.strip()]
    if not parts:
        return "1"

    try:
        numbers = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"Invalid version format: {version}")

    numbers[-1] += 1
    return ".".join(str(n) for n in numbers)