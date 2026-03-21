from __future__ import annotations

import unittest

from s2t_tool.domain.branching import normalize_branch_name, resolve_branch
from s2t_tool.domain.file_naming import parse_version_from_excel_filename
from s2t_tool.domain.versioning import bump_version, resolve_put_version


class MainLogicTests(unittest.TestCase):
    def test_branch_namespace_is_applied(self) -> None:
        self.assertEqual(normalize_branch_name("test", "s2t/master"), "s2t/test")
        self.assertEqual(normalize_branch_name("debug/dev", "s2t/master"), "s2t/debug/dev")

    def test_branch_rejects_foreign_namespace(self) -> None:
        with self.assertRaises(ValueError):
            normalize_branch_name("feature/test", "s2t/master")

    def test_resolve_branch_defaults_to_config_default(self) -> None:
        self.assertEqual(resolve_branch({"default_branch": "s2t/master"}, None), "s2t/master")

    def test_parse_version_from_filename_supports_debug_and_diff_suffixes(self) -> None:
        from pathlib import Path

        self.assertEqual(
            parse_version_from_excel_filename(Path("S2T_USL_TEST_v1.2.3_debug_diff.xlsx"), "test"),
            "1.2.3",
        )

    def test_bump_version_increments_last_component(self) -> None:
        self.assertEqual(bump_version("1.2.3.4"), "1.2.3.5")

    def test_resolve_put_version_prefers_filename_then_bumps(self) -> None:
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            version_file = Path(temp_dir) / "version.json"
            version_file.write_text('{"version":"9.9.9"}', encoding="utf-8")

            resolved = resolve_put_version(
                version_arg=None,
                input_excel=Path("S2T_USL_TEST_v1.0.0.xlsx"),
                product_name="test",
                version_path=version_file,
            )

            self.assertEqual(resolved, "1.0.1")


if __name__ == "__main__":
    unittest.main()
