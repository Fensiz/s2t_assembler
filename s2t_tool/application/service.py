from __future__ import annotations

from s2t_tool.application.commands import GetCommand, PutCommand
from s2t_tool.application.use_cases.get_s2t import GetS2TUseCase
from s2t_tool.application.use_cases.put_s2t import PutS2TUseCase


class S2TService:
    def __init__(
        self,
        get_use_case: GetS2TUseCase | None = None,
        put_use_case: PutS2TUseCase | None = None,
    ) -> None:
        self.get_use_case = get_use_case or GetS2TUseCase()
        self.put_use_case = put_use_case or PutS2TUseCase()

    def handle_get(self, command: GetCommand) -> None:
        self.get_use_case.execute(command)

    def handle_put(self, command: PutCommand) -> None:
        self.put_use_case.execute(command)
