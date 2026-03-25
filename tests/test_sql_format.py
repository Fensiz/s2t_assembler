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

    def test_format_hive_sql_formats_with_subquery(self) -> None:
        sql = (
            "WITH any (SELECT a FROM b JOIN c ON b.x = c.x "
            "WHERE s IN (1, 2) AND e <> '22') t "
            "SELECT * FROM tdeal123567"
        )
        formatted = format_hive_sql(sql)
        self.assertIn("WITH\nany (", formatted)
        self.assertIn("\n    SELECT", formatted)
        self.assertIn("\n        a", formatted)
        self.assertIn("\n    JOIN c", formatted)
        self.assertIn("\n        ON b.x = c.x", formatted)
        self.assertIn("\n    WHERE s IN (1, 2)", formatted)
        self.assertIn("\n        AND e <> '22'\n    ) t", formatted)
        self.assertIn("\nSELECT\n    *\nFROM tdeal123567", formatted)

    def test_format_hive_sql_formats_window_function_and_select_list(self) -> None:
        sql = (
            "WITH any (SELECT a, TRIM(s) AS s, "
            "ROW_NUMBER() OVER (PARTITION BY SID ORDER BY NAME DESC) AS rn "
            "FROM b JOIN c ON b.x = c.x WHERE s IN (1, 2) AND e <> '22') t "
            "SELECT * FROM tdeal123567"
        )
        formatted = format_hive_sql(sql)
        self.assertIn("\n        a,", formatted)
        self.assertIn("\n        TRIM(s) AS s,", formatted)
        self.assertIn("\n        ROW_NUMBER() OVER (", formatted)
        self.assertIn("\n            PARTITION BY SID", formatted)
        self.assertIn("\n            ORDER BY NAME DESC", formatted)
        self.assertIn("\n        ) AS rn", formatted)
        self.assertIn("\n    ) t", formatted)

    def test_format_hive_sql_keeps_numbers_inside_in_list(self) -> None:
        sql = "SELECT * FROM t WHERE attr IN (16625, 18888)"
        formatted = format_hive_sql(sql)
        self.assertIn("WHERE attr IN (16625, 18888)", formatted)

    def test_format_hive_sql_keeps_comment_on_its_line(self) -> None:
        sql = "SELECT a -- comment\nFROM t WHERE x = 1"
        formatted = format_hive_sql(sql)
        self.assertIn("a -- comment", formatted)
        self.assertIn("\nFROM t", formatted)

    def test_format_hive_sql_splits_multiple_ctes(self) -> None:
        sql = "WITH a AS (SELECT 1), b AS (SELECT 2) SELECT * FROM z"
        formatted = format_hive_sql(sql)
        self.assertIn("WITH\na AS (", formatted)
        self.assertIn("\n    ),\nb AS (", formatted)
        self.assertIn("\nSELECT\n    *\nFROM z", formatted)


if __name__ == "__main__":
    unittest.main()
