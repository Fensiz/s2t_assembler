from __future__ import annotations

from pathlib import Path

from s2t_tool.shared.constants import Logger
from s2t_tool.use_cases.ports import RepositoryGateway
from s2t_tool.adapters.git.repository import (
    commit_and_push,
    ensure_repo,
    export_commit_tree,
    has_changes_excluding,
    replace_directory_contents,
)


class GitRepositoryAdapter(RepositoryGateway):
    def ensure_repo(self, repo_url: str, repo_dir: Path, branch: str, base_branch: str, logger: Logger | None = None) -> None:
        ensure_repo(repo_url, repo_dir, branch, base_branch, logger=logger)

    def export_tree(self, repo_dir: Path, ref: str, target_dir: Path) -> None:
        export_commit_tree(repo_dir=repo_dir, commit_ref=ref, target_dir=target_dir)

    def replace_contents(self, path: Path, replacement_dir: Path, preserved_names: set[str] | None = None) -> None:
        replace_directory_contents(path=path, replacement_dir=replacement_dir, preserved_names=preserved_names or set())

    def has_changes_excluding(self, repo_dir: Path, excluded_paths: list[Path]) -> bool:
        return has_changes_excluding(repo_dir, excluded_paths=excluded_paths)

    def commit_and_push(self, repo_dir: Path, branch: str, message: str, logger: Logger | None = None) -> None:
        commit_and_push(repo_dir=repo_dir, branch=branch, message=message, logger=logger)
