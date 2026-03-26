from __future__ import annotations

from s2t_tool.use_cases.commands import GetCommand, PutCommand
from s2t_tool.use_cases.results import GetResult, PutResult
from s2t_tool.use_cases.service import S2TService


class AppOperationsService:
    def __init__(self, service: S2TService) -> None:
        self.service = service

    def run_get(
        self,
        *,
        product_name: str,
        branch: str | None,
        version: str | None,
        diff_commit: str | None,
        logger=None,
    ) -> GetResult:
        return self.service.handle_get(
            GetCommand(
                product_name=product_name,
                branch_arg=branch,
                version_arg=version,
                diff_commit_arg=diff_commit,
                logger=logger,
            )
        )

    def run_put(
        self,
        *,
        product_name: str,
        branch: str | None,
        version: str | None,
        keep_version: bool,
        format_sql: bool,
        excel_path: str | None,
        commit_message: str | None,
        logger=None,
    ) -> PutResult:
        return self.service.handle_put(
            PutCommand(
                product_name=product_name,
                branch_arg=branch,
                version_arg=version,
                keep_version=keep_version,
                format_sql=format_sql,
                excel_arg=excel_path,
                commit_message_arg=commit_message,
                logger=logger,
            )
        )
