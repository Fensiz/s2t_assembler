from __future__ import annotations

import re
from pathlib import Path

from s2t_tool.domain.branching import is_debug_branch
from s2t_tool.shared.constants import Logger


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


def build_commit_excel_filename(product_name: str, version: str, commit_ref: str) -> str:
    short_commit = commit_ref[:8]
    return f"S2T_USL_{product_name.upper()}_v{version}_commit_{short_commit}.xlsx"


def parse_version_from_excel_filename(excel_path: Path, product_name: str) -> str | None:
    """
    Extract version from file name.

    Supported examples:
        S2T_USL_TEST_v1.2.3.xlsx
        S2T_USL_TEST_v1.2.3_debug.xlsx
        S2T_USL_TEST_v1.2.3_diff.xlsx
        S2T_USL_TEST_v1.2.3_debug_diff.xlsx
        S2T_USL_TEST_v1.2.3_commit_c220991.xlsx
    """
    filename = excel_path.name

    pattern = (
        rf"^S2T_USL_{re.escape(product_name.upper())}_v"
        rf"(?P<version>.+?)"
        rf"(?:_debug)?"
        rf"(?:_commit_[0-9a-fA-F]{{7,8}})?"
        rf"(?:_diff)?"
        rf"\.xlsx$"
    )

    match = re.match(pattern, filename, flags=re.IGNORECASE)
    if not match:
        return None

    version = match.group("version").strip()
    return version or None


def ensure_put_compatible_excel(input_excel: Path) -> None:
    """
    Prevent PUT from using unsupported generated Excel files.
    """
    lower_name = input_excel.name.lower()
    if lower_name.endswith("_diff.xlsx"):
        raise ValueError(
            "Diff Excel cannot be used for PUT. "
            "Use the normal generated Excel file instead."
        )
    if "_commit_" in lower_name:
        raise ValueError(
            "Excel generated from a commit hash cannot be used for PUT. "
            "Run GET for a branch and use that Excel file instead."
        )


def find_excel_candidates(excel_dir: Path, patterns: list[str]) -> list[Path]:
    regexes = [
        re.compile("^" + pattern.replace(".", r"\.").replace("*", ".*") + "$", flags=re.IGNORECASE)
        for pattern in patterns
    ]

    candidates: list[Path] = []
    for path in excel_dir.iterdir():
        if not path.is_file():
            continue
        if any(regex.match(path.name) for regex in regexes):
            candidates.append(path)
    return candidates


def is_debug_excel_filename(path: Path) -> bool:
    lower_name = path.name.lower()
    return lower_name.endswith("_debug.xlsx") or lower_name.endswith("_debug_diff.xlsx")


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
    from s2t_tool.adapters.config.loader import resolve_excel_output_dir

    if explicit_excel:
        return Path(explicit_excel).expanduser().resolve()

    excel_dir = resolve_excel_output_dir(config)
    default_branch = str(config.get("default_branch", "master")).strip()
    resolved_branch = branch or default_branch
    debug_mode = is_debug_branch(resolved_branch, default_branch)

    if explicit_version is not None:
        expected_name = build_branch_excel_filename(product_name, explicit_version, debug_mode)
        candidates = find_excel_candidates(excel_dir, [expected_name])
        if candidates:
            return candidates[0]
        return excel_dir / expected_name

    if debug_mode:
        pattern = f"S2T_USL_{product_name.upper()}_v*_debug.xlsx"
    else:
        pattern = f"S2T_USL_{product_name.upper()}_v*.xlsx"

    candidates = sorted(
        [
            p for p in find_excel_candidates(excel_dir, [pattern])
            if not p.name.lower().endswith("_diff.xlsx")
            and "_commit_" not in p.name.lower()
            and is_debug_excel_filename(p) == debug_mode
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
    logger: Logger | None = None,
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
