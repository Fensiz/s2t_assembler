from __future__ import annotations

from pathlib import Path

from s2t_tool.shared.files import write_json_file, read_json_file


RECENT_ITEMS_FILE = Path("~/.s2t/recent_items.json").expanduser()


class RecentItemsStore:
    def __init__(self, path: Path = RECENT_ITEMS_FILE) -> None:
        self.path = path

    def load(self) -> list[dict[str, str]]:
        data = read_json_file(self.path, default=[])
        if not isinstance(data, list):
            return []

        result: list[dict[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            product_name = str(item.get("product_name", "")).strip()
            branch = str(item.get("branch", "")).strip()
            if product_name:
                result.append({"product_name": product_name, "branch": branch})

        return result

    def save(self, items: list[dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json_file(self.path, items[:30])

    @staticmethod
    def label(item: dict[str, str]) -> str:
        product_name = item.get("product_name", "")
        branch = item.get("branch", "").strip()
        if branch:
            return f"{product_name} [{branch}]"
        return product_name
