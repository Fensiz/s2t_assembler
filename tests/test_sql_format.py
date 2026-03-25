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

    def test_format_hive_sql_splits_top_level_and_or_but_keeps_nested_group_inline(self) -> None:
        sql = "SELECT * FROM t WHERE a = 1 AND b = 2 AND (c = 3 OR d = 4) OR e = 5"
        formatted = format_hive_sql(sql)
        self.assertIn("\nWHERE a = 1", formatted)
        self.assertIn("\n    AND b = 2", formatted)
        self.assertIn("\n    AND (c = 3 OR d = 4)", formatted)
        self.assertIn("\n    OR e = 5", formatted)

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
        self.assertIn("\n        AND e <> '22'\n) t", formatted)
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
        self.assertIn("\n) t", formatted)

    def test_format_hive_sql_keeps_numbers_inside_in_list(self) -> None:
        sql = "SELECT * FROM t WHERE attr IN (16625, 18888)"
        formatted = format_hive_sql(sql)
        self.assertIn("WHERE attr IN (16625, 18888)", formatted)

    def test_format_hive_sql_keeps_comment_on_its_line(self) -> None:
        sql = "SELECT a -- comment\nFROM t WHERE x = 1"
        formatted = format_hive_sql(sql)
        self.assertIn("a -- comment", formatted)
        self.assertIn("\nFROM t", formatted)

    def test_format_hive_sql_keeps_inline_select_comment_after_comma(self) -> None:
        sql = "select a as d, --comment\n    c\nfrom e"
        formatted = format_hive_sql(sql)
        self.assertIn("a AS d, --comment", formatted)
        self.assertIn("\n    c", formatted)
        self.assertIn("\nFROM e", formatted)

    def test_format_hive_sql_pulls_leading_commas_to_previous_select_items(self) -> None:
        sql = "select\n a as a --xxxx\n , b --sss\n, c ---ss"
        formatted = format_hive_sql(sql)
        self.assertIn("\n    a AS a, --xxxx", formatted)
        self.assertIn("\n    b, --sss", formatted)
        self.assertIn("\n    c ---ss", formatted)

    def test_format_hive_sql_splits_multiple_ctes(self) -> None:
        sql = "WITH a AS (SELECT 1), b AS (SELECT 2) SELECT * FROM z"
        formatted = format_hive_sql(sql)
        self.assertIn("WITH\na AS (", formatted)
        self.assertIn("\n),\nb AS (", formatted)
        self.assertIn("\nSELECT\n    *\nFROM z", formatted)

    def test_format_hive_sql_keeps_hivevar_set_syntax(self) -> None:
        sql = "set hivevar:F_ASD = '222', '2222'; set x = 1;"
        formatted = format_hive_sql(sql)
        self.assertIn("set hivevar:F_ASD = '222', '2222';", formatted)
        self.assertIn("\nset x = 1;", formatted)

    def test_format_hive_sql_aligns_closing_paren_with_join(self) -> None:
        sql = "SELECT * FROM x JOIN y ON a IN (SELECT id FROM z) WHERE q = 1"
        formatted = format_hive_sql(sql)
        self.assertIn("JOIN y", formatted)
        self.assertIn("\n    ON a IN (", formatted)
        self.assertIn("\n    )", formatted)

    def test_format_hive_sql_aligns_closing_paren_with_left_join(self) -> None:
        sql = "SELECT * FROM x LEFT JOIN (SELECT id FROM a WHERE q = 1) j ON x.id = j.id"
        formatted = format_hive_sql(sql)
        self.assertIn("\nLEFT JOIN (", formatted)
        self.assertIn("\n    WHERE q = 1", formatted)
        self.assertIn("\n) j", formatted)
        self.assertIn("\n    ON x.id = j.id", formatted)

    def test_format_hive_sql_aligns_nested_left_join_subquery_inside_with(self) -> None:
        sql = (
            "WITH op AS ("
            "SELECT h.a AS id, o.b AS b_oper_num, o.c, o.e, d.g "
            "FROM z h "
            "JOIN x t ON h.f = t.f "
            "JOIN c o ON cast(t.y as string) = o.u "
            "LEFT JOIN (SELECT u, y FROM v WHERE a = '1') d ON d.w = o.w "
            "WHERE a in (1, 2)"
            "),"
        )
        formatted = format_hive_sql(sql)
        self.assertIn("\n    LEFT JOIN (", formatted)
        self.assertIn("\n        WHERE a = '1'", formatted)
        self.assertIn("\n    ) d", formatted)

    def test_format_hive_sql_splits_and_in_outer_where_after_subquery(self) -> None:
        sql = (
            "WITH TRADE_IDS AS ("
            "SELECT d, s AS s, d, da "
            "FROM ("
            "SELECT ds, TRIM(s) AS s, b, e, "
            "ROW_NUMBER() OVER (PARTITION BY d ORDER BY da DESC, b DESC) AS rn "
            "FROM s WHERE d = '2'"
            ") t "
            "WHERE rn = 1 AND s IS NOT NULL AND s <> '0'"
            "),"
        )
        formatted = format_hive_sql(sql)
        self.assertIn("\n    WHERE rn = 1", formatted)
        self.assertIn("\n        AND s IS NOT NULL", formatted)
        self.assertIn("\n        AND s <> '0'", formatted)


if __name__ == "__main__":
    unittest.main()
