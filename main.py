from __future__ import annotations

import argparse

from main_config import load_app_config
from main_models import GetCommand, PutCommand
from main_service import S2TService


def handle_get(
    product_name: str,
    branch_arg: str | None,
    diff_commit_arg: str | None,
    config: dict,
    logger=None,
) -> None:
    service = S2TService()
    service.handle_get(
        GetCommand(
            product_name=product_name,
            branch_arg=branch_arg,
            diff_commit_arg=diff_commit_arg,
            config=config,
            logger=logger,
        )
    )


def handle_put(
    product_name: str,
    branch_arg: str | None,
    version_arg: str | None,
    excel_arg: str | None,
    commit_message_arg: str | None,
    config: dict,
    logger=None,
) -> None:
    service = S2TService()
    service.handle_put(
        PutCommand(
            product_name=product_name,
            branch_arg=branch_arg,
            version_arg=version_arg,
            excel_arg=excel_arg,
            commit_message_arg=commit_message_arg,
            config=config,
            logger=logger,
        )
    )


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