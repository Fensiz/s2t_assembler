from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Callable

from common import read_json_file, write_json_file
from main import handle_get, handle_put, load_app_config


# ============================================================
# Constants
# ============================================================

RECENT_ITEMS_FILE = Path("~/.s2t/recent_items.json").expanduser()


# ============================================================
# Recent items helpers
# ============================================================

def load_recent_items() -> list[dict[str, str]]:
    """
    Load recent product/branch pairs from local history file.

    Invalid entries are ignored.
    """
    data = read_json_file(RECENT_ITEMS_FILE, default=[])
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


def save_recent_items(items: list[dict[str, str]]) -> None:
    """
    Save recent product/branch pairs to local history file.
    """
    RECENT_ITEMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(RECENT_ITEMS_FILE, items[:30])


def recent_item_label(item: dict[str, str]) -> str:
    """
    Build user-friendly label for recent items listbox.
    """
    product_name = item.get("product_name", "")
    branch = item.get("branch", "").strip()

    if branch:
        return f"{product_name} [{branch}]"
    return product_name


def update_recent_items(product_name: str, branch: str, listbox: tk.Listbox) -> None:
    """
    Move current product/branch pair to the top of recent items list.
    """
    items = load_recent_items()

    filtered = [
        item for item in items
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

    save_recent_items(filtered)

    listbox.delete(0, tk.END)
    for item in filtered:
        listbox.insert(tk.END, recent_item_label(item))


def fill_recent_items(listbox: tk.Listbox) -> None:
    """
    Fill recent items listbox from saved history.
    """
    listbox.delete(0, tk.END)
    for item in load_recent_items():
        listbox.insert(tk.END, recent_item_label(item))


# ============================================================
# Status helpers
# ============================================================

def set_status(widget: tk.Text, message: str) -> None:
    """
    Replace status text content with a new message.
    """
    widget.configure(state="normal")
    widget.delete("1.0", tk.END)
    widget.insert(tk.END, message)
    widget.see(tk.END)
    widget.configure(state="disabled")


def append_status(widget: tk.Text, message: str) -> None:
    """
    Append a new status line to the status text widget.
    """
    widget.configure(state="normal")

    existing = widget.get("1.0", "end-1c")
    if existing:
        widget.insert(tk.END, "\n")

    widget.insert(tk.END, message)
    widget.see(tk.END)
    widget.configure(state="disabled")


# ============================================================
# OS / threading helpers
# ============================================================

def open_file_in_os(path: Path) -> None:
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


def open_directory_in_os(path: Path) -> None:
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


def resolve_branch_value(branch_text: str) -> str | None:
    """
    Convert UI branch text to optional value.
    """
    value = branch_text.strip()
    return value or None


def run_in_thread(fn: Callable[[], None]) -> None:
    """
    Run function in a daemon thread.
    """
    thread = threading.Thread(target=fn, daemon=True)
    thread.start()


def find_latest_excel_file(
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

    # для обычного режима исключаем diff-файлы
    if not diff_mode:
        candidates = [p for p in candidates if not p.name.lower().endswith("_diff.xlsx")]

    candidates = sorted(
        candidates,
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return candidates[0] if candidates else None


# ============================================================
# UI
# ============================================================

def main_ui() -> None:
    """
    Main Tkinter UI entry point.
    """
    config = load_app_config()

    root = tk.Tk()
    root.title("S2T Tool")
    root.geometry("640x520")

    # --------------------------------------------------------
    # Form area
    # --------------------------------------------------------

    form_container = tk.Frame(root)
    form_container.pack(fill="x", padx=10, pady=(10, 0))

    # row 1: product + branch
    row1 = tk.Frame(form_container)
    row1.pack(fill="x")

    product_block = tk.Frame(row1)
    product_block.pack(side="left", fill="x", expand=True)

    tk.Label(product_block, text="Product name").pack(anchor="w")
    product_entry = tk.Entry(product_block)
    product_entry.pack(fill="x")

    branch_block = tk.Frame(row1)
    branch_block.pack(side="left", fill="x", padx=(10, 0))

    tk.Label(branch_block, text="Branch").pack(anchor="w")
    branch_entry = tk.Entry(branch_block, width=24)
    branch_entry.pack(fill="x")

    # row 2: commit message + version + diff commit
    row2 = tk.Frame(form_container)
    row2.pack(fill="x", pady=(10, 0))

    commit_block = tk.Frame(row2)
    commit_block.pack(side="left", fill="x", expand=True)

    tk.Label(commit_block, text="Commit message").pack(anchor="w")
    commit_message_entry = tk.Entry(commit_block)
    commit_message_entry.pack(fill="x")

    version_block = tk.Frame(row2)
    version_block.pack(side="left", fill="x", padx=(10, 0))

    tk.Label(version_block, text="Version").pack(anchor="w")
    version_entry = tk.Entry(version_block, width=16)
    version_entry.pack(fill="x")

    diff_commit_block = tk.Frame(row2)
    diff_commit_block.pack(side="left", fill="x", padx=(10, 0))

    tk.Label(diff_commit_block, text="Diff commit").pack(anchor="w")
    diff_commit_entry = tk.Entry(diff_commit_block, width=18)
    diff_commit_entry.pack(fill="x")

    open_after_get_var = tk.BooleanVar(value=False)
    open_after_get_checkbox = tk.Checkbutton(
        root,
        text="Open file after download",
        variable=open_after_get_var,
    )
    open_after_get_checkbox.pack(anchor="w", padx=10, pady=(8, 0))

    # --------------------------------------------------------
    # Buttons
    # --------------------------------------------------------

    button_frame = tk.Frame(root)
    button_frame.pack(fill="x", padx=10, pady=10)

    # --------------------------------------------------------
    # Recent items
    # --------------------------------------------------------

    tk.Label(root, text="Recent product + branch").pack(anchor="w", padx=10)

    recent_listbox = tk.Listbox(root, height=8)
    recent_listbox.pack(fill="x", padx=10, pady=(0, 10))
    fill_recent_items(recent_listbox)

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    tk.Label(root, text="Status").pack(anchor="w", padx=10)

    status_text = tk.Text(root, height=12, state="disabled")
    status_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # --------------------------------------------------------
    # UI-local helpers
    # --------------------------------------------------------

    def ui_logger(line: str) -> None:
        """
        Thread-safe logger for git/main progress messages.
        """
        root.after(0, lambda msg=line: append_status(status_text, msg))

    def set_buttons_enabled(enabled: bool) -> None:
        """
        Enable or disable main action buttons during background operations.
        Open-folder button stays enabled.
        """
        state = "normal" if enabled else "disabled"
        get_button.config(state=state)
        put_button.config(state=state)

    def on_recent_select(event) -> None:
        """
        Fill form fields from selected recent item.
        """
        selection = recent_listbox.curselection()
        if not selection:
            return

        items = load_recent_items()
        index = selection[0]
        if index >= len(items):
            return

        item = items[index]

        product_entry.delete(0, tk.END)
        product_entry.insert(0, item.get("product_name", ""))

        branch_entry.delete(0, tk.END)
        branch_entry.insert(0, item.get("branch", ""))

        commit_message_entry.delete(0, tk.END)
        version_entry.delete(0, tk.END)

    recent_listbox.bind("<<ListboxSelect>>", on_recent_select)

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------

    def run_open_s2t_folder() -> None:
        """
        Open directory where S2T Excel files are created.
        This is the current working directory where the tool was launched.
        """
        try:
            folder = Path.cwd()
            open_directory_in_os(folder)
            append_status(status_text, f"Opened folder: {folder}")
        except Exception as exc:
            error_text = str(exc)
            set_status(status_text, f"Open folder failed:\n{error_text}")
            messagebox.showerror("Open folder failed", error_text)

    def run_get() -> None:
        """
        Start GET operation in background thread.
        """
        product_name = product_entry.get().strip()
        branch = resolve_branch_value(branch_entry.get())
        diff_commit = diff_commit_entry.get().strip() or None

        if not product_name:
            messagebox.showerror("Error", "Product name is required")
            return

        if diff_commit:
            set_status(
                status_text,
                f"Running GET for '{product_name}' with diff against '{diff_commit}'...",
            )
        else:
            set_status(status_text, f"Running GET for '{product_name}'...")

        def worker() -> None:
            try:
                handle_get(
                    product_name=product_name,
                    branch_arg=branch,
                    diff_commit_arg=diff_commit,
                    config=config,
                    logger=ui_logger,
                )

                excel_dir = Path(config.get("excel_output_dir", ".")).expanduser().resolve()
                downloaded_file = find_latest_excel_file(
                    excel_dir=excel_dir,
                    product_name=product_name,
                    diff_mode=diff_commit is not None,
                )

                if diff_commit:
                    message = f"GET completed for '{product_name}' with diff"
                else:
                    message = f"GET completed for '{product_name}'"

                if downloaded_file:
                    message += f"\nCreated: {downloaded_file}"

                root.after(
                    0,
                    lambda: update_recent_items(product_name, branch or "", recent_listbox),
                )
                root.after(0, lambda msg=message: append_status(status_text, msg))

                if open_after_get_var.get() and downloaded_file is not None:
                    try:
                        open_file_in_os(downloaded_file)
                        root.after(
                            0,
                            lambda: append_status(status_text, f"Opened: {downloaded_file}"),
                        )
                    except Exception as exc:
                        error_text = str(exc)
                        root.after(
                            0,
                            lambda msg=error_text: append_status(status_text, f"Open failed: {msg}"),
                        )

            except Exception as exc:
                error_text = str(exc)
                root.after(0, lambda msg=error_text: set_status(status_text, f"GET failed:\n{msg}"))
                root.after(0, lambda msg=error_text: messagebox.showerror("GET failed", msg))
            finally:
                root.after(0, lambda: set_buttons_enabled(True))

        set_buttons_enabled(False)
        run_in_thread(worker)

    def run_put() -> None:
        """
        Start PUT operation in background thread.
        """
        product_name = product_entry.get().strip()
        branch = resolve_branch_value(branch_entry.get())
        commit_message = commit_message_entry.get().strip() or None
        version_value = version_entry.get().strip() or None

        if not product_name:
            messagebox.showerror("Error", "Product name is required")
            return

        set_status(status_text, f"Running PUT for '{product_name}'...")

        def worker() -> None:
            try:
                handle_put(
                    product_name=product_name,
                    branch_arg=branch,
                    version_arg=version_value,
                    excel_arg=None,
                    commit_message_arg=commit_message,
                    config=config,
                    logger=ui_logger,
                )

                root.after(
                    0,
                    lambda: update_recent_items(product_name, branch or "", recent_listbox),
                )
                root.after(
                    0,
                    lambda name=product_name: append_status(status_text, f"PUT completed for '{name}'"),
                )

            except Exception as exc:
                error_text = str(exc)
                root.after(0, lambda msg=error_text: set_status(status_text, f"PUT failed:\n{msg}"))
                root.after(0, lambda msg=error_text: messagebox.showerror("PUT failed", msg))
            finally:
                root.after(0, lambda: set_buttons_enabled(True))

        set_buttons_enabled(False)
        run_in_thread(worker)

    # --------------------------------------------------------
    # Buttons wiring
    # --------------------------------------------------------

    get_button = tk.Button(button_frame, text="Get", width=12, command=run_get)
    get_button.pack(side="left")

    put_button = tk.Button(button_frame, text="Put", width=12, command=run_put)
    put_button.pack(side="left", padx=(10, 0))

    tk.Button(
        button_frame,
        text="Open S2T folder",
        width=16,
        command=run_open_s2t_folder,
    ).pack(side="left", padx=(10, 0))

    root.mainloop()


if __name__ == "__main__":
    main_ui()