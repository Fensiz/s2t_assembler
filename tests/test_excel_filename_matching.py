from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from s2t_tool.domain.file_naming import resolve_input_excel_path
from s2t_tool.adapters.excel.artifacts import find_latest_excel_file


class ExcelFilenameMatchingTests(unittest.TestCase):
    def test_resolve_input_excel_path_is_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            excel_dir = Path(temp_dir)
            actual = excel_dir / "s2t_usl_demo_v2.0.XLSX"
            actual.write_text("stub", encoding="utf-8")

            resolved = resolve_input_excel_path(
                config={"excel_output_dir": str(excel_dir), "default_branch": "s2t/master"},
                product_name="demo",
                explicit_excel=None,
                explicit_version="2.0",
                branch="s2t/master",
            )

            self.assertEqual(resolved.resolve(), actual.resolve())

    def test_find_latest_excel_file_is_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            excel_dir = Path(temp_dir)
            first = excel_dir / "s2t_usl_demo_v1.0.xlsx"
            second = excel_dir / "S2T_USL_DEMO_v2.0.XLSX"
            first.write_text("1", encoding="utf-8")
            second.write_text("2", encoding="utf-8")

            latest = find_latest_excel_file(excel_dir, "demo", diff_mode=False)

            self.assertEqual(latest, second)

    def test_resolve_input_excel_path_does_not_mix_master_and_debug_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            excel_dir = Path(temp_dir)
            master_excel = excel_dir / "S2T_USL_DEMO_v2.0.xlsx"
            debug_excel = excel_dir / "S2T_USL_DEMO_v2.0_debug.xlsx"

            master_excel.write_text("master", encoding="utf-8")
            debug_excel.write_text("debug", encoding="utf-8")

            resolved_master = resolve_input_excel_path(
                config={"excel_output_dir": str(excel_dir), "default_branch": "s2t/master"},
                product_name="demo",
                explicit_excel=None,
                explicit_version=None,
                branch="s2t/master",
            )
            resolved_debug = resolve_input_excel_path(
                config={"excel_output_dir": str(excel_dir), "default_branch": "s2t/master"},
                product_name="demo",
                explicit_excel=None,
                explicit_version=None,
                branch="s2t/debug/master",
            )

            self.assertEqual(resolved_master.resolve(), master_excel.resolve())
            self.assertEqual(resolved_debug.resolve(), debug_excel.resolve())


if __name__ == "__main__":
    unittest.main()
