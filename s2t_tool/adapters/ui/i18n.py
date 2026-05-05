from __future__ import annotations

import locale
import os
import re


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
        "keep_version": "Keep version",
        "format_sql": "Format SQL",
        "version_short": "v{version}",
        "version_update": "v{current} -> {latest}",
        "version_available": "v{current} update",
        "error_title": "Error",
        "update_title": "Update",
        "managed_runtime_notice": "The application was started from an external location.\n\nIt will be moved to the managed S2T directory, a desktop shortcut will be created, and the managed copy will be started.",
        "managed_runtime_status": "Installing managed application copy from: {path}",
        "managed_runtime_ready": "Managed application copy is ready. Restarting from: {path}",
        "managed_runtime_failed": "Failed to prepare managed application copy:\n{error}",
        "initial_setup_skipped": "Initial setup skipped: {error}",
        "action_failed_title": "{action} failed",
        "action_failed_status": "{action} failed:\n{error}",
        "product_name_required": "Product name is required",
        "product_name_invalid": "Product name must contain only letters, digits, underscores and hyphens.",
        "version_invalid": "Version must contain only digits and dots (e.g. 1.2.3).",
        "put_requires_branch": "PUT requires a branch name. Commit hash can be used only for GET.",
        "opened_folder": "Opened folder: {path}",
        "open_folder_failed": "Open folder failed:\n{error}",
        "open_folder_failed_title": "Open folder failed",
        "running_get": "Running GET for '{product}'...",
        "running_get_diff": "Running GET for '{product}' with diff against '{commit}'...",
        "running_put": "Running PUT for '{product}'...",
        "get_completed": "GET completed for '{product}'",
        "get_completed_diff": "GET completed for '{product}' with diff",
        "put_completed": "PUT completed for '{product}'",
        "created_file": "Created: {path}",
        "opened_file": "Opened: {path}",
        "open_failed": "Open failed: {error}",
        "update_available_status": "Update available: {version}",
        "update_check_failed_status": "Failed to check updates: {error}",
        "already_latest_version": "You already have the latest version installed.",
        "new_version_available": "New version available: {version}.\n\nInstall update now?",
        "starting_update": "Starting update...",
        "update_check_failed": "Failed to check update:\n{error}",
        "starting_new_version": "Starting new version: {command}",
        "new_version_started": "New version started. Closing current window...",
        "restart_failed": "Failed to restart application:\n{error}",
        "restart_error_status": "Restart error: {error}",
        "update_installed_restart": "Update installed. Restarting application...",
        "update_install_failed": "Failed to install update:\n{error}",
        "update_error_status": "Update error: {error}",
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
        "keep_version": "Оставить\nверсию",
        "format_sql": "Форматировать\nSQL",
        "version_short": "v{version}",
        "version_update": "v{current} -> {latest}",
        "version_available": "v{current} обновление",
        "error_title": "Ошибка",
        "update_title": "Обновление",
        "managed_runtime_notice": "Приложение запущено не из целевой директории.\n\nСейчас оно будет перенесено в управляемую папку S2T, будет создан ярлык на рабочем столе и запущена целевая копия.",
        "managed_runtime_status": "Подготавливаю управляемую копию приложения из: {path}",
        "managed_runtime_ready": "Управляемая копия приложения готова. Перезапуск из: {path}",
        "managed_runtime_failed": "Не удалось подготовить управляемую копию приложения:\n{error}",
        "initial_setup_skipped": "Первичная настройка пропущена: {error}",
        "action_failed_title": "{action}: ошибка",
        "action_failed_status": "{action}: ошибка\n{error}",
        "product_name_required": "Нужно указать продукт",
        "product_name_invalid": "Имя продукта должно содержать только буквы, цифры, подчёркивания и дефисы.",
        "version_invalid": "Версия должна содержать только цифры и точки (например, 1.2.3).",
        "put_requires_branch": "Для отправки нужна ветка. Хеш коммита можно использовать только для получения.",
        "opened_folder": "Открыта папка: {path}",
        "open_folder_failed": "Не удалось открыть папку:\n{error}",
        "open_folder_failed_title": "Не удалось открыть папку",
        "running_get": "Получение '{product}'...",
        "running_get_diff": "Получение '{product}' с diff относительно '{commit}'...",
        "running_put": "Отправка '{product}'...",
        "get_completed": "Получение '{product}' завершено",
        "get_completed_diff": "Получение '{product}' с diff завершено",
        "put_completed": "Отправка '{product}' завершена",
        "created_file": "Создан файл: {path}",
        "opened_file": "Открыт файл: {path}",
        "open_failed": "Не удалось открыть: {error}",
        "update_available_status": "Доступно обновление: {version}",
        "update_check_failed_status": "Не удалось проверить обновления: {error}",
        "already_latest_version": "У вас уже установлена последняя версия.",
        "new_version_available": "Доступна новая версия: {version}.\n\nУстановить обновление сейчас?",
        "starting_update": "Начинаю обновление...",
        "update_check_failed": "Не удалось проверить обновление:\n{error}",
        "starting_new_version": "Запускаю новую версию: {command}",
        "new_version_started": "Новая версия запущена. Закрываю текущее окно...",
        "restart_failed": "Не удалось перезапустить приложение:\n{error}",
        "restart_error_status": "Ошибка перезапуска: {error}",
        "update_installed_restart": "Обновление установлено. Перезапуск приложения...",
        "update_install_failed": "Не удалось установить обновление:\n{error}",
        "update_error_status": "Ошибка обновления: {error}",
    },
}


