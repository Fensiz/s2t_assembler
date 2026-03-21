from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock

from s2t_tool.infrastructure.excel_writer import build_rich_diff, maybe_build_rich_diff
from s2t_tool.infrastructure.writer_style import append_csv_sheet
from s2t_tool.shared.csv_files import write_csv_rows


class ExcelDiffOutputTests(unittest.TestCase):
    def test_returns_rich_text_for_changed_value(self) -> None:
        result = build_rich_diff("before", "after")
        self.assertIsInstance(result, CellRichText)
        self.assertTrue(any(isinstance(part, TextBlock) for part in result))

    def test_returns_plain_text_when_values_are_equal(self) -> None:
        self.assertEqual(build_rich_diff("same", "same"), "same")

    def test_non_diff_mode_returns_new_text(self) -> None:
        self.assertEqual(maybe_build_rich_diff(False, "before", "after"), "after")

    def test_append_csv_sheet_highlights_changed_data_cells(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            current = Path(temp_dir) / "current.csv"
            old = Path(temp_dir) / "old.csv"
            write_csv_rows(current, ["value"], [["after"]])
            write_csv_rows(old, ["value"], [["before"]])

            wb = Workbook()
            wb.remove(wb.active)
            append_csv_sheet(
                wb=wb,
                title="Settings",
                csv_path=current,
                config={"global": {}},
                required=True,
                pre_transforms_sheet="Pre-transforms",
                joins_sheet="Joins",
                mappings_sheet="Mappings",
                diff_csv_path=old,
                maybe_build_rich_diff=maybe_build_rich_diff,
            )

            sheet = wb["Settings"]
            self.assertIsInstance(sheet["A2"].value, CellRichText)


if __name__ == "__main__":
    unittest.main()
