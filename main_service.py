from __future__ import annotations

import tempfile
from pathlib import Path

from git_repo import (
    clear_directory_contents,
    commit_and_push,
    ensure_repo,
    export_commit_tree,
    has_changes_excluding,
)
from reader import export_excel_to_repo
from writer import build_excel_from_repo

from main_branching import is_debug_branch, resolve_branch
from main_config import (
    ensure_excel_output_dir,
    resolve_excel_output_dir,
    resolve_repo_data_dir,
    resolve_repo_dir,
    resolve_repo_url,
    resolve_writer_config,
)
from main_files import (
    build_branch_diff_excel_filename,
    build_branch_excel_filename,
    ensure_not_diff_excel,
    rename_excel_after_put,
    resolve_input_excel_path,
)
from main_models import GetCommand, PutCommand
from main_versioning import VERSION_JSON, read_repo_version, resolve_put_version, write_repo_version


class S2TService:
    def handle_get(self, command: GetCommand) -> None:
        """
        Download/refresh repo, build Excel and save it locally.
        """
        branch = resolve_branch(command.config, command.branch_arg)
        base_branch = str(command.config.get("default_branch", "master")).strip()
        debug_mode = is_debug_branch(branch, base_branch)
        repo_url = resolve_repo_url(command.config, command.product_name)
        repo_dir = resolve_repo_dir(command.config, command.product_name)

        if command.logger:
            command.logger(f"Preparing repository: {repo_url}")
            command.logger(f"Branch: {branch}")

        ensure_repo(repo_url, repo_dir, branch, base_branch, logger=command.logger)

        repo_data_dir = resolve_repo_data_dir(command.config, repo_dir)
        version_path = repo_data_dir / VERSION_JSON
        version = read_repo_version(version_path)

        excel_output_dir = resolve_excel_output_dir(command.config)
        ensure_excel_output_dir(excel_output_dir)

        if command.diff_commit_arg:
            output_excel = excel_output_dir / build_branch_diff_excel_filename(
                command.product_name,
                version,
                debug_mode,
            )
        else:
            output_excel = excel_output_dir / build_branch_excel_filename(
                command.product_name,
                version,
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
                )
        else:
            if command.logger:
                command.logger("Building Excel file...")

            build_excel_from_repo(
                repo_dir=str(repo_data_dir),
                output_excel_path=str(output_excel),
                config_path=writer_config,
                diff_repo_dir=None,
                diff_commit=None,
            )

        if command.logger:
            command.logger(f"Excel created: {output_excel}")

        print(f"Excel created: {output_excel}")

    def handle_put(self, command: PutCommand) -> None:
        """
        Parse Excel into repo structure, update version, commit and push.
        """
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

        ensure_not_diff_excel(input_excel)

        if command.logger:
            command.logger(f"Reading Excel: {input_excel}")
            command.logger("Clearing repo data directory...")

        clear_directory_contents(repo_data_dir)

        if command.logger:
            command.logger("Exporting Excel into repo structure...")

        export_excel_to_repo(
            excel_path=str(input_excel),
            output_dir=str(repo_data_dir),
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