from __future__ import annotations

from pathlib import Path

from s2t_tool.application.ports import (
    ArtifactGateway,
    ExcelGateway,
    PathResolver,
    RecentItemsGateway,
    RepositoryGateway,
)
from s2t_tool.application.results import RecentItem
from s2t_tool.application.settings import AppConfig
from s2t_tool.infrastructure.config import (
    resolve_excel_output_dir,
    resolve_repo_data_dir,
    resolve_repo_dir,
    resolve_repo_url,
    resolve_writer_config,
)
from s2t_tool.infrastructure.excel_artifacts import find_latest_excel_file
from s2t_tool.infrastructure.excel_reader import export_excel_to_repo
from s2t_tool.infrastructure.excel_writer import build_excel_from_repo
from s2t_tool.infrastructure.git_repo import (
    commit_and_push,
    ensure_repo,
    export_commit_tree,
    has_changes_excluding,
    replace_directory_contents,
)
from s2t_tool.infrastructure.recent_store import RecentItemsStore


class DefaultPathResolver(PathResolver):
    def repo_url(self, config: AppConfig, product_name: str) -> str:
        return resolve_repo_url(config, product_name)

    def repo_dir(self, config: AppConfig, product_name: str) -> Path:
        return resolve_repo_dir(config, product_name)

    def repo_data_dir(self, config: AppConfig, repo_dir: Path) -> Path:
        return resolve_repo_data_dir(config, repo_dir)

    def excel_output_dir(self, config: AppConfig) -> Path:
        return resolve_excel_output_dir(config)

    def writer_config(self, config: AppConfig) -> str:
        return resolve_writer_config(config)


class GitRepositoryAdapter(RepositoryGateway):
    def ensure_repo(self, repo_url: str, repo_dir: Path, branch: str, base_branch: str, logger=None) -> None:
        ensure_repo(repo_url, repo_dir, branch, base_branch, logger=logger)

    def export_tree(self, repo_dir: Path, ref: str, target_dir: Path) -> None:
        export_commit_tree(repo_dir=repo_dir, commit_ref=ref, target_dir=target_dir)

    def replace_contents(self, path: Path, replacement_dir: Path, preserved_names: set[str] | None = None) -> None:
        replace_directory_contents(path=path, replacement_dir=replacement_dir, preserved_names=preserved_names or set())

    def has_changes_excluding(self, repo_dir: Path, excluded_paths: list[Path]) -> bool:
        return has_changes_excluding(repo_dir, excluded_paths=excluded_paths)

    def commit_and_push(self, repo_dir: Path, branch: str, message: str, logger=None) -> None:
        commit_and_push(repo_dir=repo_dir, branch=branch, message=message, logger=logger)


class OpenpyxlExcelAdapter(ExcelGateway):
    def build_excel(
        self,
        repo_dir: Path,
        output_excel: Path,
        writer_config: str,
        diff_repo_dir: Path | None,
        diff_ref: str | None,
        logger=None,
    ) -> None:
        build_excel_from_repo(
            repo_dir=str(repo_dir),
            output_excel_path=str(output_excel),
            config_path=writer_config,
            diff_repo_dir=str(diff_repo_dir) if diff_repo_dir else None,
            diff_commit=diff_ref,
            logger=logger,
        )

    def export_excel_to_repo(
        self,
        excel_path: Path,
        output_dir: Path,
        format_sql: bool,
        logger=None,
    ) -> None:
        export_excel_to_repo(
            excel_path=str(excel_path),
            output_dir=str(output_dir),
            format_sql=format_sql,
            logger=logger,
        )


class ExcelArtifactAdapter(ArtifactGateway):
    def find_latest_excel(self, excel_dir: Path, product_name: str, diff_mode: bool) -> Path | None:
        return find_latest_excel_file(
            excel_dir=excel_dir,
            product_name=product_name,
            diff_mode=diff_mode,
        )


class RecentItemsAdapter(RecentItemsGateway):
    def __init__(self, store: RecentItemsStore | None = None) -> None:
        self.store = store or RecentItemsStore()

    def load(self) -> list[RecentItem]:
        return [RecentItem(**item) for item in self.store.load()]

    def save(self, items: list[RecentItem]) -> None:
        self.store.save(
            [
                {"product_name": item.product_name, "branch": item.branch}
                for item in items
            ]
        )

    def label(self, item: RecentItem) -> str:
        return self.store.label(
            {"product_name": item.product_name, "branch": item.branch}
        )
