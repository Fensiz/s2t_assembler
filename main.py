from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from common import load_json_resource, read_json_file, write_json_file
from git_repo import (
    clear_directory_contents,
    commit_and_push,
    ensure_repo,
    export_commit_tree,
    has_changes_excluding,
)
from reader import export_excel_to_repo
from writer import build_excel_from_repo


# ============================================================
# Constants
# ============================================================

APP_CONFIG_FILE = "app_config.json"
VERSION_JSON = "version.json"


# ============================================================
# File name helpers
# ============================================================

def rename_excel_after_put(
    input_excel: Path,
    product_name: str,
    new_version: str,
    branch: str,
    default_branch: str,
    logger=None,
) -> None:
    """
    Rename Excel file after successful PUT if version changed.

    Example:
        S2T_USL_TEST_v1.2.xlsx -> S2T_USL_TEST_v1.3.xlsx
        S2T_USL_TEST_v1.2_debug.xlsx -> S2T_USL_TEST_v1.3_debug.xlsx
    """
    debug_mode = is_debug_branch(branch, default_branch)
    expected_name = build_branch_excel_filename(product_name, new_version, debug_mode)
    new_path = input_excel.with_name(expected_name)

    if input_excel == new_path:
        return

    try:
        input_excel.rename(new_path)

        if logger:
            logger(f"Excel renamed: {new_path}")

    except Exception as exc:
        if logger:
            logger(f"Failed to rename Excel file: {exc}")


def build_branch_excel_filename(product_name: str, version: str, debug_mode: bool) -> str:
    """
    Build Excel file name for normal export, with optional _debug suffix.
    """
    suffix = "_debug" if debug_mode else ""
    return f"S2T_USL_{product_name.upper()}_v{version}{suffix}.xlsx"


def build_branch_diff_excel_filename(product_name: str, version: str, debug_mode: bool) -> str:
    """
    Build Excel file name for diff export, with optional _debug suffix.
    """
    suffix = "_debug" if debug_mode else ""
    return f"S2T_USL_{product_name.upper()}_v{version}{suffix}_diff.xlsx"


def parse_version_from_excel_filename(excel_path: Path, product_name: str) -> str | None:
    """
    Extract version from file name.

    Supported examples:
        S2T_USL_TEST_v1.2.3.xlsx
        S2T_USL_TEST_v1.2.3_debug.xlsx
        S2T_USL_TEST_v1.2.3_diff.xlsx
        S2T_USL_TEST_v1.2.3_debug_diff.xlsx
    """
    filename = excel_path.name

    pattern = (
        rf"^S2T_USL_{re.escape(product_name.upper())}_v"
        rf"(?P<version>.+?)"
        rf"(?:_debug)?"
        rf"(?:_diff)?"
        rf"\.xlsx$"
    )

    match = re.match(pattern, filename, flags=re.IGNORECASE)
    if not match:
        return None

    version = match.group("version").strip()
    return version or None


def ensure_not_diff_excel(input_excel: Path) -> None:
    """
    Prevent PUT from using diff Excel files.

    Diff Excel contains visual markup and must be treated as read-only.
    """
    if input_excel.name.lower().endswith("_diff.xlsx"):
        raise ValueError(
            "Diff Excel cannot be used for PUT. "
            "Use the normal generated Excel file instead."
        )


# ============================================================
# Config and path helpers
# ============================================================

