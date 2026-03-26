from __future__ import annotations

from typing import Any

from openpyxl.worksheet.worksheet import Worksheet


def sheet_rows(sheet: Worksheet) -> list[tuple[Any, ...]]:
    return list(sheet.iter_rows(values_only=True))
