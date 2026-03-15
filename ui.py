from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox

from common import read_json_file, write_json_file
from main import handle_get, handle_put, load_app_config


# ============================================================
# Constants
# ============================================================

RECENT_ITEMS_FILE = Path("~/.s2t/recent_items.json").expanduser()


# ============================================================
# Data models
# ============================================================

@dataclass
class GetRequest:
    product_name: str
    branch: str | None
    diff_commit: str | None


@dataclass
class PutRequest:
    product_name: str
    branch: str | None
    commit_message: str | None
    version: str | None


# ============================================================
# Recent items storage
# ============================================================

class RecentItemsStore:
    def __init__(self, path: Path) -> None:
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


# ============================================================
# Main app
# ============================================================

class S2TApp:
    def __init__(self) -> None:
        self.config = load_app_config()
        self.recent_store = RecentItemsStore(RECENT_ITEMS_FILE)

        self.root = tk.Tk()
        self.root.title("S2T Tool")
        self.root.geometry("640x520")

        self.open_after_get_var = tk.BooleanVar(value=False)

        self.product_entry: tk.Entry | None = None
        self.branch_entry: tk.Entry | None = None
        self.commit_message_entry: tk.Entry | None = None
        self.version_entry: tk.Entry | None = None
        self.diff_commit_entry: tk.Entry | None = None

        self.recent_listbox: tk.Listbox | None = None
        self.status_text: tk.Text | None = None

        self.get_button: tk.Button | None = None
        self.put_button: tk.Button | None = None

        self._build_ui()
        self._fill_recent_items()

    # --------------------------------------------------------
    # UI construction
    # --------------------------------------------------------

    def _build_ui(self) -> None:
        self._build_form_area()
        self._build_controls_area()
        self._build_recent_area()
        self._build_status_area()
        self._bind_events()

    def _build_form_area(self) -> None:
        form_container = tk.Frame(self.root)
        form_container.pack(fill="x", padx=10, pady=(10, 0))

        # row 1: product + branch
        row1 = tk.Frame(form_container)
        row1.pack(fill="x")

        product_block = tk.Frame(row1)
        product_block.pack(side="left", fill="x", expand=True)

        tk.Label(product_block, text="Product name").pack(anchor="w")
        self.product_entry = tk.Entry(product_block)
        self.product_entry.pack(fill="x")

        branch_block = tk.Frame(row1)
        branch_block.pack(side="left", fill="x", padx=(10, 0))

        tk.Label(branch_block, text="Branch").pack(anchor="w")
        self.branch_entry = tk.Entry(branch_block, width=24)
        self.branch_entry.pack(fill="x")

        # row 2: commit message + version + diff commit
        row2 = tk.Frame(form_container)
        row2.pack(fill="x", pady=(10, 0))

        commit_block = tk.Frame(row2)
        commit_block.pack(side="left", fill="x", expand=True)

        tk.Label(commit_block, text="Commit message").pack(anchor="w")
        self.commit_message_entry = tk.Entry(commit_block)
        self.commit_message_entry.pack(fill="x")

        version_block = tk.Frame(row2)
        version_block.pack(side="left", fill="x", padx=(10, 0))

        tk.Label(version_block, text="Version").pack(anchor="w")
        self.version_entry = tk.Entry(version_block, width=16)
        self.version_entry.pack(fill="x")

        diff_commit_block = tk.Frame(row2)
        diff_commit_block.pack(side="left", fill="x", padx=(10, 0))

        tk.Label(diff_commit_block, text="Diff commit").pack(anchor="w")
        self.diff_commit_entry = tk.Entry(diff_commit_block, width=18)
        self.diff_commit_entry.pack(fill="x")

    def _build_controls_area(self) -> None:
        open_after_get_checkbox = tk.Checkbutton(
            self.root,
            text="Open file after download",
            variable=self.open_after_get_var,
        )
        open_after_get_checkbox.pack(anchor="w", padx=10, pady=(8, 0))

        button_frame = tk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=10)

        self.get_button = tk.Button(button_frame, text="Get", width=12, command=self.run_get)
        self.get_button.pack(side="left")

        self.put_button = tk.Button(button_frame, text="Put", width=12, command=self.run_put)
        self.put_button.pack(side="left", padx=(10, 0))

        tk.Button(
            button_frame,
            text="Open S2T folder",
            width=16,
            command=self.run_open_s2t_folder,
        ).pack(side="left", padx=(10, 0))

    def _build_recent_area(self) -> None:
        tk.Label(self.root, text="Recent product + branch").pack(anchor="w", padx=10)

        self.recent_listbox = tk.Listbox(self.root, height=8)
        self.recent_listbox.pack(fill="x", padx=10, pady=(0, 10))

    def _build_status_area(self) -> None:
        tk.Label(self.root, text="Status").pack(anchor="w", padx=10)

        self.status_text = tk.Text(self.root, height=12, state="disabled")
        self.status_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _bind_events(self) -> None:
        self.recent_listbox.bind("<<ListboxSelect>>", self._on_recent_select)

    # --------------------------------------------------------
    # General helpers
    # --------------------------------------------------------

    def _resolve_branch_value(self, branch_text: str) -> str | None:
        """
        Convert UI branch text to optional value.
        """
        value = branch_text.strip()
        return value or None

    def _set_status(self, message: str) -> None:
        """
        Replace status text content with a new message.
        """
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", tk.END)
        self.status_text.insert(tk.END, message)
        self.status_text.see(tk.END)
        self.status_text.configure(state="disabled")

    def _append_status(self, message: str) -> None:
        """
        Append a new status line to the status text widget.
        """
        self.status_text.configure(state="normal")

        existing = self.status_text.get("1.0", "end-1c")
        if existing:
            self.status_text.insert(tk.END, "\n")

        self.status_text.insert(tk.END, message)
        self.status_text.see(tk.END)
        self.status_text.configure(state="disabled")

    def _ui_logger(self, line: str) -> None:
        """
        Thread-safe logger for git/main progress messages.
        """
        self.root.after(0, lambda msg=line: self._append_status(msg))

    def _set_action_buttons_enabled(self, enabled: bool) -> None:
        """
        Enable or disable main action buttons during background operations.
        Open-folder button stays enabled.
        """
        state = "normal" if enabled else "disabled"
        self.get_button.config(state=state)
        self.put_button.config(state=state)

    def _run_in_thread(self, fn) -> None:
        """
        Run function in a daemon thread.
        """
        thread = threading.Thread(target=fn, daemon=True)
        thread.start()

    def _open_file_in_os(self, path: Path) -> None:
        """
        Open file in the default OS application.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)

    def _open_directory_in_os(self, path: Path) -> None:
        """
        Open directory in the OS file manager.
        """
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)

    def _find_latest_excel_file(
        self,
        excel_dir: Path,
        product_name: str,
        diff_mode: bool,
    ) -> Path | None:
        """
        Find the newest generated Excel file for the product.

        Supports:
        - normal:      S2T_USL_<PRODUCT>_v*.xlsx
        - debug:       S2T_USL_<PRODUCT>_v*_debug.xlsx
        - diff:        S2T_USL_<PRODUCT>_v*_diff.xlsx
        - debug diff:  S2T_USL_<PRODUCT>_v*_debug_diff.xlsx
        """
        product_upper = product_name.upper()

        if diff_mode:
            patterns = [
                f"S2T_USL_{product_upper}_v*_debug_diff.xlsx",
                f"S2T_USL_{product_upper}_v*_diff.xlsx",
            ]
        else:
            patterns = [
                f"S2T_USL_{product_upper}_v*_debug.xlsx",
                f"S2T_USL_{product_upper}_v*.xlsx",
            ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(excel_dir.glob(pattern))

        if not diff_mode:
            candidates = [p for p in candidates if not p.name.lower().endswith("_diff.xlsx")]

        candidates = sorted(
            candidates,
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        return candidates[0] if candidates else None

    # --------------------------------------------------------
    # Recent items
    # --------------------------------------------------------

    def _fill_recent_items(self) -> None:
        """
        Fill recent items listbox from saved history.
        """
        self.recent_listbox.delete(0, tk.END)
        for item in self.recent_store.load():
            self.recent_listbox.insert(tk.END, self.recent_store.label(item))

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
            }
        )

        self.recent_store.save(filtered)

        self.recent_listbox.delete(0, tk.END)
        for item in filtered:
            self.recent_listbox.insert(tk.END, self.recent_store.label(item))

    def _on_recent_select(self, event) -> None:
        """
        Fill form fields from selected recent item.
        """
        selection = self.recent_listbox.curselection()
        if not selection:
            return

        items = self.recent_store.load()
        index = selection[0]
        if index >= len(items):
            return

        item = items[index]

        self.product_entry.delete(0, tk.END)
        self.product_entry.insert(0, item.get("product_name", ""))

        self.branch_entry.delete(0, tk.END)
        self.branch_entry.insert(0, item.get("branch", ""))

        self.commit_message_entry.delete(0, tk.END)
        self.version_entry.delete(0, tk.END)

    # --------------------------------------------------------
    # Request readers
    # --------------------------------------------------------

    def _read_get_request(self) -> GetRequest | None:
        product_name = self.product_entry.get().strip()
        branch = self._resolve_branch_value(self.branch_entry.get())
        diff_commit = self.diff_commit_entry.get().strip() or None

        if not product_name:
            messagebox.showerror("Error", "Product name is required")
            return None

        return GetRequest(
            product_name=product_name,
            branch=branch,
            diff_commit=diff_commit,
        )

    def _read_put_request(self) -> PutRequest | None:
        product_name = self.product_entry.get().strip()
        branch = self._resolve_branch_value(self.branch_entry.get())
        commit_message = self.commit_message_entry.get().strip() or None
        version = self.version_entry.get().strip() or None

        if not product_name:
            messagebox.showerror("Error", "Product name is required")
            return None

        return PutRequest(
            product_name=product_name,
            branch=branch,
            commit_message=commit_message,
            version=version,
        )

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------

    def run_open_s2t_folder(self) -> None:
        """
        Open directory where S2T Excel files are created.
        This is the current working directory where the tool was launched.
        """
        try:
            folder = Path.cwd()
            self._open_directory_in_os(folder)
            self._append_status(f"Opened folder: {folder}")
        except Exception as exc:
            error_text = str(exc)
            self._set_status(f"Open folder failed:\n{error_text}")
            messagebox.showerror("Open folder failed", error_text)

    def run_get(self) -> None:
        """
        Start GET operation in background thread.
        """
        request = self._read_get_request()
        if request is None:
            return

        if request.diff_commit:
            self._set_status(
                f"Running GET for '{request.product_name}' "
                f"with diff against '{request.diff_commit}'..."
            )
        else:
            self._set_status(f"Running GET for '{request.product_name}'...")

        self._set_action_buttons_enabled(False)
        self._run_in_thread(lambda: self._worker_get(request))

    def run_put(self) -> None:
        """
        Start PUT operation in background thread.
        """
        request = self._read_put_request()
        if request is None:
            return

        self._set_status(f"Running PUT for '{request.product_name}'...")

        self._set_action_buttons_enabled(False)
        self._run_in_thread(lambda: self._worker_put(request))

    # --------------------------------------------------------
    # Background workers
    # --------------------------------------------------------

    def _worker_get(self, request: GetRequest) -> None:
        try:
            handle_get(
                product_name=request.product_name,
                branch_arg=request.branch,
                diff_commit_arg=request.diff_commit,
                config=self.config,
                logger=self._ui_logger,
            )

            excel_dir = Path(self.config.get("excel_output_dir", ".")).expanduser().resolve()
            downloaded_file = self._find_latest_excel_file(
                excel_dir=excel_dir,
                product_name=request.product_name,
                diff_mode=request.diff_commit is not None,
            )

            if request.diff_commit:
                message = f"GET completed for '{request.product_name}' with diff"
            else:
                message = f"GET completed for '{request.product_name}'"

            if downloaded_file:
                message += f"\nCreated: {downloaded_file}"

            self.root.after(
                0,
                lambda: self._update_recent_items(request.product_name, request.branch or ""),
            )
            self.root.after(0, lambda msg=message: self._append_status(msg))

            if self.open_after_get_var.get() and downloaded_file is not None:
                try:
                    self._open_file_in_os(downloaded_file)
                    self.root.after(
                        0,
                        lambda: self._append_status(f"Opened: {downloaded_file}"),
                    )
                except Exception as exc:
                    error_text = str(exc)
                    self.root.after(
                        0,
                        lambda msg=error_text: self._append_status(f"Open failed: {msg}"),
                    )

        except Exception as exc:
            error_text = str(exc)
            self.root.after(0, lambda msg=error_text: self._set_status(f"GET failed:\n{msg}"))
            self.root.after(0, lambda msg=error_text: messagebox.showerror("GET failed", msg))
        finally:
            self.root.after(0, lambda: self._set_action_buttons_enabled(True))

    def _worker_put(self, request: PutRequest) -> None:
        try:
            handle_put(
                product_name=request.product_name,
                branch_arg=request.branch,
                version_arg=request.version,
                excel_arg=None,
                commit_message_arg=request.commit_message,
                config=self.config,
                logger=self._ui_logger,
            )

            self.root.after(
                0,
                lambda: self._update_recent_items(request.product_name, request.branch or ""),
            )
            self.root.after(
                0,
                lambda name=request.product_name: self._append_status(f"PUT completed for '{name}'"),
            )

        except Exception as exc:
            error_text = str(exc)
            self.root.after(0, lambda msg=error_text: self._set_status(f"PUT failed:\n{msg}"))
            self.root.after(0, lambda msg=error_text: messagebox.showerror("PUT failed", msg))
        finally:
            self.root.after(0, lambda: self._set_action_buttons_enabled(True))


# ============================================================
# Public entry point
# ============================================================

def main_ui() -> None:
    app = S2TApp()
    app.root.mainloop()


if __name__ == "__main__":
    main_ui()