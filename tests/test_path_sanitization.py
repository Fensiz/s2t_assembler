from __future__ import annotations

import unittest

from s2t_tool.shared.text import slugify_dir_name


class PathSanitizationTests(unittest.TestCase):
    def test_replaces_newlines_and_collapses_whitespace(self) -> None:
        self.assertEqual(slugify_dir_name("load\n\ncode"), "load code")

    def test_removes_windows_invalid_characters(self) -> None:
        self.assertEqual(slugify_dir_name('name:with*bad|chars?'), "name_with_bad_chars_")

    def test_strips_trailing_windows_invalid_suffixes(self) -> None:
        self.assertEqual(slugify_dir_name("folder. "), "folder")

    def test_protects_reserved_windows_names(self) -> None:
        self.assertEqual(slugify_dir_name("CON"), "_CON")


if __name__ == "__main__":
    unittest.main()
