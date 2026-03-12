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

def build_excel_filename(product_name: str, version: str) -> str:
    """
    Build standard Excel file name for normal export.
    """
    return f"S2T_USL_{product_name.upper()}_v{version}.xlsx"


def build_diff_excel_filename(product_name: str, version: str) -> str:
    """
    Build Excel file name for diff export.
    """
    return f"S2T_USL_{product_name.upper()}_v{version}_diff.xlsx"


def parse_version_from_excel_filename(excel_path: Path, product_name: str) -> str | None:
    """
    Extract version from file name like:
        S2T_USL_<PRODUCT_NAME>_v1.2.3.xlsx
    """
    filename = excel_path.name
    pattern = rf"^S2T_USL_{re.escape(product_name.upper())}_v(.+)\.xlsx$"
    match = re.match(pattern, filename, flags=re.IGNORECASE)

    if not match:
        return None

    version = match.group(1).strip()
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
    Normalize branch name using namespace rules from configured default branch.

    Rules:
    - if branch is empty -> use default_branch
    - if default_branch has prefix like 's2t/', then:
        - 'master'       -> 's2t/master'
        - 'test'         -> 's2t/test'
        - 's2t/test'     -> 's2t/test'
        - 'feature/test' -> error
    - if default_branch has no prefix, return branch as is
    """
    value = str(branch).strip()
    if not value:
        return default_branch

    prefix = branch_prefix_from_default(default_branch)

    # No namespace in default branch -> no special restrictions.
    if not prefix:
        return value

    # Already in allowed namespace.
    if value.startswith(prefix):
        return value

    # Any other prefixed branch is forbidden.
    if "/" in value:
        raise ValueError(
            f"Branch '{value}' is not allowed. "
            f"Allowed branch names must start with '{prefix}' "
            f"or be short names without '/'."
        )

    # Short name -> expand into configured namespace.
    return f"{prefix}{value}"


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
) -> Path:
    """
    Build output path for regular GET operation.
    """
    output_dir = resolve_excel_output_dir(config)
    ensure_excel_output_dir(output_dir)
    return output_dir / build_excel_filename(product_name, version)


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
) -> Path:
    """
    Resolve Excel file to use for PUT.

    Priority:
    1. explicit --excel path
    2. generated name from --version
    3. latest matching file in configured Excel output directory
    """
    if explicit_excel:
        return Path(explicit_excel).expanduser().resolve()

    excel_dir = resolve_excel_output_dir(config)

    if explicit_version is not None:
        return excel_dir / build_excel_filename(product_name, explicit_version)

    pattern = f"S2T_USL_{product_name.upper()}_v*.xlsx"
    candidates = sorted(
        excel_dir.glob(pattern),
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
        output_excel = excel_output_dir / build_diff_excel_filename(product_name, version)
    else:
        output_excel = excel_output_dir / build_excel_filename(product_name, version)

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
    )

    if not input_excel.exists():
        raise ValueError(f"Excel file not found: {input_excel}")

    ensure_not_diff_excel(input_excel)

    if logger:
        logger(f"Reading Excel: {input_excel}")

    # Resolve new version before cleaning repo data.
    new_version = resolve_put_version(
        version_arg=version_arg,
        input_excel=input_excel,
        product_name=product_name,
        version_path=version_path,
    )

    if logger:
        logger("Clearing repo data directory...")

    # Remove previous generated artifacts so deletions from Excel are reflected in git.
    clear_directory_contents(repo_data_dir)

    if logger:
        logger("Exporting Excel into repo structure...")

    export_excel_to_repo(
        excel_path=str(input_excel),
        output_dir=str(repo_data_dir),
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