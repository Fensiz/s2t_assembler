from __future__ import annotations

import argparse
from typing import Any

from s2t_tool.application.commands import GetCommand, PutCommand
from s2t_tool.application.service import S2TService
from s2t_tool.infrastructure.config import load_app_config

_service = S2TService()


def handle_get(
    product_name: str,
    branch_arg: str | None,
    version_arg: str | None,
    diff_commit_arg: str | None,
    config: dict[str, Any],
    logger=None,
) -> None:
    _service.handle_get(
        GetCommand(
            product_name=product_name,
            branch_arg=branch_arg,
            version_arg=version_arg,
            diff_commit_arg=diff_commit_arg,
            config=config,
            logger=logger,
        )
    )


def handle_put(
    product_name: str,
    branch_arg: str | None,
    version_arg: str | None,
    keep_version: bool,
    excel_arg: str | None,
    commit_message_arg: str | None,
    config: dict[str, Any],
    logger=None,
) -> None:
    _service.handle_put(
        PutCommand(
            product_name=product_name,
            branch_arg=branch_arg,
            version_arg=version_arg,
            keep_version=keep_version,
            excel_arg=excel_arg,
            commit_message_arg=commit_message_arg,
            config=config,
            logger=logger,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None, help="Path to app config json")

    subparsers = parser.add_subparsers(dest="command", required=True)
    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("product_name")
    get_parser.add_argument("--branch", default=None)
    get_parser.add_argument("--version", default=None)
    get_parser.add_argument("--diff-commit", default=None)

    put_parser = subparsers.add_parser("put")
    put_parser.add_argument("product_name")
    put_parser.add_argument("--branch", default=None)
    put_parser.add_argument("--version", default=None)
    put_parser.add_argument("--keep-version", action="store_true")
    put_parser.add_argument("--excel", default=None)
    put_parser.add_argument("--message", default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_app_config(args.config)

    if args.command == "get":
        handle_get(
            args.product_name,
            args.branch,
            args.version,
            args.diff_commit,
            config=config,
            logger=None,
        )
    elif args.command == "put":
        handle_put(
            args.product_name,
            args.branch,
            args.version,
            args.keep_version,
            args.excel,
            args.message,
            config=config,
            logger=None,
        )
