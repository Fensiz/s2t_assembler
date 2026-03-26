from __future__ import annotations

import tkinter as tk
from pathlib import Path

from s2t_tool.use_cases.results import RecentItem
from s2t_tool.app.bootstrap import AppContainer
from s2t_tool.domain.branching import is_commit_ref
from s2t_tool.adapters.system.os_runtime import (
    open_directory_in_os,
    open_file_in_os,
    run_in_thread,
)
from s2t_tool.adapters.ui.form_models import GetRequest, PutRequest
from s2t_tool.adapters.ui.i18n import detect_language, localize_runtime_message, tr
from s2t_tool.adapters.ui.view import S2TView


class S2TController:
    def __init__(self, root: tk.Tk, view: S2TView, container: AppContainer) -> None:
        self.root = root
        self.view = view
        self.container = container
        self.config = container.config
        self.language = detect_language(self.config.language)

        self.view.bind_actions(
            on_get=self.run_get,
            on_put=self.run_put,
            on_open_folder=self.run_open_s2t_folder,
            on_recent_select=self._on_recent_select,
            on_version_click=self._on_version_click,
        )

        self._fill_recent_items()

        try:
            self.container.lifecycle.initial_setup_service.logger = self._ui_logger
            self.container.lifecycle.ensure_initial_setup()
        except Exception as exc:
            self.view.append_status(self._t("initial_setup_skipped", error=exc))

        self.root.after(1000, self._check_updates_on_start)

    def _call_in_ui(self, fn) -> None:
        self.root.after(0, fn)

    def _t(self, key: str, **kwargs: object) -> str:
        return tr(key, self.language, **kwargs)

    def _localize_runtime_message(self, message: object) -> str:
        return localize_runtime_message(str(message), self.language)

    def _set_status_ui(self, message: str) -> None:
        self.root.after(0, lambda msg=message: self.view.set_status(msg))

    def _append_status_ui(self, message: str) -> None:
        self.root.after(0, lambda msg=message: self.view.append_status(msg))

    def _ui_logger(self, line: str) -> None:
        self._append_status_ui(self._localize_runtime_message(line))

    def _run_background_action(self, start_message: str, worker, error_title: str) -> None:
        self.view.set_status(start_message)
        self.view.set_action_buttons_enabled(False)

        def wrapped() -> None:
            try:
                worker()
            except Exception as exc:
                error_text = self._localize_runtime_message(exc)
                self._set_status_ui(self._t("action_failed_status", action=error_title, error=error_text))
                self._call_in_ui(
                    lambda msg=error_text: self.view.show_error(
                        self._t("action_failed_title", action=error_title),
                        msg,
                    )
                )
            finally:
                self._call_in_ui(lambda: self.view.set_action_buttons_enabled(True))

        run_in_thread(wrapped)

    def _fill_recent_items(self) -> None:
        items = self.container.recent_items.load()
        self.view.fill_recent_items(items, self.container.recent_items.label)

    def _update_recent_items(self, product_name: str, branch: str) -> None:
        items = self.container.recent_items.load()
        filtered = [
            item
            for item in items
            if not (item.product_name == product_name and item.branch == branch)
        ]
        filtered.insert(0, RecentItem(product_name=product_name, branch=branch))
        self.container.recent_items.save(filtered)
        self.view.fill_recent_items(filtered, self.container.recent_items.label)

    def _on_recent_select(self, event) -> None:
        assert self.view.recent_listbox is not None
        selection = self.view.recent_listbox.curselection()
        if not selection:
            return
        items = self.container.recent_items.load()
        index = selection[0]
        if index >= len(items):
            return
        item = items[index]
        self.view.fill_form_from_recent_item(
            {"product_name": item.product_name, "branch": item.branch}
        )

    def _validate_get_request(self, request: GetRequest) -> bool:
        if not request.product_name:
            self.view.show_error(self._t("error_title"), self._t("product_name_required"))
            return False
        return True

    def _validate_put_request(self, request: PutRequest) -> bool:
        if not request.product_name:
            self.view.show_error(self._t("error_title"), self._t("product_name_required"))
            return False
        if is_commit_ref(request.branch):
            self.view.show_error(self._t("error_title"), self._t("put_requires_branch"))
            return False
        return True

    def run_open_s2t_folder(self) -> None:
        try:
            folder = self.container.paths.excel_output_dir(self.config)
            open_directory_in_os(folder)
            self.view.append_status(self._t("opened_folder", path=folder))
        except Exception as exc:
            error_text = self._localize_runtime_message(exc)
            self.view.set_status(self._t("open_folder_failed", error=error_text))
            self.view.show_error(self._t("open_folder_failed_title"), error_text)

    def run_get(self) -> None:
        request = self.view.read_get_request()
        if not self._validate_get_request(request):
            return
        start_message = (
            self._t("running_get_diff", product=request.product_name, commit=request.diff_commit)
            if request.diff_commit
            else self._t("running_get", product=request.product_name)
        )
        self._run_background_action(
            start_message=start_message,
            worker=lambda: self._worker_get(request),
            error_title=tr("get_export", self.language),
        )

    def run_put(self) -> None:
        request = self.view.read_put_request()
        if not self._validate_put_request(request):
            return
        self._run_background_action(
            start_message=self._t("running_put", product=request.product_name),
            worker=lambda: self._worker_put(request),
            error_title=tr("put_publish", self.language),
        )

    def _after_get_success(self, request: GetRequest, downloaded_file: Path | None) -> None:
        self._update_recent_items(request.product_name, request.branch or "")
        message = (
            self._t("get_completed_diff", product=request.product_name)
            if request.diff_commit
            else self._t("get_completed", product=request.product_name)
        )
        if downloaded_file:
            message += f"\n{self._t('created_file', path=downloaded_file)}"
        self.view.append_status(message)
        if self.view.open_after_get_var.get() and downloaded_file is not None:
            try:
                open_file_in_os(downloaded_file)
                self.view.append_status(self._t("opened_file", path=downloaded_file))
            except Exception as exc:
                self.view.append_status(self._t("open_failed", error=self._localize_runtime_message(exc)))

    def _after_put_success(self, request: PutRequest) -> None:
        self._update_recent_items(request.product_name, request.branch or "")
        self.view.append_status(self._t("put_completed", product=request.product_name))

    def _worker_get(self, request: GetRequest) -> None:
        result = self.container.operations.run_get(
            product_name=request.product_name,
            branch=request.branch,
            version=request.version,
            diff_commit=request.diff_commit,
            logger=self._ui_logger,
        )
        self._call_in_ui(lambda: self._after_get_success(request, result.output_excel))

    def _worker_put(self, request: PutRequest) -> None:
        self.container.operations.run_put(
            product_name=request.product_name,
            branch=request.branch,
            version=request.version,
            keep_version=request.keep_version,
            format_sql=request.format_sql,
            excel_path=None,
            commit_message=request.commit_message,
            logger=self._ui_logger,
        )
        self._call_in_ui(lambda: self._after_put_success(request))

    def _check_updates_on_start(self) -> None:
        def worker() -> None:
            try:
                result = self.container.update_flow.check_updates(logger=self._ui_logger)
                self._call_in_ui(lambda: self.view.set_update_available(result.available, result.latest_version))
                if result.available and result.latest_version:
                    self._append_status_ui(self._t("update_available_status", version=result.latest_version))
            except Exception as exc:
                self._append_status_ui(self._t("update_check_failed_status", error=self._localize_runtime_message(exc)))

        run_in_thread(worker)

    def _on_version_click(self, event) -> None:
        def worker() -> None:
            try:
                result = self.container.update_flow.check_updates(logger=self._ui_logger)
                self._call_in_ui(lambda: self.view.set_update_available(result.available, result.latest_version))
                if not result.available:
                    self._call_in_ui(
                        lambda: self.view.show_info(
                            self._t("update_title"),
                            self._t("already_latest_version"),
                        )
                    )
                    return

                message = self._t("new_version_available", version=result.latest_version)

                def ask_and_update() -> None:
                    confirmed = self.view.ask_yes_no(self._t("update_title"), message)
                    if not confirmed:
                        return
                    self.view.append_status(self._t("starting_update"))
                    self.view.set_action_buttons_enabled(False)
                    run_in_thread(self._perform_update)

                self._call_in_ui(ask_and_update)
            except Exception as exc:
                error_text = self._localize_runtime_message(exc)
                self._call_in_ui(
                    lambda msg=error_text: self.view.show_error(
                        self._t("update_title"),
                        self._t("update_check_failed", error=msg),
                    )
                )

        run_in_thread(worker)

    def _restart_with_updated_app(self, app_path: Path) -> None:
        try:
            command = self.container.update_flow.restart_updated_app(app_path, logger=None)
            self.view.append_status(self._t("starting_new_version", command=" ".join(command)))
            self.view.append_status(self._t("new_version_started"))
            self.root.after(200, self.root.destroy)
        except Exception as exc:
            self.view.show_error(
                self._t("update_title"),
                self._t("restart_failed", error=self._localize_runtime_message(exc)),
            )
            self.view.append_status(self._t("restart_error_status", error=self._localize_runtime_message(exc)))
            self.view.set_action_buttons_enabled(True)

    def _perform_update(self) -> None:
        try:
            updated_app_path = self.container.update_flow.install_update(logger=self._ui_logger)
            self._append_status_ui(self._t("update_installed_restart"))
            self._call_in_ui(lambda path=updated_app_path: self._restart_with_updated_app(path))
        except Exception as exc:
            error_text = self._localize_runtime_message(exc)
            self._call_in_ui(
                lambda msg=error_text: self.view.show_error(
                    self._t("update_title"),
                    self._t("update_install_failed", error=msg),
                )
            )
            self._append_status_ui(self._t("update_error_status", error=error_text))
            self._call_in_ui(lambda: self.view.set_action_buttons_enabled(True))
