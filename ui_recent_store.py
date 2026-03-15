from __future__ import annotations

from pathlib import Path

from common import read_json_file, write_json_file


RECENT_ITEMS_FILE = Path("~/.s2t/recent_items.json").expanduser()


class RecentItemsStore:
    def __init__(self, path: Path = RECENT_ITEMS_FILE) -> None:
        self.path = path

    def load(self) -> list[dict[str, str]]:
        """
        Load recent product/branch pairs from local history file.

        Invalid entries are ignored.
        """
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
                result.append(
                    {
                        "product_name": product_name,
                        "branch": branch,
                    }
                )

        return result

    def save(self, items: list[dict[str, str]]) -> None:
        """
        Save recent product/branch pairs to local history file.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json_file(self.path, items[:30])

    @staticmethod
    def label(item: dict[str, str]) -> str:
        """
        Build user-friendly label for recent items listbox.
        """
        product_name = item.get("product_name", "")
        branch = item.get("branch", "").strip()

        if branch:
            return f"{product_name} [{branch}]"
        return product_name