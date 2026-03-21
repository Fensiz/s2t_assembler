from __future__ import annotations

import re
from typing import Any


COMMIT_REF_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


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

    if not prefix:
        return value

    if value.startswith(prefix):
        return value

    if "/" in value and not value.startswith("debug/"):
        raise ValueError(
            f"Branch '{value}' is not allowed. "
            f"Allowed branch names must start with '{prefix}' "
            f"or be inside namespace '{prefix}debug/'."
        )

    return f"{prefix}{value}"


def branch_tail(branch: str, default_branch: str) -> str:
    """
    Return branch tail after configured namespace prefix.
    """
    prefix = branch_prefix_from_default(default_branch)
    value = str(branch).strip()

    if prefix and value.startswith(prefix):
        return value[len(prefix):]

    return value


def is_debug_branch(branch: str, default_branch: str) -> bool:
    """
    Return True only if debug is the second prefix after base namespace.
    """
    tail = branch_tail(branch, default_branch).strip().lower()
    return tail.startswith("debug/")


def is_commit_ref(value: str | None) -> bool:
    if value is None:
        return False
    return bool(COMMIT_REF_RE.fullmatch(str(value).strip()))


def resolve_branch(config: dict[str, Any], branch_arg: str | None) -> str:
    """
    Resolve requested branch and enforce namespace from configured default branch.
    """
    default_branch = str(config.get("default_branch", "master")).strip()
    raw_branch = branch_arg or default_branch
    return normalize_branch_name(raw_branch, default_branch)
