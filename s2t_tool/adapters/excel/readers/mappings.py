from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from openpyxl.worksheet.worksheet import Worksheet

from s2t_tool.adapters.excel.readers.common import sheet_rows
from s2t_tool.domain.schema import S2TSchema
from s2t_tool.shared.csv_files import write_csv_rows
from s2t_tool.shared.files import ensure_dir, write_json_file
from s2t_tool.shared.text import is_row_empty, normalize_cell, slugify_dir_name


def export_mappings(output_dir: Path, schema: S2TSchema, sheet: Worksheet) -> tuple[Path, Path]:
    ensure_dir(output_dir)
    rows = sheet_rows(sheet)
    if len(rows) < 2:
        raise ValueError("Mappings sheet must contain header and data rows")

    joins_root = output_dir / schema.joins_dir
    ensure_dir(joins_root)

    grouped_rows: dict[tuple[str, str], list[dict[str, str]]] = {}
    attribute_names_by_table: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for row in rows[2:]:
        values = [normalize_cell(v) for v in row[:7]]
        while len(values) < 7:
            values.append("")
        if is_row_empty(values):
            continue

        load_code, table_name, attribute_code, attribute_name, mapping_algorithm, additional_join, settings = values

        if not load_code or not table_name or not attribute_code:
            raise ValueError("Mappings row must contain load_code, table_name, attribute_code")

        grouped_rows.setdefault((table_name, load_code), []).append(
            {
                "attribute_code": attribute_code,
                "mapping_algorithm": mapping_algorithm,
                "additional_join": additional_join,
                "settings": settings,
            }
        )

        if attribute_name:
            attribute_names_by_table[table_name][attribute_code].append(attribute_name)

    for (table_name, load_code), mapping_rows in grouped_rows.items():
        mapping_dir = joins_root / slugify_dir_name(table_name) / slugify_dir_name(load_code)
        ensure_dir(mapping_dir)

        csv_rows: list[list[str]] = []
        extra_payload: dict[str, dict[str, str]] = {}

        for item in mapping_rows:
            csv_rows.append([item["attribute_code"], item["mapping_algorithm"]])

            extra: dict[str, str] = {}
            if item["additional_join"]:
                extra["additional_join"] = item["additional_join"]
            if item["settings"]:
                extra["settings"] = item["settings"]

            if extra:
                extra_payload[item["attribute_code"]] = extra

        write_csv_rows(
            mapping_dir / schema.mappings_csv,
            ["attribute_code", "mapping_algorithm"],
            csv_rows,
        )

        if extra_payload:
            write_json_file(mapping_dir / schema.mappings_extra_json, extra_payload)

    resolved_table_names: dict[str, dict[str, str]] = {}
    for table_name, attrs in attribute_names_by_table.items():
        resolved_table_names[table_name] = {}
        for attribute_code, names in attrs.items():
            unique_names = {n for n in names if n}
            if len(unique_names) > 1:
                raise ValueError(
                    f"Conflicting attribute_name inside table '{table_name}' "
                    f"for attribute_code '{attribute_code}': {sorted(unique_names)}"
                )
            if unique_names:
                resolved_table_names[table_name][attribute_code] = next(iter(unique_names))

    attribute_to_table_values: dict[str, dict[str, str]] = defaultdict(dict)
    for table_name, attrs in resolved_table_names.items():
        for attribute_code, attribute_name in attrs.items():
            attribute_to_table_values[attribute_code][table_name] = attribute_name

    common_names: dict[str, str] = {}
    table_overrides: dict[str, dict[str, str]] = {}

    for attribute_code, table_values in attribute_to_table_values.items():
        unique_values = set(table_values.values())
        if len(unique_values) == 1:
            common_names[attribute_code] = next(iter(unique_values))
        else:
            for table_name, attribute_name in table_values.items():
                table_overrides.setdefault(table_name, {})[attribute_code] = attribute_name

    attribute_names_payload = {
        "common": dict(sorted(common_names.items())),
        "tables": {
            table_name: dict(sorted(attrs.items()))
            for table_name, attrs in sorted(table_overrides.items())
        },
    }

    attribute_names_path = output_dir / schema.attribute_names_json
    write_json_file(attribute_names_path, attribute_names_payload)
    return joins_root, attribute_names_path
