from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from s2t_tool.application.commands import GetCommand, PutCommand
from s2t_tool.application.service import S2TService


class ServiceVersionRefTests(unittest.TestCase):
    def test_get_uses_tag_when_version_is_provided(self) -> None:
        service = S2TService()
        config = {
            "default_branch": "s2t/master",
            "repo_base_url": "git@github.com:Fensiz",
            "workspace_dir": "~/.s2t",
            "excel_output_dir": "~/.s2t/excel",
            "writer_config": "writer_config.json",
            "repo_data_subdir": "resources/s2t",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            exported_root = Path(temp_dir) / "exported"
            repo_data_dir = exported_root / "resources" / "s2t"
            repo_data_dir.mkdir(parents=True)
            (repo_data_dir / "version.json").write_text('{"version":"2.4.6"}', encoding="utf-8")

            command = GetCommand(
                product_name="s2t_test",
                branch_arg=None,
                version_arg="2.4.6",
                diff_commit_arg=None,
                config=config,
                logger=None,
            )

            with patch("s2t_tool.application.use_cases.get_s2t.ensure_repo"), \
                patch("s2t_tool.application.use_cases.get_s2t.export_commit_tree") as export_commit_tree_mock, \
                patch("s2t_tool.application.use_cases.get_s2t.build_excel_from_repo") as build_excel_mock:
                original_resolve_repo_data_dir = __import__(
                    "s2t_tool.application.use_cases.get_s2t", fromlist=["resolve_repo_data_dir"]
                ).resolve_repo_data_dir

                with patch(
                    "s2t_tool.application.use_cases.get_s2t.resolve_repo_data_dir",
                    side_effect=lambda cfg, repo_dir: repo_data_dir if Path(repo_dir) == exported_root else original_resolve_repo_data_dir(cfg, repo_dir),
                ):
                    with patch(
                        "tempfile.TemporaryDirectory",
                        return_value=type(
                            "TempDir",
                            (),
                            {
                                "__enter__": lambda self: str(exported_root),
                                "__exit__": lambda self, exc_type, exc, tb: False,
                            },
                        )(),
                    ):
                        service.handle_get(command)

                export_commit_tree_mock.assert_called_once()
                self.assertEqual(export_commit_tree_mock.call_args.kwargs["commit_ref"], "s2t.2.4.6")
                output_path = Path(build_excel_mock.call_args.kwargs["output_excel_path"])
                self.assertEqual(output_path.name, "S2T_USL_S2T_TEST_v2.4.6.xlsx")

    def test_get_resolves_diff_version_to_tag(self) -> None:
        service = S2TService()
        config = {
            "default_branch": "s2t/master",
            "repo_base_url": "git@github.com:Fensiz",
            "workspace_dir": "~/.s2t",
            "excel_output_dir": "~/.s2t/excel",
            "writer_config": "writer_config.json",
            "repo_data_subdir": "resources/s2t",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            repo_data_dir = repo_root / "resources" / "s2t"
            repo_data_dir.mkdir(parents=True)
            (repo_data_dir / "version.json").write_text('{"version":"3.0.0"}', encoding="utf-8")

            command = GetCommand(
                product_name="s2t_test",
                branch_arg="s2t/master",
                version_arg=None,
                diff_commit_arg="2.4.6",
                config=config,
                logger=None,
            )

            with patch("s2t_tool.application.use_cases.get_s2t.ensure_repo"), \
                patch("s2t_tool.application.use_cases.get_s2t.resolve_repo_dir", return_value=repo_root), \
                patch("s2t_tool.application.use_cases.get_s2t.resolve_repo_data_dir", return_value=repo_data_dir), \
                patch("s2t_tool.application.use_cases.get_s2t.build_excel_from_repo") as build_excel_mock, \
                patch("s2t_tool.application.use_cases.get_s2t.export_commit_tree") as export_commit_tree_mock:
                service.handle_get(command)

                self.assertEqual(export_commit_tree_mock.call_args.kwargs["commit_ref"], "s2t.2.4.6")
                self.assertEqual(build_excel_mock.call_args.kwargs["diff_commit"], "s2t.2.4.6")

    def test_put_keep_version_does_not_bump(self) -> None:
        service = S2TService()
        config = {
            "default_branch": "s2t/master",
            "repo_base_url": "git@github.com:Fensiz",
            "workspace_dir": "~/.s2t",
            "excel_output_dir": "~/.s2t/excel",
            "repo_data_subdir": "resources/s2t",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            repo_data_dir = repo_root / "resources" / "s2t"
            repo_data_dir.mkdir(parents=True)
            version_path = repo_data_dir / "version.json"
            version_path.write_text('{"version":"1.2.3"}', encoding="utf-8")
            excel_path = Path(temp_dir) / "input.xlsx"
            excel_path.write_text("stub", encoding="utf-8")

            command = PutCommand(
                product_name="s2t_test",
                branch_arg="s2t/master",
                version_arg=None,
                keep_version=True,
                excel_arg=str(excel_path),
                commit_message_arg=None,
                config=config,
                logger=None,
            )

            with patch("s2t_tool.application.use_cases.put_s2t.ensure_repo"), \
                patch("s2t_tool.application.use_cases.put_s2t.resolve_repo_dir", return_value=repo_root), \
                patch("s2t_tool.application.use_cases.put_s2t.resolve_repo_data_dir", return_value=repo_data_dir), \
                patch("s2t_tool.application.use_cases.put_s2t.ensure_put_compatible_excel"), \
                patch("s2t_tool.application.use_cases.put_s2t.export_excel_to_repo"), \
                patch("s2t_tool.application.use_cases.put_s2t.replace_directory_contents"), \
                patch("s2t_tool.application.use_cases.put_s2t.has_changes_excluding", return_value=True), \
                patch("s2t_tool.application.use_cases.put_s2t.commit_and_push"), \
                patch("s2t_tool.application.use_cases.put_s2t.rename_excel_after_put"), \
                patch("s2t_tool.application.use_cases.put_s2t.write_repo_version") as write_repo_version_mock:
                service.handle_put(command)

                write_repo_version_mock.assert_called_once_with(version_path, "1.2.3")
                self.assertIn('"1.2.3"', version_path.read_text(encoding="utf-8"))

    def test_put_keep_version_restores_original_version_after_staged_replace(self) -> None:
        service = S2TService()
        config = {
            "default_branch": "s2t/master",
            "repo_base_url": "git@github.com:Fensiz",
            "workspace_dir": "~/.s2t",
            "excel_output_dir": "~/.s2t/excel",
            "repo_data_subdir": "resources/s2t",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            repo_data_dir = repo_root / "resources" / "s2t"
            repo_data_dir.mkdir(parents=True)
            version_path = repo_data_dir / "version.json"
            version_path.write_text('{"version":"2.0"}', encoding="utf-8")
            (repo_data_dir / "payload.json").write_text('{"before":true}', encoding="utf-8")

            excel_path = Path(temp_dir) / "input.xlsx"
            excel_path.write_text("stub", encoding="utf-8")

            command = PutCommand(
                product_name="s2t_test",
                branch_arg="s2t/master",
                version_arg=None,
                keep_version=True,
                excel_arg=str(excel_path),
                commit_message_arg=None,
                config=config,
                logger=None,
            )

            def fake_export_excel_to_repo(excel_path: str, output_dir: str, logger=None) -> None:
                target = Path(output_dir)
                target.mkdir(parents=True, exist_ok=True)
                (target / "payload.json").write_text('{"after":true}', encoding="utf-8")

            with patch("s2t_tool.application.use_cases.put_s2t.ensure_repo"), \
                patch("s2t_tool.application.use_cases.put_s2t.resolve_repo_dir", return_value=repo_root), \
                patch("s2t_tool.application.use_cases.put_s2t.resolve_repo_data_dir", return_value=repo_data_dir), \
                patch("s2t_tool.application.use_cases.put_s2t.ensure_put_compatible_excel"), \
                patch("s2t_tool.application.use_cases.put_s2t.export_excel_to_repo", side_effect=fake_export_excel_to_repo), \
                patch("s2t_tool.application.use_cases.put_s2t.has_changes_excluding", return_value=True), \
                patch("s2t_tool.application.use_cases.put_s2t.commit_and_push"), \
                patch("s2t_tool.application.use_cases.put_s2t.rename_excel_after_put"):
                service.handle_put(command)

            restored_version = json.loads(version_path.read_text(encoding="utf-8"))["version"]
            self.assertEqual(restored_version, "2.0")
            self.assertEqual((repo_data_dir / "payload.json").read_text(encoding="utf-8"), '{"after":true}')


if __name__ == "__main__":
    unittest.main()
