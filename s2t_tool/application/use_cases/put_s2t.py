from __future__ import annotations

import tempfile
from pathlib import Path

from s2t_tool.application.commands import PutCommand
from s2t_tool.application.ports import ExcelGateway, PathResolver, RepositoryGateway
from s2t_tool.application.results import PutResult
from s2t_tool.application.settings import AppConfig
from s2t_tool.domain.branching import is_commit_ref, resolve_branch
from s2t_tool.domain.file_naming import ensure_put_compatible_excel, rename_excel_after_put, resolve_input_excel_path
from s2t_tool.domain.versioning import VERSION_JSON, read_repo_version, resolve_put_version, write_repo_version
from s2t_tool.infrastructure.adapters import (
    DefaultPathResolver,
    GitRepositoryAdapter,
    OpenpyxlExcelAdapter,
)


class PutS2TUseCase:
    def __init__(
        self,
        config: AppConfig,
        paths: PathResolver | None = None,
        repository: RepositoryGateway | None = None,
        excel: ExcelGateway | None = None,
    ) -> None:
        self.config = config
        self.paths = paths or DefaultPathResolver()
        self.repository = repository or GitRepositoryAdapter()
        self.excel = excel or OpenpyxlExcelAdapter()

    def execute(self, command: PutCommand) -> PutResult:
        if is_commit_ref(command.branch_arg):
            raise ValueError("PUT requires a branch name. Commit hash can be used only for GET.")

        branch = resolve_branch(self.config, command.branch_arg)
        base_branch = self.config.default_branch
        repo_url = self.paths.repo_url(self.config, command.product_name)
        repo_dir = self.paths.repo_dir(self.config, command.product_name)

        if command.logger:
            command.logger(f"Preparing repository: {repo_url}")
            command.logger(f"Branch: {branch}")

        self.repository.ensure_repo(repo_url, repo_dir, branch, base_branch, logger=command.logger)

        repo_data_dir = self.paths.repo_data_dir(self.config, repo_dir)
        version_path = repo_data_dir / VERSION_JSON
        original_version = read_repo_version(version_path)
        input_excel = resolve_input_excel_path(
            config=self.config,
            product_name=command.product_name,
            explicit_excel=command.excel_arg,
            explicit_version=command.version_arg,
            branch=branch,
        )

        if not input_excel.exists():
            raise ValueError(f"Excel file not found: {input_excel}")

        ensure_put_compatible_excel(input_excel)

        if command.logger:
            command.logger(f"Reading Excel: {input_excel}")
            command.logger("Exporting Excel into staging directory...")

        repo_data_dir.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="s2t_put_", dir=str(repo_data_dir.parent)) as temp_dir:
            staged_repo_data_dir = Path(temp_dir) / repo_data_dir.name
            staged_repo_data_dir.mkdir(parents=True, exist_ok=True)

            self.excel.export_excel_to_repo(
                excel_path=input_excel,
                output_dir=staged_repo_data_dir,
                format_sql=command.format_sql,
                logger=command.logger,
            )

            if command.logger:
                command.logger("Replacing repo data directory with staged export...")

            preserved_names = {".git"} if repo_data_dir == repo_dir else set()
            self.repository.replace_contents(
                path=repo_data_dir,
                replacement_dir=staged_repo_data_dir,
                preserved_names=preserved_names,
            )

        if command.keep_version:
            write_repo_version(version_path, original_version)

        version_rel_path = version_path.relative_to(repo_dir)
        if not self.repository.has_changes_excluding(repo_dir, excluded_paths=[version_rel_path]):
            if command.logger:
                command.logger("No content changes detected. Version was not bumped.")
                command.logger("Nothing to commit.")
            return PutResult(
                product_name=command.product_name,
                repo_dir=repo_dir,
                version=original_version,
                changed=False,
            )

        if command.keep_version:
            new_version = original_version
            if command.logger:
                command.logger(f"Keeping version unchanged: {new_version}")
        else:
            new_version = resolve_put_version(
                version_arg=command.version_arg,
                input_excel=input_excel,
                product_name=command.product_name,
                version_path=version_path,
            )
            write_repo_version(version_path, new_version)

        commit_message = (
            command.commit_message_arg.strip()
            if command.commit_message_arg and command.commit_message_arg.strip()
            else f"Update S2T for {command.product_name} to version {new_version}"
        )

        if command.logger:
            command.logger("Committing and pushing changes...")

        self.repository.commit_and_push(repo_dir=repo_dir, branch=branch, message=commit_message, logger=command.logger)

        rename_excel_after_put(
            input_excel=input_excel,
            product_name=command.product_name,
            new_version=new_version,
            branch=branch,
            default_branch=base_branch,
            logger=command.logger,
        )

        if command.logger:
            command.logger(f"Repo updated: {repo_dir}")
            command.logger(f"New version: {new_version}")

        return PutResult(
            product_name=command.product_name,
            repo_dir=repo_dir,
            version=new_version,
            changed=True,
        )
