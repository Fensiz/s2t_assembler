from __future__ import annotations

from pathlib import Path


def find_latest_excel_file(excel_dir: Path, product_name: str, diff_mode: bool) -> Path | None:
    if not excel_dir.exists():
        return None

    prefix = f"s2t_usl_{product_name}_".lower()
    suffix = "_diff.xlsx" if diff_mode else ".xlsx"

    candidates = [
        path
        for path in excel_dir.iterdir()
        if path.is_file()
        and path.name.lower().startswith(prefix)
        and path.name.lower().endswith(suffix)
    ]
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)
