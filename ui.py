from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from main import load_app_config, handle_get, handle_put, build_excel_filename
from common import read_json_file, write_json_file

RECENT_ITEMS_FILE = Path("~/.s2t/recent_items.json").expanduser()


def load_recent_items() -> list[dict[str, str]]:
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
    RECENT_ITEMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(RECENT_ITEMS_FILE, items[:30])


def recent_item_label(item: dict[str, str]) -> str:
    product_name = item.get("product_name", "")
    branch = item.get("branch", "").strip()
    if branch:
        return f"{product_name} [{branch}]"
    return product_name


def update_recent_items(product_name: str, branch: str, listbox: tk.Listbox) -> None:
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
    listbox.delete(0, tk.END)
    for item in load_recent_items():
        listbox.insert(tk.END, recent_item_label(item))


def set_status(widget: tk.Text, message: str) -> None:
    widget.configure(state="normal")
    widget.delete("1.0", tk.END)
    widget.insert(tk.END, message)
    widget.see(tk.END)
    widget.configure(state="disabled")


def append_status(widget: tk.Text, message: str) -> None:
    widget.configure(state="normal")

    # Если в виджете уже есть текст, добавляем перенос перед новой строкой.
    if widget.compare("end-1c", "!=", "1.0"):
        last_real_char = widget.get("end-2c", "end-1c")
        if last_real_char != "\n":
            widget.insert(tk.END, "\n")

    widget.insert(tk.END, message)
    widget.see(tk.END)
    widget.configure(state="disabled")


def open_file_in_os(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def resolve_branch_value(branch_text: str) -> str | None:
    value = branch_text.strip()
    return value or None


def run_in_thread(fn) -> None:
    thread = threading.Thread(target=fn, daemon=True)
    thread.start()


def main_ui() -> None:
    config = load_app_config()

    root = tk.Tk()
    root.title("S2T Tool")
    root.geometry("640x520")

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

    # row 2: commit message + version
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

    button_frame = tk.Frame(root)
    button_frame.pack(fill="x", padx=10, pady=10)

    recent_label = tk.Label(root, text="Recent product + branch")
    recent_label.pack(anchor="w", padx=10)

    recent_listbox = tk.Listbox(root, height=8)
    recent_listbox.pack(fill="x", padx=10, pady=(0, 10))
    fill_recent_items(recent_listbox)

    status_label = tk.Label(root, text="Status")
    status_label.pack(anchor="w", padx=10)

    status_text = tk.Text(root, height=12, state="disabled")
    status_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def on_recent_select(event) -> None:
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

    def run_get() -> None:
        product_name = product_entry.get().strip()
        branch = resolve_branch_value(branch_entry.get())
        diff_commit = diff_commit_entry.get().strip() or None

        if not product_name:
            messagebox.showerror("Error", "Product name is required")
            return

        if diff_commit:
            set_status(
                status_text,
                f"Running GET for '{product_name}' with diff against '{diff_commit}'..."
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
                )

                update_recent_items(product_name, branch or "", recent_listbox)

                # Имя файла строим так же, как main.py: из version.json через handle_get.
                # Здесь просто ищем последний подходящий файл в excel_output_dir.
                excel_dir = Path(config.get("excel_output_dir", ".")).expanduser().resolve()
                if diff_commit:
                    pattern = f"S2T_USL_{product_name.upper()}_v*_diff.xlsx"
                else:
                    pattern = f"S2T_USL_{product_name.upper()}_v*.xlsx"

                candidates = sorted(
                    excel_dir.glob(pattern),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )

                downloaded_file = candidates[0] if candidates else None

                if diff_commit:
                    message = f"GET completed for '{product_name}' with diff"
                else:
                    message = f"GET completed for '{product_name}'"

                if downloaded_file:
                    message += f"\nCreated: {downloaded_file}"

                root.after(0, lambda: set_status(status_text, message))

                if open_after_get_var.get() and downloaded_file is not None:
                    try:
                        open_file_in_os(downloaded_file)
                        root.after(
                            0,
                            lambda: append_status(status_text, f"Opened: {downloaded_file}")
                        )
                    except Exception as exc:
                        error_text = str(exc)
                        root.after(
                            0,
                            lambda msg=error_text: append_status(status_text, f"Open failed: {msg}")
                        )

            except Exception as exc:
                error_text = str(exc)
                root.after(0, lambda msg=error_text: set_status(status_text, f"GET failed:\n{msg}"))
                root.after(0, lambda msg=error_text: messagebox.showerror("GET failed", msg))

        run_in_thread(worker)

    def run_put() -> None:
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
                )

                update_recent_items(product_name, branch or "", recent_listbox)
                root.after(
                    0,
                    lambda: set_status(status_text, f"PUT completed for '{product_name}'")
                )
            except Exception as exc:
                error_text = str(exc)
                root.after(0, lambda msg=error_text: set_status(status_text, f"PUT failed:\n{msg}"))
                root.after(0, lambda msg=error_text: messagebox.showerror("PUT failed", msg))

        run_in_thread(worker)

    tk.Button(button_frame, text="Get", width=12, command=run_get).pack(side="left")
    tk.Button(button_frame, text="Put", width=12, command=run_put).pack(side="left", padx=(10, 0))

    root.mainloop()


if __name__ == "__main__":
    main_ui()