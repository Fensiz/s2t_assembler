from __future__ import annotations

import tempfile
from pathlib import Path

from s2t_tool.application.commands import GetCommand
from s2t_tool.domain.branching import is_commit_ref, is_debug_branch, resolve_branch
from s2t_tool.domain.file_naming import (
    build_branch_diff_excel_filename,
    build_branch_excel_filename,
    build_commit_excel_filename,
)
from s2t_tool.domain.versioning import (
    VERSION_JSON,
    build_version_tag,
    looks_like_version,
    read_repo_version,
)
from s2t_tool.infrastructure.config import (
    ensure_excel_output_dir,
    resolve_excel_output_dir,
    resolve_repo_data_dir,
    resolve_repo_dir,
    resolve_repo_url,
    resolve_writer_config,
)
from s2t_tool.infrastructure.excel_writer import build_excel_from_repo
from s2t_tool.infrastructure.git_repo import ensure_repo, export_commit_tree


class GetS2TUseCase:
    def execute(self, command: GetCommand) -> None:
        base_branch = str(command.config.get("default_branch", "master")).strip()
        version_ref = command.version_arg.strip() if command.version_arg and command.version_arg.strip() else None
        commit_ref = command.branch_arg.strip() if is_commit_ref(command.branch_arg) else None
        branch = base_branch if (commit_ref or version_ref) else resolve_branch(command.config, command.branch_arg)
        debug_mode = False if (commit_ref or version_ref) else is_debug_branch(branch, base_branch)
        repo_url = resolve_repo_url(command.config, command.product_name)
        repo_dir = resolve_repo_dir(command.config, command.product_name)

        if command.logger:
            command.logger(f"Preparing repository: {repo_url}")
            if version_ref:
                command.logger(f"Tag version: {build_version_tag(version_ref)}")
                command.logger(f"Base branch for fetch: {branch}")
            elif commit_ref:
                command.logger(f"Commit: {commit_ref}")
                command.logger(f"Base branch for fetch: {branch}")
            else:
                command.logger(f"Branch: {branch}")

        ensure_repo(repo_url, repo_dir, branch, base_branch, logger=command.logger)
        repo_data_dir = resolve_repo_data_dir(command.config, repo_dir)

        if version_ref:
            with tempfile.TemporaryDirectory(prefix="s2t_tag_") as temp_dir:
                export_commit_tree(
                    repo_dir=repo_dir,
                    commit_ref=build_version_tag(version_ref),
                    target_dir=Path(temp_dir),
                )
                source_repo_data_dir = resolve_repo_data_dir(command.config, Path(temp_dir))
                version = read_repo_version(source_repo_data_dir / VERSION_JSON)
                self._build_excel(command, source_repo_data_dir, version, debug_mode, None)
            return

        if commit_ref:
            with tempfile.TemporaryDirectory(prefix="s2t_commit_") as temp_dir:
                export_commit_tree(repo_dir=repo_dir, commit_ref=commit_ref, target_dir=Path(temp_dir))
                source_repo_data_dir = resolve_repo_data_dir(command.config, Path(temp_dir))
                version = read_repo_version(source_repo_data_dir / VERSION_JSON)
                self._build_excel(command, source_repo_data_dir, version, debug_mode, commit_ref)
            return

        version = read_repo_version(repo_data_dir / VERSION_JSON)
        self._build_excel(command, repo_data_dir, version, debug_mode, None)

    def _build_excel(
        self,
        command: GetCommand,
        repo_data_dir: Path,
        excel_version: str,
        debug_mode: bool,
        commit_ref: str | None,
    ) -> None:
        excel_output_dir = resolve_excel_output_dir(command.config)
        ensure_excel_output_dir(excel_output_dir)

        diff_ref = self._resolve_diff_ref(command.diff_commit_arg)

        if diff_ref:
            output_excel = excel_output_dir / build_branch_diff_excel_filename(
                command.product_name,
                excel_version,
                debug_mode,
            )
        elif commit_ref:
            output_excel = excel_output_dir / build_commit_excel_filename(
                command.product_name,
                excel_version,
                commit_ref,
            )
        else:
            output_excel = excel_output_dir / build_branch_excel_filename(
                command.product_name,
                excel_version,
                debug_mode,
            )

        writer_config = resolve_writer_config(command.config)

        if diff_ref:
            if command.logger:
                command.logger(f"Exporting diff tree from ref: {diff_ref}")

            with tempfile.TemporaryDirectory(prefix="s2t_diff_") as temp_dir:
                export_commit_tree(
                    repo_dir=resolve_repo_dir(command.config, command.product_name),
                    commit_ref=diff_ref,
                    target_dir=Path(temp_dir),
                )
                diff_repo_dir = str(resolve_repo_data_dir(command.config, Path(temp_dir)))

                if command.logger:
                    command.logger("Building Excel with diff highlighting...")

                build_excel_from_repo(
                    repo_dir=str(repo_data_dir),
                    output_excel_path=str(output_excel),
                    config_path=writer_config,
                    diff_repo_dir=diff_repo_dir,
                    diff_commit=diff_ref,
                    logger=command.logger,
                )
        else:
            if command.logger:
                command.logger("Building Excel file...")

            build_excel_from_repo(
                repo_dir=str(repo_data_dir),
                output_excel_path=str(output_excel),
                config_path=writer_config,
                diff_repo_dir=None,
                diff_commit=commit_ref,
                logger=command.logger,
            )

        if command.logger:
            command.logger(f"Excel created: {output_excel}")
        print(f"Excel created: {output_excel}")

    @staticmethod
    def _resolve_diff_ref(diff_ref: str | None) -> str | None:
        if diff_ref is None:
            return None

        normalized = diff_ref.strip()
        if not normalized:
            return None

        if looks_like_version(normalized):
            return build_version_tag(normalized)

        return normalized
