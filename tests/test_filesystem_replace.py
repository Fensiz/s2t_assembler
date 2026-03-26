from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from s2t_tool.adapters.git.repository import replace_directory_contents


class ReplaceDirectoryContentsTests(unittest.TestCase):
    def test_replaces_contents_and_removes_stale_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            replacement = root / "replacement"

            (target / "nested").mkdir(parents=True)
            (target / "nested" / "old.txt").write_text("old", encoding="utf-8")
            (target / "keep.json").write_text("legacy", encoding="utf-8")

            replacement.mkdir()
            (replacement / "new.txt").write_text("new", encoding="utf-8")

            replace_directory_contents(target, replacement)

            self.assertFalse((target / "nested").exists())
            self.assertFalse((target / "keep.json").exists())
            self.assertEqual((target / "new.txt").read_text(encoding="utf-8"), "new")

    def test_preserves_selected_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            replacement = root / "replacement"

            (target / ".git").mkdir(parents=True)
            (target / ".git" / "config").write_text("git", encoding="utf-8")
            (target / "stale.txt").write_text("stale", encoding="utf-8")

            replacement.mkdir()
            (replacement / "fresh.txt").write_text("fresh", encoding="utf-8")

            replace_directory_contents(target, replacement, preserved_names={".git"})

            self.assertTrue((target / ".git" / "config").exists())
            self.assertFalse((target / "stale.txt").exists())
            self.assertEqual((target / "fresh.txt").read_text(encoding="utf-8"), "fresh")

    def test_restores_original_contents_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            replacement = root / "replacement"

            target.mkdir()
            (target / "old.txt").write_text("old", encoding="utf-8")

            replacement.mkdir()
            (replacement / "new.txt").write_text("new", encoding="utf-8")

            original_replace = __import__("os").replace

            def failing_replace(src, dst):
                src_path = Path(src)
                dst_path = Path(dst)
                if src_path.name == "new.txt" and dst_path.name == "new.txt":
                    raise OSError("simulated failure")
                return original_replace(src, dst)

            with patch("s2t_tool.adapters.git.repository.os.replace", side_effect=failing_replace):
                with self.assertRaises(OSError):
                    replace_directory_contents(target, replacement)

            self.assertEqual((target / "old.txt").read_text(encoding="utf-8"), "old")
            self.assertFalse(replacement.exists())


if __name__ == "__main__":
    unittest.main()
