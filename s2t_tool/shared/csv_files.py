from __future__ import annotations

import csv
from pathlib import Path

from s2t_tool.shared.files import ensure_dir


def write_csv_rows(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, delimiter=";")
        writer.writerow(headers)
        writer.writerows(rows)


def read_csv_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        return [], []

    with path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file, delimiter=";")
        rows = list(reader)

    if not rows:
        return [], []

    return rows[0], rows[1:]

