from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from s2t_tool.application.commands import GetCommand, PutCommand
from s2t_tool.application.service import S2TService


class ServiceCommitRefTests(unittest.TestCase):
    def test_put_rejects_commit_hash_instead_of_branch(self) -> None:
        service = S2TService()
        command = PutCommand(
            product_name="s2t_test",
            branch_arg="c220991",
            version_arg=None,
            keep_version=False,
            excel_arg=None,
            commit_message_arg=None,
            config={"default_branch": "s2t/master"},
            logger=None,
        )

        with self.assertRaises(ValueError):
            service.handle_put(command)

    def test_get_uses_commit_export_when_branch_arg_is_commit_hash(self) -> None:
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
            (repo_data_dir / "version.json").write_text('{"version":"1.2.3"}', encoding="utf-8")

            command = GetCommand(
                product_name="s2t_test",
                branch_arg="c220991",
                version_arg=None,
                diff_commit_arg=None,
                config=config,
                logger=None,
            )

            with patch("s2t_tool.application.use_cases.get_s2t.ensure_repo") as ensure_repo_mock, \
                patch("s2t_tool.application.use_cases.get_s2t.export_commit_tree") as export_commit_tree_mock, \
                patch("s2t_tool.application.use_cases.get_s2t.build_excel_from_repo") as build_excel_from_repo_mock:
                export_commit_tree_mock.side_effect = lambda repo_dir, commit_ref, target_dir: None

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

                ensure_repo_mock.assert_called_once()
                export_commit_tree_mock.assert_called_once()
                build_excel_from_repo_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
