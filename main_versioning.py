from __future__ import annotations

from pathlib import Path

from common import read_json_file, write_json_file
from main_files import parse_version_from_excel_filename


VERSION_JSON = "version.json"


def read_repo_version(version_path: Path) -> str:
    """
    Read version from repo version.json.

    If file or value is missing, return default version.
    """
    payload = read_json_file(version_path, default={}) or {}
    version = payload.get("version")
    return str(version) if version else "0.0.0.0"


def write_repo_version(version_path: Path, version: str) -> None:
    """
    Write version into repo version.json.
    """
    write_json_file(version_path, {"version": version})


def bump_version(version: str) -> str:
    """
    Increment last numeric component of dotted version.
    """
    parts = [p.strip() for p in str(version).split(".") if p.strip()]
    if not parts:
        return "1"

    try:
        numbers = [int(p) for p in parts]
    except ValueError as exc:
        raise ValueError(f"Invalid version format: {version}") from exc

    numbers[-1] += 1
    return ".".join(str(n) for n in numbers)


def resolve_put_version(
    version_arg: str | None,
    input_excel: Path,
    product_name: str,
    version_path: Path,
) -> str:
    """
    Resolve new version for PUT.

    Priority:
    1. explicit --version
    2. version parsed from input Excel file name, then bumped
    3. version from repo version.json, then bumped
    """
    if version_arg is not None:
        return version_arg

    excel_version = parse_version_from_excel_filename(input_excel, product_name)
    if excel_version is not None:
        return bump_version(excel_version)

    repo_version = read_repo_version(version_path)
    return bump_version(repo_version)