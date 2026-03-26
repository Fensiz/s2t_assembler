from __future__ import annotations

from pathlib import Path

from openpyxl.worksheet.worksheet import Worksheet

from s2t_tool.adapters.excel.readers.common import sheet_rows
from s2t_tool.domain.schema import S2TSchema
from s2t_tool.shared.files import ensure_dir, write_json_file, write_text_file
from s2t_tool.shared.sql_format import maybe_format_hive_sql
from s2t_tool.shared.text import is_row_empty, normalize_cell, slugify_dir_name, split_lines


def export_pre_transforms(
    output_dir: Path,
    schema: S2TSchema,
    sheet: Worksheet,
    format_sql: bool,
) -> Path:
    ensure_dir(output_dir)
    rows = sheet_rows(sheet)

    if len(rows) < 2:
        raise ValueError("Pre-transforms sheet must contain at least double header")

    root = output_dir / schema.pre_transforms_dir
    ensure_dir(root)

    if len(rows) == 2:
        return root

    for row in rows[2:]:
        values = [normalize_cell(v) for v in row[:5]]
        while len(values) < 5:
            values.append("")
        if is_row_empty(values):
            continue

        target_table, source_tables_raw, transformation_sql, comments, settings_sql = values
        if not target_table:
            raise ValueError("Pre-transforms row has empty target table")

        target_dir = root / slugify_dir_name(target_table)
        ensure_dir(target_dir)

        payload = {
            "target_table": target_table,
            "source_tables": split_lines(source_tables_raw),
            "comments": comments or None,
        }

        write_json_file(target_dir / "pre-transform.json", payload)

        if transformation_sql:
            write_text_file(
                target_dir / "preliminary_transformation.sql",
                maybe_format_hive_sql(transformation_sql, format_sql),
            )
        if settings_sql:
            write_text_file(
                target_dir / "settings.sql",
                maybe_format_hive_sql(settings_sql, format_sql),
            )

    return root
