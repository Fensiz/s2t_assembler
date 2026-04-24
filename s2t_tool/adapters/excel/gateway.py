from __future__ import annotations

from pathlib import Path

from s2t_tool.shared.constants import Logger
from s2t_tool.use_cases.ports import ExcelGateway
from s2t_tool.adapters.excel.reader import export_excel_to_repo
from s2t_tool.adapters.excel.writer import build_excel_from_repo


class OpenpyxlExcelAdapter(ExcelGateway):
    def build_excel(
        self,
        repo_dir: Path,
        output_excel: Path,
        writer_config: str,
        diff_repo_dir: Path | None,
        diff_ref: str | None,
        logger: Logger | None = None,
    ) -> None:
        build_excel_from_repo(
            repo_dir=str(repo_dir),
            output_excel_path=str(output_excel),
            config_path=writer_config,
            diff_repo_dir=str(diff_repo_dir) if diff_repo_dir else None,
            diff_commit=diff_ref,
            logger=logger,
        )

    def export_excel_to_repo(
        self,
        excel_path: Path,
        output_dir: Path,
        format_sql: bool,
        logger: Logger | None = None,
    ) -> None:
        export_excel_to_repo(
            excel_path=str(excel_path),
            output_dir=str(output_dir),
            format_sql=format_sql,
            logger=logger,
        )
