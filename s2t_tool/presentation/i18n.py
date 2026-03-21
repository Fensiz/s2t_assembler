from __future__ import annotations

import locale


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "S2T Tool",
        "product": "Product",
        "branch_or_commit": "Branch / commit",
        "commit_message": "Commit message",
        "version_override": "Version",
        "diff_against_commit": "Diff commit",
        "actions": "Actions",
        "recent_targets": "Recent",
        "execution_log": "Log",
        "get_export": "Get",
        "put_publish": "Send",
        "open_excel_folder": "Folder",
        "open_after_get": "Open after GET",
        "version_short": "v{version}",
        "version_update": "v{current} -> {latest}",
        "version_available": "v{current} update",
    },
    "ru": {
        "app_title": "S2T Tool",
        "product": "Продукт",
        "branch_or_commit": "Ветка / коммит",
        "commit_message": "Сообщение коммита",
        "version_override": "Версия",
        "diff_against_commit": "Diff коммит",
        "actions": "Действия",
        "recent_targets": "Недавние",
        "execution_log": "Лог",
        "get_export": "Получить",
        "put_publish": "Отправить",
        "open_excel_folder": "Папка",
        "open_after_get": "Открывать после получения",
        "version_short": "v{version}",
        "version_update": "v{current} -> {latest}",
        "version_available": "v{current} обновление",
    },
}


def detect_language() -> str:
    language, _encoding = locale.getlocale()
    normalized = (language or "").lower()
    if normalized.startswith("ru"):
        return "ru"
    return "en"


def tr(key: str, language: str, **kwargs: object) -> str:
    catalog = STRINGS.get(language, STRINGS["en"])
    template = catalog.get(key, STRINGS["en"].get(key, key))
    return template.format(**kwargs)