def load_app_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load app config.

    Priority:
    1. explicit external path
    2. bundled app_config.json resource
    """
    if config_path is None:
        return load_json_resource(APP_CONFIG_FILE)

    path = Path(config_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    # Fallback: config file may be inside bundled archive.
    return load_json_resource(str(config_path))


def expand_user_path(path: str) -> Path:
    """
    Expand '~' and return absolute resolved path.
    """
    return Path(path).expanduser().resolve()


def build_repo_url(base_url: str, product_name: str) -> str:
    """
    Build repo URL from base URL and product name.
    """
    return f"{base_url.rstrip('/')}/{product_name}.git"


def build_local_repo_path(workspace_dir: str, product_name: str) -> Path:
    """
    Build local repo path inside workspace directory.
    """
    return expand_user_path(workspace_dir) / product_name


def branch_prefix_from_default(default_branch: str) -> str:
    """
    Extract branch prefix from configured default branch.

    Examples:
        s2t/master -> s2t/
        master     -> ""
    """
    value = str(default_branch).strip()
    if "/" not in value:
        return ""
    return value.rsplit("/", 1)[0] + "/"


def normalize_branch_name(branch: str, default_branch: str) -> str:
    """
    Normalize branch name using namespace rules derived from default_branch.

    Rules (example default_branch = "s2t/master"):

        test            -> s2t/test
        debug/develop   -> s2t/debug/develop
        s2t/test        -> s2t/test
        s2t/debug/x     -> s2t/debug/x

    Branches starting with another namespace are forbidden:

        feature/test -> error
        hotfix/x     -> error
    """
    value = str(branch).strip()
    if not value:
        return default_branch

    prefix = branch_prefix_from_default(default_branch)

    # No namespace restriction
    if not prefix:
        return value

    # Already valid namespace
    if value.startswith(prefix):
        return value

    # If branch starts with another namespace (feature/, hotfix/, etc)
    if "/" in value and not value.startswith("debug/"):
        raise ValueError(
            f"Branch '{value}' is not allowed. "
            f"Allowed branch names must start with '{prefix}' "
            f"or be inside namespace '{prefix}debug/'."
        )

    # Short name or debug/... branch → expand namespace
    return f"{prefix}{value}"


def branch_tail(branch: str, default_branch: str) -> str:
    """
    Return branch tail after configured namespace prefix.

    Example:
        default_branch = "s2t/master"
        branch = "s2t/debug/test" -> "debug/test"
        branch = "s2t/test"       -> "test"
    """
    prefix = branch_prefix_from_default(default_branch)
    value = str(branch).strip()

    if prefix and value.startswith(prefix):
        return value[len(prefix):]

    return value


def is_debug_branch(branch: str, default_branch: str) -> bool:
    """
    Return True only if debug is the second prefix after base namespace.

    Example for default_branch = "s2t/master":
        s2t/debug/test -> True
        s2t/test       -> False
        s2t/debug      -> False
        debug/test     -> False
        debug          -> False
    """
    tail = branch_tail(branch, default_branch).strip().lower()
    return tail.startswith("debug/")


def resolve_branch(config: dict[str, Any], branch_arg: str | None) -> str:
    """
    Resolve requested branch and enforce namespace from configured default branch.
    """
    default_branch = str(config.get("default_branch", "master")).strip()
    raw_branch = branch_arg or default_branch
    return normalize_branch_name(raw_branch, default_branch)


def resolve_repo_url(config: dict[str, Any], product_name: str) -> str:
    """
    Resolve remote repository URL for product.
    """
    base_url = config["repo_base_url"]
    return build_repo_url(base_url, product_name)


def resolve_repo_dir(config: dict[str, Any], product_name: str) -> Path:
    """
    Resolve local cloned repository directory.
    """
    workspace_dir = config.get("workspace_dir", "~/.s2t")
    return build_local_repo_path(workspace_dir, product_name)


def resolve_repo_data_dir(config: dict[str, Any], repo_dir: Path) -> Path:
    """
    Resolve directory inside repo where S2T data is stored.

    Usually this is the repo root, but a subdirectory can be configured.
    """
    subdir = config.get("repo_data_subdir", ".")
    if subdir in ("", "."):
        return repo_dir
    return repo_dir / subdir


def resolve_excel_output_dir(config: dict[str, Any]) -> Path:
    """
    Resolve directory where generated Excel files are written.
    """
    return expand_user_path(config.get("excel_output_dir", "."))


def resolve_writer_config(config: dict[str, Any]) -> str:
    """
    Resolve writer config file name/path.
    """
    return config.get("writer_config", "writer_config.json")


def ensure_excel_output_dir(path: Path) -> None:
    """
    Ensure output directory for generated Excel exists.
    """
    path.mkdir(parents=True, exist_ok=True)


def find_default_excel_path(
    config: dict[str, Any],
    product_name: str,
    version: str,
    branch: str | None = None,
) -> Path:
    """
    Build output path for regular GET operation.
    """
    output_dir = resolve_excel_output_dir(config)
    ensure_excel_output_dir(output_dir)

    default_branch = str(config.get("default_branch", "master")).strip()
    resolved_branch = branch or default_branch
    debug_mode = is_debug_branch(resolved_branch, default_branch)

    return output_dir / build_branch_excel_filename(product_name, version, debug_mode)


# ============================================================
# Version helpers
# ============================================================

def read_repo_version(version_path: Path) -> str:
    """
    Read version from repo version.json.

    If file or value is missing, return default version.
    """
    payload = read_json_file(version_path, default={}) or {}
    version = payload.get("version")
    return str(version) if version else "0.0.0.0"


def write_repo_version(version_path: Path, version: str) -> None:
    """
    Write version into repo version.json.
    """
    write_json_file(version_path, {"version": version})


def bump_version(version: str) -> str:
    """
    Increment last numeric component of dotted version.

    Examples:
        1        -> 2
        1.2      -> 1.3
        1.2.3.4  -> 1.2.3.5
    """
    parts = [p.strip() for p in str(version).split(".") if p.strip()]
    if not parts:
        return "1"

    try:
        numbers = [int(p) for p in parts]
    except ValueError as exc:
        raise ValueError(f"Invalid version format: {version}") from exc

    numbers[-1] += 1
    return ".".join(str(n) for n in numbers)


def resolve_put_version(
    version_arg: str | None,
    input_excel: Path,
    product_name: str,
    version_path: Path,
) -> str:
    """
    Resolve new version for PUT.

    Priority:
    1. explicit --version
    2. version parsed from input Excel file name, then bumped
    3. version from repo version.json, then bumped
    """
    if version_arg is not None:
        return version_arg

    excel_version = parse_version_from_excel_filename(input_excel, product_name)
    if excel_version is not None:
        return bump_version(excel_version)

    repo_version = read_repo_version(version_path)
    return bump_version(repo_version)


# ============================================================
# Input Excel resolution
# ============================================================

def resolve_input_excel_path(
    config: dict[str, Any],
    product_name: str,
    explicit_excel: str | None,
    explicit_version: str | None,
    branch: str | None = None,
) -> Path:
    """
    Resolve Excel file to use for PUT.

    Priority:
    1. explicit --excel path
    2. generated name from --version
    3. latest matching file in configured Excel output directory

    File name selection respects debug-mode derived from branch name.
    """
    if explicit_excel:
        return Path(explicit_excel).expanduser().resolve()

    excel_dir = resolve_excel_output_dir(config)
    default_branch = str(config.get("default_branch", "master")).strip()
    resolved_branch = branch or default_branch
    debug_mode = is_debug_branch(resolved_branch, default_branch)

    if explicit_version is not None:
        return excel_dir / build_branch_excel_filename(product_name, explicit_version, debug_mode)

    if debug_mode:
        pattern = f"S2T_USL_{product_name.upper()}_v*_debug.xlsx"
    else:
        pattern = f"S2T_USL_{product_name.upper()}_v*.xlsx"

    candidates = sorted(
        [
            p for p in excel_dir.glob(pattern)
            if not p.name.lower().endswith("_diff.xlsx")
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise ValueError(
            f"Excel file not found for product '{product_name}'. "
            f"Expected file like: {pattern} in {excel_dir}"
        )

    return candidates[0]


# ============================================================
# Main operations
# ============================================================

def handle_get(
    product_name: str,
    branch_arg: str | None,
    diff_commit_arg: str | None,
    config: dict[str, Any],
    logger=None,
) -> None:
    """
    Download/refresh repo, build Excel and save it locally.

    If diff_commit_arg is provided, build diff Excel against the given commit.
    """
    branch = resolve_branch(config, branch_arg)
    base_branch = str(config.get("default_branch", "master")).strip()
    debug_mode = is_debug_branch(branch, base_branch)
    repo_url = resolve_repo_url(config, product_name)
    repo_dir = resolve_repo_dir(config, product_name)

    if logger:
        logger(f"Preparing repository: {repo_url}")
        logger(f"Branch: {branch}")

    ensure_repo(repo_url, repo_dir, branch, base_branch, logger=logger)

    repo_data_dir = resolve_repo_data_dir(config, repo_dir)
    version_path = repo_data_dir / VERSION_JSON
    version = read_repo_version(version_path)

    excel_output_dir = resolve_excel_output_dir(config)
    ensure_excel_output_dir(excel_output_dir)

    if diff_commit_arg:
        output_excel = excel_output_dir / build_branch_diff_excel_filename(
            product_name,
            version,
            debug_mode,
        )
    else:
        output_excel = excel_output_dir / build_branch_excel_filename(
            product_name,
            version,
            debug_mode,
        )

    writer_config = resolve_writer_config(config)

    if diff_commit_arg:
        if logger:
            logger(f"Exporting diff tree from commit: {diff_commit_arg}")

        with tempfile.TemporaryDirectory(prefix="s2t_diff_") as temp_dir:
            export_commit_tree(
                repo_dir=repo_dir,
                commit_ref=diff_commit_arg,
                target_dir=Path(temp_dir),
            )

            diff_repo_dir = str(resolve_repo_data_dir(config, Path(temp_dir)))

            if logger:
                logger("Building Excel with diff highlighting...")

            build_excel_from_repo(
                repo_dir=str(repo_data_dir),
                output_excel_path=str(output_excel),
                config_path=writer_config,
                diff_repo_dir=diff_repo_dir,
                diff_commit=diff_commit_arg,
            )
    else:
        if logger:
            logger("Building Excel file...")

        build_excel_from_repo(
            repo_dir=str(repo_data_dir),
            output_excel_path=str(output_excel),
            config_path=writer_config,
            diff_repo_dir=None,
            diff_commit=None,
        )

    if logger:
        logger(f"Excel created: {output_excel}")

    print(f"Excel created: {output_excel}")


def handle_put(
    product_name: str,
    branch_arg: str | None,
    version_arg: str | None,
    excel_arg: str | None,
    commit_message_arg: str | None,
    config: dict[str, Any],
    logger=None,
) -> None:
    """
    Parse Excel into repo structure, update version, commit and push.

    Version is bumped only if real content changes are detected.
    If the only potential change would be version.json itself, nothing is committed.
    """
    branch = resolve_branch(config, branch_arg)
    base_branch = str(config.get("default_branch", "master")).strip()
    repo_url = resolve_repo_url(config, product_name)
    repo_dir = resolve_repo_dir(config, product_name)

    if logger:
        logger(f"Preparing repository: {repo_url}")
        logger(f"Branch: {branch}")

    ensure_repo(repo_url, repo_dir, branch, base_branch, logger=logger)

    repo_data_dir = resolve_repo_data_dir(config, repo_dir)
    version_path = repo_data_dir / VERSION_JSON

    input_excel = resolve_input_excel_path(
        config=config,
        product_name=product_name,
        explicit_excel=excel_arg,
        explicit_version=version_arg,
        branch=branch,
    )

    if not input_excel.exists():
        raise ValueError(f"Excel file not found: {input_excel}")

    ensure_not_diff_excel(input_excel)

    if logger:
        logger(f"Reading Excel: {input_excel}")
        logger("Clearing repo data directory...")

    # Remove previous generated artifacts so deletions from Excel are reflected in git.
    clear_directory_contents(repo_data_dir)

    if logger:
        logger("Exporting Excel into repo structure...")

    export_excel_to_repo(
        excel_path=str(input_excel),
        output_dir=str(repo_data_dir),
    )

    version_rel_path = version_path.relative_to(repo_dir)

    # If there are no real content changes (excluding version.json), do nothing.
    if not has_changes_excluding(repo_dir, excluded_paths=[version_rel_path]):
        if logger:
            logger("No content changes detected. Version was not bumped.")
            logger("Nothing to commit.")
        print("No content changes detected. Nothing to commit.")
        return

    # Only now resolve and write new version.
    new_version = resolve_put_version(
        version_arg=version_arg,
        input_excel=input_excel,
        product_name=product_name,
        version_path=version_path,
    )

    write_repo_version(version_path, new_version)

    commit_message = (
        commit_message_arg.strip()
        if commit_message_arg and commit_message_arg.strip()
        else f"Update S2T for {product_name} to version {new_version}"
    )

    if logger:
        logger("Committing and pushing changes...")

    commit_and_push(repo_dir=repo_dir, branch=branch, message=commit_message, logger=logger)

    rename_excel_after_put(
        input_excel=input_excel,
        product_name=product_name,
        new_version=new_version,
        branch=branch,
        default_branch=base_branch,
        logger=logger,
    )

    if logger:
        logger(f"Repo updated: {repo_dir}")
        logger(f"New version: {new_version}")

    print(f"Repo updated: {repo_dir}")
    print(f"New version: {new_version}")


# ============================================================
# CLI
# ============================================================

def main() -> None:
    """
    CLI entry point.

    Commands:
        get <product_name>
        put <product_name>
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=None,
        help="Path to app config json",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("product_name")
    get_parser.add_argument("--branch", default=None)
    get_parser.add_argument("--diff-commit", default=None)

    put_parser = subparsers.add_parser("put")
    put_parser.add_argument("product_name")
    put_parser.add_argument("--branch", default=None)
    put_parser.add_argument("--version", default=None)
    put_parser.add_argument("--excel", default=None)
    put_parser.add_argument("--message", default=None)

    args = parser.parse_args()
    config = load_app_config(args.config)

    if args.command == "get":
        handle_get(
            product_name=args.product_name,
            branch_arg=args.branch,
            diff_commit_arg=args.diff_commit,
            config=config,
            logger=None,
        )
    elif args.command == "put":
        handle_put(
            product_name=args.product_name,
            branch_arg=args.branch,
            version_arg=args.version,
            excel_arg=args.excel,
            commit_message_arg=args.message,
            config=config,
            logger=None,
        )


if __name__ == "__main__":
    main()