def detect_language(preferred: str | None = None) -> str:
    candidates = [
        preferred,
        os.environ.get("S2T_TOOL_LANG"),
        os.environ.get("LC_ALL"),
        os.environ.get("LC_MESSAGES"),
        os.environ.get("LANG"),
    ]

    try:
        language, _encoding = locale.getlocale()
        candidates.append(language)
    except Exception:
        pass

    try:
        language, _encoding = locale.getdefaultlocale()
        candidates.append(language)
    except Exception:
        pass

    for candidate in candidates:
        normalized = str(candidate or "").lower()
        if normalized.startswith("ru"):
            return "ru"
        if normalized.startswith("en"):
            return "en"

    return "ru"


def tr(key: str, language: str, **kwargs: object) -> str:
    catalog = STRINGS.get(language, STRINGS["en"])
    template = catalog.get(key, STRINGS["en"].get(key, key))
    return template.format(**kwargs)


def localize_runtime_message(message: str, language: str) -> str:
    if language != "ru":
        return message

    patterns: list[tuple[re.Pattern[str], str | callable]] = [
        (
            re.compile(r"^Source LG sheet is empty$"),
            "Лист Source LG пуст.",
        ),
        (
            re.compile(r"^Missing columns in Source LG: (?P<columns>.+)$"),
            lambda m: f"На листе Source LG отсутствуют обязательные колонки: {m.group('columns')}",
        ),
        (
            re.compile(r"^Pre-transforms sheet must contain at least double header$"),
            "На листе Pre-transforms должен быть двойной заголовок.",
        ),
        (
            re.compile(r"^Pre-transforms row has empty target table$"),
            "На листе Pre-transforms есть строка без target table.",
        ),
        (
            re.compile(r"^Joins must contain double header and data rows$"),
            "Лист Joins должен содержать двойной заголовок и строки с данными.",
        ),
        (
            re.compile(r"^Joins row must contain table_name and load_code$"),
            "На листе Joins в строке должны быть заполнены table_name и load_code.",
        ),
        (
            re.compile(r"^Mappings sheet must contain header and data rows$"),
            "Лист Mappings должен содержать заголовок и строки с данными.",
        ),
        (
            re.compile(r"^Mappings row must contain load_code, table_name, attribute_code$"),
            "На листе Mappings в строке должны быть заполнены load_code, table_name и attribute_code.",
        ),
        (
            re.compile(
                r"^Conflicting attribute_name inside table '(?P<table>[^']+)' "
                r"for attribute_code '(?P<code>[^']+)': (?P<names>.+)$"
            ),
            lambda m: (
                f"Лист Mappings: для таблицы '{m.group('table')}' "
                f"у атрибута '{m.group('code')}' заданы разные описания: {m.group('names')}"
            ),
        ),
        (
            re.compile(
                r"^Sheet '(?P<sheet>[^']+)' not found in (?P<path>.+)\. "
                r"Available sheets: (?P<available>.+)$"
            ),
            lambda m: (
                f"Не найден лист '{m.group('sheet')}' в файле {m.group('path')}. "
                f"Доступные листы: {m.group('available')}"
            ),
        ),
        (
            re.compile(
                r"^Branch '(?P<branch>[^']+)' is not allowed\. "
                r"Allowed branch names must start with '(?P<prefix>[^']+)' "
                r"or be inside namespace '(?P<debug>[^']+)'\.$"
            ),
            lambda m: (
                f"Ветка '{m.group('branch')}' недопустима. "
                f"Имя ветки должно начинаться с '{m.group('prefix')}' "
                f"или находиться в пространстве '{m.group('debug')}'."
            ),
        ),
        (
            re.compile(r"^Excel file not found: (?P<path>.+)$"),
            lambda m: f"Excel-файл не найден: {m.group('path')}",
        ),
        (
            re.compile(
                r"^Excel file not found for product '(?P<product>[^']+)'\. "
                r"Expected file like: (?P<pattern>.+) in (?P<dir>.+)$"
            ),
            lambda m: (
                f"Не найден Excel для продукта '{m.group('product')}'. "
                f"Ожидался файл вида {m.group('pattern')} в {m.group('dir')}"
            ),
        ),
        (
            re.compile(r"^Diff Excel cannot be used for PUT\. Use the normal generated Excel file instead\.$"),
            "Diff-файл Excel нельзя использовать для отправки. Используй обычный сгенерированный Excel.",
        ),
        (
            re.compile(
                r"^Excel generated from a commit hash cannot be used for PUT\. "
                r"Run GET for a branch and use that Excel file instead\.$"
            ),
            "Excel, полученный по хешу коммита, нельзя использовать для отправки. Сначала выполни получение для ветки.",
        ),
        (
            re.compile(r"^Version must not be empty$"),
            "Версия не должна быть пустой.",
        ),
        (
            re.compile(r"^Invalid version format: (?P<version>.+)$"),
            lambda m: f"Некорректный формат версии: {m.group('version')}",
        ),
    ]

    for pattern, replacement in patterns:
        match = pattern.match(message)
        if not match:
            continue
        return replacement(match) if callable(replacement) else replacement

    return message
