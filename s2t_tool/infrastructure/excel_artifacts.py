from __future__ import annotations

from pathlib import Path


def find_latest_excel_file(
    excel_dir: Path,
    product_name: str,
    diff_mode: bool,
) -> Path | None:
    product_upper = product_name.upper()

    if diff_mode:
        patterns = [
            f"S2T_USL_{product_upper}_v*_debug_diff.xlsx",
            f"S2T_USL_{product_upper}_v*_diff.xlsx",
        ]
    else:
        patterns = [
            f"S2T_USL_{product_upper}_v*_commit_*.xlsx",
            f"S2T_USL_{product_upper}_v*_debug.xlsx",
            f"S2T_USL_{product_upper}_v*.xlsx",
        ]

    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(excel_dir.glob(pattern))

    if not diff_mode:
        candidates = [path for path in candidates if not path.name.lower().endswith("_diff.xlsx")]

    candidates = sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None
