from __future__ import annotations

from s2t_tool.use_cases.ports import RecentItemsGateway
from s2t_tool.use_cases.results import RecentItem
from s2t_tool.adapters.system.recent_store import RecentItemsStore


class RecentItemsAdapter(RecentItemsGateway):
    def __init__(self, store: RecentItemsStore | None = None) -> None:
        self.store = store or RecentItemsStore()

    def load(self) -> list[RecentItem]:
        return [RecentItem(**item) for item in self.store.load()]

    def save(self, items: list[RecentItem]) -> None:
        self.store.save(
            [
                {"product_name": item.product_name, "branch": item.branch}
                for item in items
            ]
        )

    def label(self, item: RecentItem) -> str:
        return self.store.label(
            {"product_name": item.product_name, "branch": item.branch}
        )
