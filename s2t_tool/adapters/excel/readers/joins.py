from __future__ import annotations

from pathlib import Path

from openpyxl.worksheet.worksheet import Worksheet

from s2t_tool.adapters.excel.readers.common import sheet_rows
from s2t_tool.domain.schema import S2TSchema
from s2t_tool.shared.files import ensure_dir, write_json_file, write_text_file
from s2t_tool.shared.sql_format import maybe_format_hive_sql
from s2t_tool.shared.text import is_row_empty, normalize_cell, slugify_dir_name, split_lines


def export_joins(
    output_dir: Path,
    schema: S2TSchema,
    sheet: Worksheet,
    format_sql: bool,
) -> Path:
    ensure_dir(output_dir)
    rows = sheet_rows(sheet)
    if len(rows) < 3:
        raise ValueError("Joins must contain double header and data rows")

    root = output_dir / schema.joins_dir
    ensure_dir(root)

    for row in rows[2:]:
        values = [normalize_cell(v) for v in row[:10]]
        while len(values) < 10:
            values.append("")
        if is_row_empty(values):
            continue

        (
            load_code,
            table_name,
            description,
            table_codes_raw,
            delta_codes_raw,
            source_tables_join_sql,
            load_code_params_raw,
            settings_table_join_sql,
            history_rule,
            business_history_dates,
        ) = values

        if not load_code or not table_name:
            raise ValueError("Joins row must contain table_name and load_code")

        join_dir = root / slugify_dir_name(table_name) / slugify_dir_name(load_code)
        ensure_dir(join_dir)

        payload = {
            "description": description or None,
            "table_codes": split_lines(table_codes_raw),
            "table_codes_to_track_delta": split_lines(delta_codes_raw),
            "load_code_params": split_lines(load_code_params_raw),
            "history_rule": history_rule or None,
            "business_history_dates": business_history_dates or None,
        }
        payload = {k: v for k, v in payload.items() if v not in (None, [], "")}
        write_json_file(join_dir / "join.json", payload)

        if source_tables_join_sql:
            write_text_file(
                join_dir / "source_tables_join.sql",
                maybe_format_hive_sql(source_tables_join_sql, format_sql),
            )
        if settings_table_join_sql:
            write_text_file(
                join_dir / "settings_table_join.sql",
                maybe_format_hive_sql(settings_table_join_sql, format_sql),
            )

    return root
