from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from s2t_tool.infrastructure.excel_reader import ExcelRepoReader
from s2t_tool.shared.sql_format import format_hive_sql


class SqlFormatTests(unittest.TestCase):
    def test_format_hive_sql_uppercases_keywords_and_splits_lines(self) -> None:
        sql = "select a, b from table_x where x in ('a','b') and y = 1"
        formatted = format_hive_sql(sql)
        self.assertIn("SELECT", formatted)
        self.assertIn("\nFROM", formatted)
        self.assertIn("\nWHERE", formatted)
        self.assertIn("\n    AND", formatted)

    def test_excel_reader_formats_join_sql_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            excel_path = Path(temp_dir) / "input.xlsx"
            output_dir = Path(temp_dir) / "repo"

            wb = Workbook()
            joins = wb.active
            joins.title = "Joins"
            joins.append(["", "TARGET", "", "", "", "SOURCE"])
            joins.append([
                "Load code", "Table name", "Description", "Table code(s)",
                "Table codes to track delta", "Source tables join", "Load code params",
                "Settings table join", "History rule", "Business history dates",
            ])
            joins.append([
                "main", "registry", "", "", "",
                "select a, b from t where x = 1 and y = 2",
                "", "select c from t2 where z = 3", "", "",
            ])
            wb.save(excel_path)

            ExcelRepoReader(excel_path=excel_path, output_dir=output_dir, format_sql=True).export_joins()

            source_sql = (output_dir / "joins" / "registry" / "main" / "source_tables_join.sql").read_text(encoding="utf-8")
            self.assertIn("SELECT", source_sql)
            self.assertIn("\nFROM", source_sql)
            self.assertIn("\nWHERE", source_sql)


if __name__ == "__main__":
    unittest.main()
