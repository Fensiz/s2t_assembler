from __future__ import annotations

import re
from pathlib import Path

from main_branching import is_debug_branch


def build_branch_excel_filename(product_name: str, version: str, debug_mode: bool) -> str:
    """
    Build Excel file name for normal export, with optional _debug suffix.
    """
    suffix = "_debug" if debug_mode else ""
    return f"S2T_USL_{product_name.upper()}_v{version}{suffix}.xlsx"


def build_branch_diff_excel_filename(product_name: str, version: str, debug_mode: bool) -> str:
    """
    Build Excel file name for diff export, with optional _debug suffix.
    """
    suffix = "_debug" if debug_mode else ""
    return f"S2T_USL_{product_name.upper()}_v{version}{suffix}_diff.xlsx"


def parse_version_from_excel_filename(excel_path: Path, product_name: str) -> str | None:
    """
    Extract version from file name.

    Supported examples:
        S2T_USL_TEST_v1.2.3.xlsx
        S2T_USL_TEST_v1.2.3_debug.xlsx
        S2T_USL_TEST_v1.2.3_diff.xlsx
        S2T_USL_TEST_v1.2.3_debug_diff.xlsx
    """
    filename = excel_path.name

    pattern = (
        rf"^S2T_USL_{re.escape(product_name.upper())}_v"
        rf"(?P<version>.+?)"
        rf"(?:_debug)?"
        rf"(?:_diff)?"
        rf"\.xlsx$"
    )

    match = re.match(pattern, filename, flags=re.IGNORECASE)
    if not match:
        return None

    version = match.group("version").strip()
    return version or None


def ensure_not_diff_excel(input_excel: Path) -> None:
    """
    Prevent PUT from using diff Excel files.
    """
    if input_excel.name.lower().endswith("_diff.xlsx"):
        raise ValueError(
            "Diff Excel cannot be used for PUT. "
            "Use the normal generated Excel file instead."
        )


def resolve_input_excel_path(
    config: dict,
    product_name: str,
    explicit_excel: str | None,
    explicit_version: str | None,
    branch: str | None = None,
) -> Path:
    """
    Resolve Excel file to use for PUT.
    """
    from main_config import resolve_excel_output_dir

    if explicit_excel:
        return Path(explicit_excel).expanduser().resolve()

    excel_dir = resolve_excel_output_dir(config)
    default_branch = str(config.get("default_branch", "master")).strip()
    resolved_branch = branch or default_branch
    debug_mode = is_debug_branch(resolved_branch, default_branch)

    if explicit_version is not None:
        return excel_dir / build_branch_excel_filename(product_name, explicit_version, debug_mode)

    if debug_mode:
        pattern = f"S2T_USL_{product_name.upper()}_v*_debug.xlsx"
    else:
        pattern = f"S2T_USL_{product_name.upper()}_v*.xlsx"

    candidates = sorted(
        [
            p for p in excel_dir.glob(pattern)
            if not p.name.lower().endswith("_diff.xlsx")
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise ValueError(
            f"Excel file not found for product '{product_name}'. "
            f"Expected file like: {pattern} in {excel_dir}"
        )

    return candidates[0]


def rename_excel_after_put(
    input_excel: Path,
    product_name: str,
    new_version: str,
    branch: str,
    default_branch: str,
    logger=None,
) -> None:
    """
    Rename Excel file after successful PUT if version changed.
    """
    debug_mode = is_debug_branch(branch, default_branch)
    expected_name = build_branch_excel_filename(product_name, new_version, debug_mode)
    new_path = input_excel.with_name(expected_name)

    if input_excel == new_path:
        return

    try:
        input_excel.rename(new_path)
        if logger:
            logger(f"Excel renamed: {new_path}")
    except Exception as exc:
        if logger:
            logger(f"Failed to rename Excel file: {exc}")