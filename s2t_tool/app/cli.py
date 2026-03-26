from __future__ import annotations

import argparse

from s2t_tool.use_cases.commands import GetCommand, PutCommand
from s2t_tool.app.bootstrap import build_container


def handle_get(
    service,
    product_name: str,
    branch_arg: str | None,
    version_arg: str | None,
    diff_commit_arg: str | None,
    logger=None,
) -> None:
    service.handle_get(
        GetCommand(
            product_name=product_name,
            branch_arg=branch_arg,
            version_arg=version_arg,
            diff_commit_arg=diff_commit_arg,
            logger=logger,
        )
    )


def handle_put(
    service,
    product_name: str,
    branch_arg: str | None,
    version_arg: str | None,
    keep_version: bool,
    format_sql: bool,
    excel_arg: str | None,
    commit_message_arg: str | None,
    logger=None,
) -> None:
    service.handle_put(
        PutCommand(
            product_name=product_name,
            branch_arg=branch_arg,
            version_arg=version_arg,
            keep_version=keep_version,
            format_sql=format_sql,
            excel_arg=excel_arg,
            commit_message_arg=commit_message_arg,
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
    put_parser.add_argument("--format-sql", action="store_true")
    put_parser.add_argument("--excel", default=None)
    put_parser.add_argument("--message", default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    container = build_container(args.config)

    if args.command == "get":
        handle_get(
            container.service,
            args.product_name,
            args.branch,
            args.version,
            args.diff_commit,
            logger=None,
        )
    elif args.command == "put":
        handle_put(
            container.service,
            args.product_name,
            args.branch,
            args.version,
            args.keep_version,
            args.format_sql,
            args.excel,
            args.message,
            logger=None,
        )
