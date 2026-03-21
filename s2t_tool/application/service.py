from __future__ import annotations

import tempfile
from pathlib import Path

from s2t_tool.application.commands import GetCommand, PutCommand
from s2t_tool.domain.branching import is_commit_ref, is_debug_branch, resolve_branch
from s2t_tool.domain.file_naming import (
    build_branch_diff_excel_filename,
    build_branch_excel_filename,
    build_commit_excel_filename,
    ensure_put_compatible_excel,
    rename_excel_after_put,
    resolve_input_excel_path,
)
from s2t_tool.domain.versioning import (
    VERSION_JSON,
    read_repo_version,
    resolve_put_version,
    write_repo_version,
)
from s2t_tool.infrastructure.config import (
    ensure_excel_output_dir,
    resolve_excel_output_dir,
    resolve_repo_data_dir,
    resolve_repo_dir,
    resolve_repo_url,
    resolve_writer_config,
)
from s2t_tool.infrastructure.excel_reader import export_excel_to_repo
from s2t_tool.infrastructure.excel_writer import build_excel_from_repo
from s2t_tool.infrastructure.git_repo import (
    commit_and_push,
    ensure_repo,
    export_commit_tree,
    has_changes_excluding,
    replace_directory_contents,
)


class S2TService:
    def handle_get(self, command: GetCommand) -> None:
        """
        Download/refresh repo, build Excel and save it locally.
        """
        base_branch = str(command.config.get("default_branch", "master")).strip()
        commit_ref = command.branch_arg.strip() if is_commit_ref(command.branch_arg) else None
        branch = base_branch if commit_ref else resolve_branch(command.config, command.branch_arg)
        debug_mode = False if commit_ref else is_debug_branch(branch, base_branch)
        repo_url = resolve_repo_url(command.config, command.product_name)
        repo_dir = resolve_repo_dir(command.config, command.product_name)

        if command.logger:
            command.logger(f"Preparing repository: {repo_url}")
            if commit_ref:
                command.logger(f"Commit: {commit_ref}")
                command.logger(f"Base branch for fetch: {branch}")
            else:
                command.logger(f"Branch: {branch}")

        ensure_repo(repo_url, repo_dir, branch, base_branch, logger=command.logger)

        repo_data_dir = resolve_repo_data_dir(command.config, repo_dir)

        if commit_ref:
            with tempfile.TemporaryDirectory(prefix="s2t_commit_") as temp_dir:
                export_commit_tree(
                    repo_dir=repo_dir,
                    commit_ref=commit_ref,
                    target_dir=Path(temp_dir),
                )
                source_repo_data_dir = resolve_repo_data_dir(command.config, Path(temp_dir))
                version_path = source_repo_data_dir / VERSION_JSON
                version = read_repo_version(version_path)
                self._build_get_excel(
                    command=command,
                    repo_data_dir=source_repo_data_dir,
                    excel_version=version,
                    debug_mode=debug_mode,
                    commit_ref=commit_ref,
                )
            return

        version_path = repo_data_dir / VERSION_JSON
        version = read_repo_version(version_path)
        self._build_get_excel(
            command=command,
            repo_data_dir=repo_data_dir,
            excel_version=version,
            debug_mode=debug_mode,
            commit_ref=None,
        )

    def _build_get_excel(
        self,
        command: GetCommand,
        repo_data_dir: Path,
        excel_version: str,
        debug_mode: bool,
        commit_ref: str | None,
    ) -> None:
        base_branch = str(command.config.get("default_branch", "master")).strip()

        excel_output_dir = resolve_excel_output_dir(command.config)
        ensure_excel_output_dir(excel_output_dir)

        if command.diff_commit_arg:
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

        if command.diff_commit_arg:
            if command.logger:
                command.logger(f"Exporting diff tree from commit: {command.diff_commit_arg}")

            with tempfile.TemporaryDirectory(prefix="s2t_diff_") as temp_dir:
                export_commit_tree(
                    repo_dir=repo_dir,
                    commit_ref=command.diff_commit_arg,
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
                    diff_commit=command.diff_commit_arg,
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

    def handle_put(self, command: PutCommand) -> None:
        """
        Parse Excel into repo structure, update version, commit and push.
        """
        if is_commit_ref(command.branch_arg):
            raise ValueError("PUT requires a branch name. Commit hash can be used only for GET.")

        branch = resolve_branch(command.config, command.branch_arg)
        base_branch = str(command.config.get("default_branch", "master")).strip()
        repo_url = resolve_repo_url(command.config, command.product_name)
        repo_dir = resolve_repo_dir(command.config, command.product_name)

        if command.logger:
            command.logger(f"Preparing repository: {repo_url}")
            command.logger(f"Branch: {branch}")

        ensure_repo(repo_url, repo_dir, branch, base_branch, logger=command.logger)

        repo_data_dir = resolve_repo_data_dir(command.config, repo_dir)
        version_path = repo_data_dir / VERSION_JSON

        input_excel = resolve_input_excel_path(
            config=command.config,
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

        with tempfile.TemporaryDirectory(
            prefix="s2t_put_",
            dir=str(repo_data_dir.parent),
        ) as temp_dir:
            staged_repo_data_dir = Path(temp_dir) / repo_data_dir.name
            staged_repo_data_dir.mkdir(parents=True, exist_ok=True)

            export_excel_to_repo(
                excel_path=str(input_excel),
                output_dir=str(staged_repo_data_dir),
                logger=command.logger,
            )

            if command.logger:
                command.logger("Replacing repo data directory with staged export...")

            preserved_names = {".git"} if repo_data_dir == repo_dir else set()
            replace_directory_contents(
                path=repo_data_dir,
                replacement_dir=staged_repo_data_dir,
                preserved_names=preserved_names,
            )

        version_rel_path = version_path.relative_to(repo_dir)

        if not has_changes_excluding(repo_dir, excluded_paths=[version_rel_path]):
            if command.logger:
                command.logger("No content changes detected. Version was not bumped.")
                command.logger("Nothing to commit.")
            print("No content changes detected. Nothing to commit.")
            return

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

        commit_and_push(repo_dir=repo_dir, branch=branch, message=commit_message, logger=command.logger)

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

        print(f"Repo updated: {repo_dir}")
        print(f"New version: {new_version}")
