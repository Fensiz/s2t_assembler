from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Any

from InitialSetupService import InitialSetupService
from UpdateService import UpdateService
from main import handle_get, handle_put, load_app_config
from main_config import resolve_excel_output_dir
from ui_models import GetRequest, PutRequest
from ui_recent_store import RecentItemsStore
from ui_utils import (
    find_latest_excel_file,
    open_directory_in_os,
    open_file_in_os,
    run_in_thread,
)
from ui_view import S2TView


class S2TApp:
    def __init__(self) -> None:
        self.config = load_app_config()
        self.recent_store = RecentItemsStore()

        self.root = tk.Tk()
        self.view = S2TView(self.root)

        self.update_service = UpdateService(
            self.config,
            logger=lambda message: self.view.append_status(message),
        )

        self.view.bind_actions(
            on_get=self.run_get,
            on_put=self.run_put,
            on_open_folder=self.run_open_s2t_folder,
            on_recent_select=self._on_recent_select,
            on_version_click=self._on_version_click,
        )

        self._fill_recent_items()

        try:
            InitialSetupService(
                self.config,
                logger=lambda message: self.view.append_status(message),
            ).ensure_initial_setup()
        except Exception as exc:
            self.view.append_status(f"Initial setup skipped: {exc}")

        self.root.after(1000, self._check_updates_on_start)

    # --------------------------------------------------------
    # UI-thread helpers
    # --------------------------------------------------------

    def _call_in_ui(self, fn) -> None:
        self.root.after(0, fn)

    def _set_status_ui(self, message: str) -> None:
        self.root.after(0, lambda msg=message: self.view.set_status(msg))

    def _append_status_ui(self, message: str) -> None:
        self.root.after(0, lambda msg=message: self.view.append_status(msg))

    def _ui_logger(self, line: str) -> None:
        """
        Thread-safe logger for git/main progress messages.
        """
        self._append_status_ui(line)

    def _run_background_action(self, start_message: str, worker, error_title: str) -> None:
        """
        Common wrapper for background actions.
        """
        self.view.set_status(start_message)
        self.view.set_action_buttons_enabled(False)

        def wrapped() -> None:
            try:
                worker()
            except Exception as exc:
                error_text = str(exc)
                self._set_status_ui(f"{error_title} failed:\n{error_text}")
                self._call_in_ui(
                    lambda msg=error_text: self.view.show_error(f"{error_title} failed", msg)
                )
            finally:
                self._call_in_ui(lambda: self.view.set_action_buttons_enabled(True))

        run_in_thread(wrapped)

    # --------------------------------------------------------
    # Recent items
    # --------------------------------------------------------

    def _fill_recent_items(self) -> None:
        self.view.fill_recent_items(self.recent_store.load(), self.recent_store.label)

    def _update_recent_items(self, product_name: str, branch: str) -> None:
        """
        Move current product/branch pair to the top of recent items list.
        """
        items = self.recent_store.load()

        filtered = [
            item
            for item in items
            if not (
                item.get("product_name", "") == product_name
                and item.get("branch", "") == branch
            )
        ]

        filtered.insert(
            0,
            {
                "product_name": product_name,
                "branch": branch,
            },
        )

        self.recent_store.save(filtered)
        self.view.fill_recent_items(filtered, self.recent_store.label)

    def _on_recent_select(self, event) -> None:
        """
        Fill form fields from selected recent item.
        """
        assert self.view.recent_listbox is not None

        selection = self.view.recent_listbox.curselection()
        if not selection:
            return

        items = self.recent_store.load()
        index = selection[0]
        if index >= len(items):
            return

        item = items[index]
        self.view.fill_form_from_recent_item(item)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    def _validate_get_request(self, request: GetRequest) -> bool:
        if not request.product_name:
            self.view.show_error("Error", "Product name is required")
            return False
        return True

    def _validate_put_request(self, request: PutRequest) -> bool:
        if not request.product_name:
            self.view.show_error("Error", "Product name is required")
            return False
        return True

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------

    def run_open_s2t_folder(self) -> None:
        """
        Open directory where S2T Excel files are created.
        """
        try:
            folder = resolve_excel_output_dir(self.config)
            open_directory_in_os(folder)
            self.view.append_status(f"Opened folder: {folder}")
        except Exception as exc:
            error_text = str(exc)
            self.view.set_status(f"Open folder failed:\n{error_text}")
            self.view.show_error("Open folder failed", error_text)

    def run_get(self) -> None:
        """
        Start GET operation in background thread.
        """
        request = self.view.read_get_request()
        if not self._validate_get_request(request):
            return

        start_message = (
            f"Running GET for '{request.product_name}' with diff against '{request.diff_commit}'..."
            if request.diff_commit
            else f"Running GET for '{request.product_name}'..."
        )

        self._run_background_action(
            start_message=start_message,
            worker=lambda: self._worker_get(request),
            error_title="GET",
        )

    def run_put(self) -> None:
        """
        Start PUT operation in background thread.
        """
        request = self.view.read_put_request()
        if not self._validate_put_request(request):
            return

        self._run_background_action(
            start_message=f"Running PUT for '{request.product_name}'...",
            worker=lambda: self._worker_put(request),
            error_title="PUT",
        )

    # --------------------------------------------------------
    # Background workers
    # --------------------------------------------------------

    def _after_get_success(self, request: GetRequest, downloaded_file: Path | None) -> None:
        self._update_recent_items(request.product_name, request.branch or "")

        if request.diff_commit:
            message = f"GET completed for '{request.product_name}' with diff"
        else:
            message = f"GET completed for '{request.product_name}'"

        if downloaded_file:
            message += f"\nCreated: {downloaded_file}"

        self.view.append_status(message)

        if self.view.open_after_get_var.get() and downloaded_file is not None:
            try:
                open_file_in_os(downloaded_file)
                self.view.append_status(f"Opened: {downloaded_file}")
            except Exception as exc:
                self.view.append_status(f"Open failed: {exc}")

    def _after_put_success(self, request: PutRequest) -> None:
        self._update_recent_items(request.product_name, request.branch or "")
        self.view.append_status(f"PUT completed for '{request.product_name}'")

    def _worker_get(self, request: GetRequest) -> None:
        handle_get(
            product_name=request.product_name,
            branch_arg=request.branch,
            diff_commit_arg=request.diff_commit,
            config=self.config,
            logger=self._ui_logger,
        )

        excel_dir = resolve_excel_output_dir(self.config)
        downloaded_file = find_latest_excel_file(
            excel_dir=excel_dir,
            product_name=request.product_name,
            diff_mode=request.diff_commit is not None,
        )

        self._call_in_ui(lambda: self._after_get_success(request, downloaded_file))

    def _worker_put(self, request: PutRequest) -> None:
        handle_put(
            product_name=request.product_name,
            branch_arg=request.branch,
            version_arg=request.version,
            excel_arg=None,
            commit_message_arg=request.commit_message,
            config=self.config,
            logger=self._ui_logger,
        )

        self._call_in_ui(lambda: self._after_put_success(request))

    # --------------------------------------------------------
    # Update service
    # --------------------------------------------------------

    def _check_updates_on_start(self) -> None:
        """
        Check for updates after UI startup and highlight version widget if needed.
        """
        def worker() -> None:
            try:
                available, latest_version = self.update_service.check_update()
                self._call_in_ui(
                    lambda: self.view.set_update_available(available, latest_version)
                )

                if available and latest_version:
                    self._append_status_ui(f"Доступно обновление: {latest_version}")
            except Exception as exc:
                self._append_status_ui(f"Не удалось проверить обновления: {exc}")

        run_in_thread(worker)

    def _on_version_click(self, event) -> None:
        """
        Handle click on version widget.
        If update is available, ask user and perform update.
        Otherwise just show current status.
        """
        def worker() -> None:
            try:
                available, latest_version = self.update_service.check_update()

                self._call_in_ui(
                    lambda: self.view.set_update_available(available, latest_version)
                )

                if not available:
                    self._call_in_ui(
                        lambda: self.view.show_info(
                            "Обновление",
                            "У вас уже установлена последняя версия.",
                        )
                    )
                    return

                message = (
                    f"Доступна новая версия: {latest_version}.\n\n"
                    f"Установить обновление сейчас?"
                )

                def ask_and_update() -> None:
                    confirmed = self.view.ask_yes_no("Обновление", message)
                    if not confirmed:
                        return

                    self.view.append_status("Начинаю обновление...")
                    self.view.set_action_buttons_enabled(False)
                    run_in_thread(self._perform_update)

                self._call_in_ui(ask_and_update)

            except Exception as exc:
                error_text = str(exc)
                self._call_in_ui(
                    lambda msg=error_text: self.view.show_error(
                        "Обновление",
                        f"Не удалось проверить обновление:\n{msg}",
                    )
                )

        run_in_thread(worker)

    def _perform_update(self) -> None:
        """
        Download/install update and restart application.
        """
        try:
            self.update_service.perform_update()
        except SystemExit:
            raise
        except Exception as exc:
            error_text = str(exc)
            self._call_in_ui(
                lambda msg=error_text: self.view.show_error(
                    "Обновление",
                    f"Не удалось установить обновление:\n{msg}",
                )
            )
            self._append_status_ui(f"Ошибка обновления: {error_text}")
            self._call_in_ui(lambda: self.view.set_action_buttons_enabled(True))