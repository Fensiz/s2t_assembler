from __future__ import annotations

from pathlib import Path

from openpyxl.worksheet.worksheet import Worksheet

from s2t_tool.adapters.excel.readers.common import sheet_rows
from s2t_tool.domain.schema import S2TSchema
from s2t_tool.shared.csv_files import write_csv_rows
from s2t_tool.shared.files import ensure_dir, write_json_file
from s2t_tool.shared.text import excel_to_repo_header, is_row_empty, normalize_cell


def export_change_history(output_dir: Path, schema: S2TSchema, sheet: Worksheet) -> Path:
    ensure_dir(output_dir)
    rows = sheet_rows(sheet)

    entries: list[dict[str, str | None]] = []
    for row in rows[1:]:
        values = [normalize_cell(v) for v in row[:5]]
        while len(values) < 5:
            values.append("")
        if is_row_empty(values):
            continue

        entries.append(
            {
                "author": values[0] or None,
                "date": values[1] or None,
                "version": values[2] or None,
                "description": values[3] or None,
                "jira_ticket": values[4] or None,
            }
        )

    path = output_dir / schema.change_history_json
    write_json_file(path, entries)
    return path


def export_source_lg(output_dir: Path, schema: S2TSchema, sheet: Worksheet) -> Path:
    ensure_dir(output_dir)
    rows = sheet_rows(sheet)
    if not rows:
        raise ValueError("Source LG sheet is empty")

    header_map: dict[int, str] = {}
    source_headers = list(schema.source_lg_headers)
    for idx, name in enumerate(rows[0]):
        normalized = excel_to_repo_header(str(name or ""))
        if normalized in source_headers:
            header_map[idx] = normalized

    missing = set(source_headers) - set(header_map.values())
    if missing:
        raise ValueError(f"Missing columns in Source LG: {sorted(missing)}")

    output_rows: list[list[str]] = []
    for row in rows[1:]:
        values = {name: "" for name in source_headers}
        for idx, repo_name in header_map.items():
            if idx < len(row):
                values[repo_name] = normalize_cell(row[idx])
        if is_row_empty(list(values.values())):
            continue
        output_rows.append([values[h] for h in source_headers])

    path = output_dir / schema.source_lg_csv
    write_csv_rows(path, source_headers, output_rows)
    return path


def export_targets(output_dir: Path, schema: S2TSchema, sheet: Worksheet) -> Path:
    ensure_dir(output_dir)
    rows = sheet_rows(sheet)

    output_rows: list[list[str]] = []
    for row in rows[1:]:
        values = [normalize_cell(v) for v in row[:2]]
        while len(values) < 2:
            values.append("")
        if is_row_empty(values):
            continue
        output_rows.append(values)

    path = output_dir / schema.targets_csv
    write_csv_rows(path, list(schema.targets_headers), output_rows)
    return path


def export_simple_csv_sheet(
    output_dir: Path,
    output_name: str,
    headers: list[str],
    sheet: Worksheet | None,
) -> Path | None:
    ensure_dir(output_dir)
    if sheet is None:
        return None

    rows = sheet_rows(sheet)
    output_rows: list[list[str]] = []

    for row in rows[1:]:
        values = [normalize_cell(v) for v in row[:len(headers)]]
        while len(values) < len(headers):
            values.append("")
        if is_row_empty(values):
            continue
        output_rows.append(values)

    path = output_dir / output_name
    write_csv_rows(path, headers, output_rows)
    return path
