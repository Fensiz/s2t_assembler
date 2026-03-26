from __future__ import annotations

from s2t_tool.use_cases.commands import GetCommand, PutCommand
from s2t_tool.use_cases.results import GetResult, PutResult
from s2t_tool.use_cases.settings import AppConfig
from s2t_tool.use_cases.get_s2t import GetS2TUseCase
from s2t_tool.use_cases.put_s2t import PutS2TUseCase


class S2TService:
    def __init__(
        self,
        config: AppConfig,
        get_use_case: GetS2TUseCase | None = None,
        put_use_case: PutS2TUseCase | None = None,
    ) -> None:
        self.config = config
        self.get_use_case = get_use_case or GetS2TUseCase(config)
        self.put_use_case = put_use_case or PutS2TUseCase(config)

    def handle_get(self, command: GetCommand) -> GetResult:
        return self.get_use_case.execute(command)

    def handle_put(self, command: PutCommand) -> PutResult:
        return self.put_use_case.execute(command)
