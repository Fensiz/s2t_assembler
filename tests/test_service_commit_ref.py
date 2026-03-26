from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from s2t_tool.application.commands import GetCommand, PutCommand
from s2t_tool.application.service import S2TService
from s2t_tool.application.settings import AppConfig


class ServiceCommitRefTests(unittest.TestCase):
    def test_put_rejects_commit_hash_instead_of_branch(self) -> None:
        service = S2TService(AppConfig.from_mapping({"repo_base_url": "git@github.com:Fensiz"}))
        command = PutCommand(
            product_name="s2t_test",
            branch_arg="c220991",
            version_arg=None,
            keep_version=False,
            format_sql=False,
            excel_arg=None,
            commit_message_arg=None,
            logger=None,
        )

        with self.assertRaises(ValueError):
            service.handle_put(command)

    def test_get_uses_commit_export_when_branch_arg_is_commit_hash(self) -> None:
        config = AppConfig.from_mapping(
            {
                "default_branch": "s2t/master",
                "repo_base_url": "git@github.com:Fensiz",
                "workspace_dir": "~/.s2t",
                "excel_output_dir": "~/.s2t/excel",
                "writer_config": "writer_config.json",
                "repo_data_subdir": "resources/s2t",
            }
        )
        service = S2TService(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            exported_root = Path(temp_dir) / "exported"
            repo_data_dir = exported_root / "resources" / "s2t"
            repo_data_dir.mkdir(parents=True)
            (repo_data_dir / "version.json").write_text('{"version":"1.2.3"}', encoding="utf-8")

            repository = Mock()
            excel = Mock()
            paths = Mock()
            paths.repo_url.return_value = "git@github.com:Fensiz/s2t_test.git"
            paths.repo_dir.return_value = Path(temp_dir) / "repo"
            paths.repo_data_dir.side_effect = lambda cfg, repo_dir: repo_data_dir if Path(repo_dir) == exported_root else Path(repo_dir) / "resources" / "s2t"
            paths.excel_output_dir.return_value = Path(temp_dir) / "excel"
            paths.writer_config.return_value = "writer_config.json"

            service.get_use_case.repository = repository
            service.get_use_case.excel = excel
            service.get_use_case.paths = paths

            command = GetCommand(
                product_name="s2t_test",
                branch_arg="c220991",
                version_arg=None,
                diff_commit_arg=None,
                logger=None,
            )

            with unittest.mock.patch(
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
                result = service.handle_get(command)

            repository.ensure_repo.assert_called_once()
            repository.export_tree.assert_called_once_with(
                repo_dir=paths.repo_dir.return_value,
                ref="c220991",
                target_dir=exported_root,
            )
            excel.build_excel.assert_called_once()
            self.assertEqual(result.output_excel.name, "S2T_USL_S2T_TEST_v1.2.3_commit_c220991.xlsx")


if __name__ == "__main__":
    unittest.main()
