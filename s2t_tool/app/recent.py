from __future__ import annotations

from dataclasses import dataclass

from s2t_tool.use_cases.ports import RecentItemsGateway
from s2t_tool.use_cases.results import RecentItem


@dataclass(frozen=True)
class RecentItemsViewData:
    items: list[RecentItem]
    labels: list[str]


class RecentItemsService:
    def __init__(self, gateway: RecentItemsGateway) -> None:
        self.gateway = gateway

    def build_view_data(self) -> RecentItemsViewData:
        items = self.gateway.load()
        return RecentItemsViewData(
            items=items,
            labels=[self.gateway.label(item) for item in items],
        )

    def add_recent(self, product_name: str, branch: str) -> RecentItemsViewData:
        items = self.gateway.load()
        filtered = [
            item
            for item in items
            if not (item.product_name == product_name and item.branch == branch)
        ]
        filtered.insert(0, RecentItem(product_name=product_name, branch=branch))
        self.gateway.save(filtered)
        return RecentItemsViewData(
            items=filtered,
            labels=[self.gateway.label(item) for item in filtered],
        )

    def get_by_index(self, index: int) -> RecentItem | None:
        items = self.gateway.load()
        if index < 0 or index >= len(items):
            return None
        return items[index]
