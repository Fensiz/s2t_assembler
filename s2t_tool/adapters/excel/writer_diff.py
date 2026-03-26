from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Any

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont

from s2t_tool.adapters.excel.writer_style import append_csv_sheet, create_sheet, finalize_sheet_style
from s2t_tool.shared.files import read_json_file


RED_FONT = InlineFont(color="FFFF0000", strike=True)
GREEN_FONT = InlineFont(color="FF008000")


def build_rich_diff(old_text: str | None, new_text: str | None) -> CellRichText | str:
    old_value = "" if old_text is None else str(old_text)
    new_value = "" if new_text is None else str(new_text)

    if old_value == new_value:
        return new_value

    old_tokens = _diff_tokens(old_value)
    new_tokens = _diff_tokens(new_value)
    matcher = SequenceMatcher(a=old_tokens, b=new_tokens)
    rich = CellRichText()

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_chunk = "".join(old_tokens[i1:i2])
        new_chunk = "".join(new_tokens[j1:j2])

        if tag == "equal":
            if old_chunk:
                rich.append(old_chunk)
        elif tag == "delete":
            if old_chunk:
                rich.append(TextBlock(RED_FONT, old_chunk))
        elif tag == "insert":
            if new_chunk:
                rich.append(TextBlock(GREEN_FONT, new_chunk))
        elif tag == "replace":
            if old_chunk:
                rich.append(TextBlock(RED_FONT, old_chunk))
            if new_chunk:
                rich.append(TextBlock(GREEN_FONT, new_chunk))

    return rich


def maybe_build_rich_diff(
    diff_enabled: bool,
    old_value: str | None,
    new_value: str | None,
) -> str | CellRichText:
    new_text = "" if new_value is None else str(new_value)
    if not diff_enabled:
        return new_text
    return build_rich_diff(old_value, new_text)


def normalize_key_part(value: object) -> str:
    return "" if value is None else str(value)


def join_row_key(table_name: str, load_code: str) -> tuple[str, str]:
    return (normalize_key_part(table_name), normalize_key_part(load_code))


def pre_transform_row_key(target_table: str) -> str:
    return normalize_key_part(target_table)


def mapping_row_key(load_code: str, table_name: str, attribute_code: str) -> tuple[str, str, str]:
    return (
        normalize_key_part(load_code),
        normalize_key_part(table_name),
        normalize_key_part(attribute_code),
    )


def build_change_history_sheet(
    wb: Workbook,
    repo_dir: Path,
    config: dict[str, Any],
    *,
    change_history_json: str,
    change_history_sheet: str,
    pre_transforms_sheet: str,
    joins_sheet: str,
    mappings_sheet: str,
    diff_repo_dir: str | None = None,
) -> None:
    path = repo_dir / change_history_json
    entries = read_json_file(path, default=[])
    diff_enabled = diff_repo_dir is not None
    old_entries: list[dict[str, Any]] = []
    if diff_enabled:
        old_entries = read_json_file(Path(diff_repo_dir) / change_history_json, default=[]) or []
    sheet = create_sheet(wb, change_history_sheet)

    sheet.append(["Author", "Date", "Version", "Description", "Jira ticket"])

    for row_idx, entry in enumerate(entries):
        old_entry = old_entries[row_idx] if row_idx < len(old_entries) else {}
        sheet.append(
            [
                maybe_build_rich_diff(diff_enabled, old_entry.get("author"), entry.get("author")),
                maybe_build_rich_diff(diff_enabled, old_entry.get("date"), entry.get("date")),
                maybe_build_rich_diff(diff_enabled, old_entry.get("version"), entry.get("version")),
                maybe_build_rich_diff(diff_enabled, old_entry.get("description"), entry.get("description")),
                maybe_build_rich_diff(diff_enabled, old_entry.get("jira_ticket"), entry.get("jira_ticket")),
            ]
        )

    finalize_sheet_style(sheet, config, change_history_sheet, pre_transforms_sheet, joins_sheet, mappings_sheet)


def append_standard_csv_sheet(
    wb: Workbook,
    sheet_name: str,
    csv_name: str,
    repo_dir: Path,
    config: dict[str, Any],
    *,
    pre_transforms_sheet: str,
    joins_sheet: str,
    mappings_sheet: str,
    diff_repo_dir: str | None = None,
) -> None:
    append_csv_sheet(
        wb,
        sheet_name,
        repo_dir / csv_name,
        config,
        True,
        pre_transforms_sheet,
        joins_sheet,
        mappings_sheet,
        diff_csv_path=(Path(diff_repo_dir) / csv_name) if diff_repo_dir else None,
        maybe_build_rich_diff=maybe_build_rich_diff,
    )


def _diff_tokens(value: str) -> list[str]:
    if "\n" in value:
        return value.splitlines(keepends=True)

    token_re = re.compile(r"'[^']*'|\s+|[(),]|[^\s(),]+")
    tokens = token_re.findall(value)
    return tokens or [value]
