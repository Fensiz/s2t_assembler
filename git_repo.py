from __future__ import annotations

import shutil
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path


# ============================================================
# Low-level git helpers
# ============================================================

def run_git(args: list[str], cwd: Path | None = None, log=None) -> str:
    """
    Execute git command and return collected output.

    If `log` callback is provided, stream git output line-by-line to it.
    """
    cmd = ["git"] + args

    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines: list[str] = []

    assert process.stdout is not None

    for line in process.stdout:
        line = line.rstrip()
        output_lines.append(line)

        if log:
            log(line)

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(
            f"Git command failed: {' '.join(cmd)}\n"
            + "\n".join(output_lines)
        )

    return "\n".join(output_lines)


def remote_branch_exists(repo_url: str, branch: str) -> bool:
    """
    Check whether branch exists in remote repository.

    Uses:
        git ls-remote --heads <repo_url> <branch>
    """
    result = subprocess.run(
        ["git", "ls-remote", "--heads", repo_url, branch],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Git ls-remote failed for {repo_url} {branch}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return bool(result.stdout.strip())


def local_remote_branch_exists(repo_dir: Path, branch: str) -> bool:
    """
    Check whether origin/<branch> exists in already cloned local repo.
    """
    output = run_git(["branch", "-r", "--list", f"origin/{branch}"], cwd=repo_dir)
    return bool(output.strip())


def local_branch_exists(repo_dir: Path, branch: str) -> bool:
    """
    Check whether local branch exists.
    """
    output = run_git(["branch", "--list", branch], cwd=repo_dir)
    return bool(output.strip())


# ============================================================
# Filesystem cleanup helpers
# ============================================================

def clear_directory_contents(path: Path) -> None:
    """
    Remove all contents of a directory except .git.

    Used before regenerating repo artifacts so deleted objects in Excel
    are also deleted in git working tree.
    """
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return

    for child in path.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def clear_worktree_except_git(repo_dir: Path) -> None:
    """
    Remove all working tree files except .git directory.
    """
    for child in repo_dir.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


# ============================================================
# Sync helpers
# ============================================================

def reset_and_clean_to_remote(repo_dir: Path, branch: str, logger=None) -> None:
    """
    Reset local working tree to exact remote branch state and remove untracked files.
    """
    run_git(["reset", "--hard", f"origin/{branch}"], cwd=repo_dir, log=logger)
    run_git(["clean", "-fd"], cwd=repo_dir, log=logger)


# ============================================================
# Branch creation / switching logic
# ============================================================

def create_orphan_branch(repo_dir: Path, branch: str, logger=None) -> None:
    """
    Recreate branch as orphan.

    This is used only when we are creating the base branch itself and
    it does not exist in remote repository.
    """
    # If branch already exists locally, delete it first.
    if local_branch_exists(repo_dir, branch):
        current_branch = run_git(["branch", "--show-current"], cwd=repo_dir, log=logger)
        if current_branch == branch:
            # Move away from branch before deleting it.
            run_git(["switch", "--detach"], cwd=repo_dir, log=logger)
        run_git(["branch", "-D", branch], cwd=repo_dir, log=logger)

    # Create orphan branch.
    run_git(["switch", "--orphan", branch], cwd=repo_dir, log=logger)

    # Remove tracked files from index if index is not empty.
    # In a completely empty repo this may fail, so ignore it.
    try:
        run_git(["rm", "-rf", "--cached", "."], cwd=repo_dir, log=logger)
    except RuntimeError:
        pass

    # Remove cloned files from working tree.
    clear_worktree_except_git(repo_dir)


def create_branch_from_base(repo_dir: Path, branch: str, base_branch: str, logger=None) -> None:
    """
    Create a new local branch from base_branch.

    Used when target branch does not exist, but base branch exists.
    """
    if not local_remote_branch_exists(repo_dir, base_branch):
        raise RuntimeError(
            f"Target branch '{branch}' does not exist, and base branch "
            f"'{base_branch}' was not found in remote repository."
        )

    # Switch to local base branch if present, otherwise create local tracking branch.
    if local_branch_exists(repo_dir, base_branch):
        run_git(["switch", base_branch], cwd=repo_dir, log=logger)
    else:
        run_git(["switch", "-c", base_branch, f"origin/{base_branch}"], cwd=repo_dir, log=logger)

    # Make sure base branch content matches remote exactly.
    reset_and_clean_to_remote(repo_dir, base_branch, logger)

    # If branch somehow exists locally, recreate it cleanly.
    if local_branch_exists(repo_dir, branch):
        current_branch = run_git(["branch", "--show-current"], cwd=repo_dir, log=logger)
        if current_branch == branch:
            run_git(["switch", "--detach"], cwd=repo_dir, log=logger)
        run_git(["branch", "-D", branch], cwd=repo_dir, log=logger)

    run_git(["switch", "-c", branch], cwd=repo_dir, log=logger)


# ============================================================
# Clone / sync logic
# ============================================================

def clone_repo(repo_url: str, target_dir: Path, branch: str, base_branch: str, logger=None) -> None:
    """
    Clone repository into target_dir and prepare requested branch.

    Rules:
    - if target branch exists remotely -> clone that branch directly
    - if target branch does not exist:
        - if target branch == base_branch -> clone repo and create orphan branch
        - otherwise create target branch from existing base_branch
    """
    if remote_branch_exists(repo_url, branch):
        run_git(["clone", "--branch", branch, repo_url, str(target_dir)], log=logger)
        return

    # If we are creating the base branch itself and it does not exist,
    # create it as orphan.
    if branch == base_branch:
        run_git(["clone", repo_url, str(target_dir)], log=logger)
        create_orphan_branch(target_dir, branch, logger)
        return

    # Otherwise base branch must exist.
    if not remote_branch_exists(repo_url, base_branch):
        raise RuntimeError(
            f"Target branch '{branch}' does not exist, and base branch "
            f"'{base_branch}' was not found in remote repository."
        )

    # Clone from base branch and then create new branch from it.
    run_git(["clone", "--branch", base_branch, repo_url, str(target_dir)], log=logger)
    create_branch_from_base(target_dir, branch, base_branch, logger)


def hard_reset_to_remote(repo_dir: Path, branch: str, base_branch: str, logger=None) -> None:
    """
    Bring already cloned repo to clean state.

    Rules:
    - if target branch exists remotely -> switch to it and hard reset to origin/<branch>
    - if target branch does not exist:
        - if target branch == base_branch -> create orphan branch
        - otherwise create branch from base_branch
    """
    run_git(["fetch", "origin"], cwd=repo_dir, log=logger)

    # Branch exists in remote -> sync local branch to remote state.
    if local_remote_branch_exists(repo_dir, branch):
        if local_branch_exists(repo_dir, branch):
            run_git(["switch", branch], cwd=repo_dir, log=logger)
        else:
            run_git(["switch", "-c", branch, f"origin/{branch}"], cwd=repo_dir, log=logger)

        reset_and_clean_to_remote(repo_dir, branch, logger)
        return

    # Branch does not exist remotely.
    if branch == base_branch:
        create_orphan_branch(repo_dir, branch, logger)
        return

    create_branch_from_base(repo_dir, branch, base_branch, logger)


def ensure_repo(repo_url: str, repo_dir: Path, branch: str, base_branch: str, logger=None) -> None:
    """
    Ensure local repo exists and is prepared on requested branch.
    """
    if not repo_dir.exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        clone_repo(repo_url, repo_dir, branch, base_branch, logger)
    else:
        hard_reset_to_remote(repo_dir, branch, base_branch, logger)


# ============================================================
# Commit / push helpers
# ============================================================

def has_changes(repo_dir: Path) -> bool:
    """
    Return True if repo has staged/unstaged/untracked changes.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def has_changes_excluding(repo_dir: Path, excluded_paths: list[Path] | None = None) -> bool:
    """
    Return True if repo has changes excluding selected repo-relative paths.
    """
    excluded_rel = {
        str(path).replace("\\", "/").lstrip("./")
        for path in (excluded_paths or [])
    }

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Git status failed in {repo_dir}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        # формат porcelain: "XY path"
        path_text = line[3:].strip().replace("\\", "/")

        # для rename строк формат может быть "old -> new"
        if " -> " in path_text:
            old_path, new_path = path_text.split(" -> ", 1)
            old_path = old_path.strip()
            new_path = new_path.strip()

            if old_path in excluded_rel and new_path in excluded_rel:
                continue

            return True

        if path_text in excluded_rel:
            continue

        return True

    return False


def commit_all(repo_dir: Path, message: str, logger=None) -> None:
    """
    Stage all changes (including deletions) and create commit.
    """
    run_git(["add", "-A"], cwd=repo_dir, log=logger)
    run_git(["commit", "-m", message], cwd=repo_dir, log=logger)


def push(repo_dir: Path, branch: str, logger=None) -> None:
    """
    Push current branch to origin and set upstream if needed.
    """
    run_git(["push", "-u", "origin", branch], cwd=repo_dir, log=logger)


def commit_and_push(repo_dir: Path, branch: str, message: str, logger=None) -> None:
    """
    Commit and push repo only if there are changes.
    """
    if not has_changes(repo_dir):
        if logger:
            logger("No changes to commit")
        else:
            print("No changes to commit")
        return

    commit_all(repo_dir, message, logger)
    push(repo_dir, branch, logger)


# ============================================================
# Export helpers
# ============================================================

def export_commit_tree(repo_dir: Path, commit_ref: str, target_dir: Path) -> None:
    """
    Export repository tree for a given commit into target_dir.

    Used for Excel diff mode:
    current repo vs repo at <commit_ref>.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["git", "archive", commit_ref],
        cwd=repo_dir,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Git archive failed for commit '{commit_ref}'\n"
            f"stdout:\n{result.stdout.decode(errors='ignore')}\n"
            f"stderr:\n{result.stderr.decode(errors='ignore')}"
        )

    with tarfile.open(fileobj=BytesIO(result.stdout), mode="r:") as archive:
        archive.extractall(target_dir)