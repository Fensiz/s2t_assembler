from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook

from s2t_tool.adapters.excel.writer_diff import (
    append_standard_csv_sheet,
    build_change_history_sheet as build_change_history_sheet_section,
)


def build_change_history_sheet(
    wb: Workbook,
    repo_dir: Path,
    config: dict[str, Any],
    change_history_json: str,
    change_history_sheet: str,
    pre_transforms_sheet: str,
    joins_sheet: str,
    mappings_sheet: str,
    diff_repo_dir: str | None = None,
) -> None:
    build_change_history_sheet_section(
        wb=wb,
        repo_dir=repo_dir,
        config=config,
        change_history_json=change_history_json,
        change_history_sheet=change_history_sheet,
        pre_transforms_sheet=pre_transforms_sheet,
        joins_sheet=joins_sheet,
        mappings_sheet=mappings_sheet,
        diff_repo_dir=diff_repo_dir,
    )


def build_source_lg_sheet(
    wb: Workbook,
    repo_dir: Path,
    config: dict[str, Any],
    source_lg_sheet: str,
    source_lg_csv: str,
    pre_transforms_sheet: str,
    joins_sheet: str,
    mappings_sheet: str,
    diff_repo_dir: str | None = None,
) -> None:
    append_standard_csv_sheet(
        wb=wb,
        sheet_name=source_lg_sheet,
        csv_name=source_lg_csv,
        repo_dir=repo_dir,
        config=config,
        pre_transforms_sheet=pre_transforms_sheet,
        joins_sheet=joins_sheet,
        mappings_sheet=mappings_sheet,
        diff_repo_dir=diff_repo_dir,
    )


def build_targets_sheet(
    wb: Workbook,
    repo_dir: Path,
    config: dict[str, Any],
    targets_sheet: str,
    targets_csv: str,
    pre_transforms_sheet: str,
    joins_sheet: str,
    mappings_sheet: str,
    diff_repo_dir: str | None = None,
) -> None:
    append_standard_csv_sheet(
        wb=wb,
        sheet_name=targets_sheet,
        csv_name=targets_csv,
        repo_dir=repo_dir,
        config=config,
        pre_transforms_sheet=pre_transforms_sheet,
        joins_sheet=joins_sheet,
        mappings_sheet=mappings_sheet,
        diff_repo_dir=diff_repo_dir,
    )
