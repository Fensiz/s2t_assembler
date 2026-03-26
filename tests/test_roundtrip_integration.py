from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from s2t_tool.adapters.facades import DefaultPathResolver, OpenpyxlExcelAdapter
from s2t_tool.adapters.git.repository import replace_directory_contents
from s2t_tool.shared.csv_files import write_csv_rows
from s2t_tool.shared.files import write_json_file, write_text_file
from s2t_tool.use_cases.commands import GetCommand, PutCommand
from s2t_tool.use_cases.get_s2t import GetS2TUseCase
from s2t_tool.use_cases.put_s2t import PutS2TUseCase
from s2t_tool.use_cases.service import S2TService
from s2t_tool.use_cases.settings import AppConfig


def snapshot_tree(root: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        result[str(path.relative_to(root))] = path.read_bytes()
    return result


class LocalRepositoryGateway:
    def __init__(self) -> None:
        self._snapshots: dict[Path, dict[str, bytes]] = {}
        self.commit_calls: list[tuple[Path, str, str]] = []

    def ensure_repo(self, repo_url: str, repo_dir: Path, branch: str, base_branch: str, logger=None) -> None:
        self._snapshots[repo_dir] = snapshot_tree(repo_dir)

    def export_tree(self, repo_dir: Path, ref: str, target_dir: Path) -> None:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(repo_dir, target_dir)

    def replace_contents(self, path: Path, replacement_dir: Path, preserved_names: set[str] | None = None) -> None:
        replace_directory_contents(path, replacement_dir, preserved_names or set())

    def has_changes_excluding(self, repo_dir: Path, excluded_paths: list[Path]) -> bool:
        before = dict(self._snapshots.get(repo_dir, {}))
        after = snapshot_tree(repo_dir)
        excluded = {str(path).replace("\\", "/") for path in excluded_paths}
        for key in excluded:
            before.pop(key, None)
            after.pop(key, None)
        return before != after

    def commit_and_push(self, repo_dir: Path, branch: str, message: str, logger=None) -> None:
        self.commit_calls.append((repo_dir, branch, message))


class RoundtripIntegrationTests(unittest.TestCase):
    def _build_fixture(self, temp_root: Path) -> tuple[str, Path, Path, AppConfig, LocalRepositoryGateway, S2TService]:
        workspace_dir = temp_root / "workspace"
        excel_dir = temp_root / "excel"
        product_name = "demo_s2t"
        repo_dir = workspace_dir / product_name
        repo_data_dir = repo_dir / "resources" / "s2t"
        repo_data_dir.mkdir(parents=True)
        excel_dir.mkdir(parents=True)

        write_json_file(
            repo_data_dir / "change-history.json",
            [
                {
                    "author": "dev",
                    "date": "2026-03-26",
                    "version": "1.0.0",
                    "description": "Initial import",
                    "jira_ticket": "S2T-1",
                }
            ],
        )
        write_csv_rows(
            repo_data_dir / "source-lg.csv",
            ["scheme", "table", "column", "data_type", "data_length", "is_key", "description", "link"],
            [["dm", "registry", "sid", "string", "", "Y", "Source id", ""]],
        )
        write_csv_rows(
            repo_data_dir / "targets.csv",
            ["table_code", "table_name"],
            [["registry", "registry"]],
        )
        write_json_file(repo_data_dir / "version.json", {"version": "1.0.0"})
        write_json_file(
            repo_data_dir / "attribute_names.json",
            {"common": {"sid": "Source ID"}, "tables": {}},
        )

        join_dir = repo_data_dir / "joins" / "registry" / "main"
        join_dir.mkdir(parents=True)
        write_json_file(
            join_dir / "join.json",
            {
                "description": "Registry join",
                "table_codes": ["registry"],
                "table_codes_to_track_delta": ["registry"],
                "load_code_params": ["env=prod"],
                "history_rule": "snapshot",
                "business_history_dates": "off",
            },
        )
        write_text_file(join_dir / "source_tables_join.sql", "select sid from src_registry where x = 1 and y = 2")
        write_text_file(join_dir / "settings_table_join.sql", "select 1")
        write_csv_rows(
            join_dir / "mappings.csv",
            ["attribute_code", "mapping_algorithm"],
            [["sid", "src_registry.sid"]],
        )

        config = AppConfig.from_mapping(
            {
                "repo_base_url": "git@example.com:demo",
                "workspace_dir": str(workspace_dir),
                "excel_output_dir": str(excel_dir),
                "repo_data_subdir": "resources/s2t",
                "writer_config": "writer_config.json",
                "default_branch": "master",
            }
        )

        repository = LocalRepositoryGateway()
        paths = DefaultPathResolver()
        excel = OpenpyxlExcelAdapter()
        service = S2TService(
            config=config,
            get_use_case=GetS2TUseCase(config, paths=paths, repository=repository, excel=excel),
            put_use_case=PutS2TUseCase(config, paths=paths, repository=repository, excel=excel),
        )
        return product_name, repo_dir, repo_data_dir, config, repository, service

    def test_repo_get_put_get_roundtrip_keeps_repo_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            product_name, _repo_dir, repo_data_dir, _config, repository, service = self._build_fixture(temp_root)
            before_snapshot = snapshot_tree(repo_data_dir)

            get_result = service.handle_get(
                GetCommand(
                    product_name=product_name,
                    branch_arg="master",
                    version_arg=None,
                    diff_commit_arg=None,
                    logger=None,
                )
            )

            self.assertTrue(get_result.output_excel.exists())

            put_result = service.handle_put(
                PutCommand(
                    product_name=product_name,
                    branch_arg="master",
                    version_arg=None,
                    keep_version=False,
                    format_sql=False,
                    excel_arg=None,
                    commit_message_arg=None,
                    logger=None,
                )
            )

            after_put_snapshot = snapshot_tree(repo_data_dir)
            self.assertFalse(put_result.changed)
            self.assertEqual(before_snapshot, after_put_snapshot)
            self.assertEqual(repository.commit_calls, [])

            get_result_2 = service.handle_get(
                GetCommand(
                    product_name=product_name,
                    branch_arg="master",
                    version_arg=None,
                    diff_commit_arg=None,
                    logger=None,
                )
            )

            self.assertTrue(get_result_2.output_excel.exists())
            self.assertEqual(get_result.output_excel, get_result_2.output_excel)

    def test_get_diff_roundtrip_creates_diff_excel(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            product_name, _repo_dir, _repo_data_dir, _config, _repository, service = self._build_fixture(temp_root)

            result = service.handle_get(
                GetCommand(
                    product_name=product_name,
                    branch_arg="master",
                    version_arg=None,
                    diff_commit_arg="abc1234",
                    logger=None,
                )
            )

            self.assertTrue(result.diff_mode)
            self.assertTrue(result.output_excel.exists())
            self.assertTrue(result.output_excel.name.endswith("_diff.xlsx"))

    def test_put_with_format_sql_formats_join_sql_and_commits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            product_name, _repo_dir, repo_data_dir, _config, repository, service = self._build_fixture(temp_root)

            get_result = service.handle_get(
                GetCommand(
                    product_name=product_name,
                    branch_arg="master",
                    version_arg=None,
                    diff_commit_arg=None,
                    logger=None,
                )
            )
            self.assertTrue(get_result.output_excel.exists())

            put_result = service.handle_put(
                PutCommand(
                    product_name=product_name,
                    branch_arg="master",
                    version_arg=None,
                    keep_version=False,
                    format_sql=True,
                    excel_arg=None,
                    commit_message_arg=None,
                    logger=None,
                )
            )

            formatted_sql = (repo_data_dir / "joins" / "registry" / "main" / "source_tables_join.sql").read_text(encoding="utf-8")
            self.assertTrue(put_result.changed)
            self.assertIn("SELECT", formatted_sql)
            self.assertIn("\nFROM", formatted_sql)
            self.assertIn("\nWHERE x = 1", formatted_sql)
            self.assertIn("\n    AND y = 2", formatted_sql)
            self.assertEqual(len(repository.commit_calls), 1)


if __name__ == "__main__":
    unittest.main()
