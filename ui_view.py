from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Any

from app_info import APP_VERSION
from ui_models import GetRequest, PutRequest


class S2TView:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
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
        self.open_folder_button: tk.Button | None = None

        self.version_container: tk.Frame | None = None
        self.version_label: tk.Label | None = None

        self.build()

    # --------------------------------------------------------
    # Build UI
    # --------------------------------------------------------

    def build(self) -> None:
        self._build_header_area()
        self._build_form_area()
        self._build_controls_area()
        self._build_recent_area()
        self._build_status_area()

    def _build_header_area(self) -> None:
        header_frame = tk.Frame(self.root)
        header_frame.pack(fill="x", padx=10, pady=(10, 0))

        left_spacer = tk.Frame(header_frame)
        left_spacer.pack(side="left", fill="x", expand=True)

        self.version_container = tk.Frame(
            header_frame,
            highlightthickness=0,
            bd=0,
        )
        self.version_container.pack(side="right", anchor="ne")

        self.version_label = tk.Label(
            self.version_container,
            text=f"v{APP_VERSION}",
            cursor="hand2",
            padx=8,
            pady=4,
        )
        self.version_label.pack()

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

        self.get_button = tk.Button(button_frame, text="Get", width=12)
        self.get_button.pack(side="left")

        self.put_button = tk.Button(button_frame, text="Put", width=12)
        self.put_button.pack(side="left", padx=(10, 0))

        self.open_folder_button = tk.Button(button_frame, text="Open S2T folder", width=16)
        self.open_folder_button.pack(side="left", padx=(10, 0))

    def _build_recent_area(self) -> None:
        tk.Label(self.root, text="Recent product + branch").pack(anchor="w", padx=10)

        self.recent_listbox = tk.Listbox(self.root, height=8)
        self.recent_listbox.pack(fill="x", padx=10, pady=(0, 10))

    def _build_status_area(self) -> None:
        tk.Label(self.root, text="Status").pack(anchor="w", padx=10)

        self.status_text = tk.Text(self.root, height=12, state="disabled")
        self.status_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # --------------------------------------------------------
    # Bindings
    # --------------------------------------------------------

    def bind_actions(
        self,
        on_get: Callable[[], None],
        on_put: Callable[[], None],
        on_open_folder: Callable[[], None],
        on_recent_select: Callable[[Any], None],
        on_version_click: Callable[[Any], None] | None = None,
    ) -> None:
        assert self.get_button is not None
        assert self.put_button is not None
        assert self.open_folder_button is not None
        assert self.recent_listbox is not None
        assert self.version_label is not None

        self.get_button.config(command=on_get)
        self.put_button.config(command=on_put)
        self.open_folder_button.config(command=on_open_folder)
        self.recent_listbox.bind("<<ListboxSelect>>", on_recent_select)

        if on_version_click is not None:
            self.version_label.bind("<Button-1>", on_version_click)

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    def set_status(self, message: str) -> None:
        """
        Replace status text content with a new message.
        """
        assert self.status_text is not None

        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", tk.END)
        self.status_text.insert(tk.END, message)
        self.status_text.see(tk.END)
        self.status_text.configure(state="disabled")

    def append_status(self, message: str) -> None:
        """
        Append a new status line to the status text widget.
        """
        assert self.status_text is not None

        self.status_text.configure(state="normal")

        existing = self.status_text.get("1.0", "end-1c")
        if existing:
            self.status_text.insert(tk.END, "\n")

        self.status_text.insert(tk.END, message)
        self.status_text.see(tk.END)
        self.status_text.configure(state="disabled")

    # --------------------------------------------------------
    # Buttons / state
    # --------------------------------------------------------

    def set_action_buttons_enabled(self, enabled: bool) -> None:
        """
        Enable or disable main action buttons during background operations.

        Open-folder button stays enabled.
        """
        assert self.get_button is not None
        assert self.put_button is not None

        state = "normal" if enabled else "disabled"
        self.get_button.config(state=state)
        self.put_button.config(state=state)

    # --------------------------------------------------------
    # Version / update indicator
    # --------------------------------------------------------

    def set_update_available(self, available: bool, latest_version: str | None = None) -> None:
        """
        Highlight version widget if update is available.
        """
        assert self.version_container is not None
        assert self.version_label is not None

        if available:
            self.version_container.config(
                highlightbackground="red",
                highlightcolor="red",
                highlightthickness=2,
            )
            if latest_version:
                self.version_label.config(text=f"v{APP_VERSION} → {latest_version}")
            else:
                self.version_label.config(text=f"v{APP_VERSION}")
        else:
            self.version_container.config(highlightthickness=0)
            self.version_label.config(text=f"v{APP_VERSION}")

    def set_version_text(self, text: str) -> None:
        """
        Override displayed version text.
        """
        assert self.version_label is not None
        self.version_label.config(text=text)

    # --------------------------------------------------------
    # Recent items
    # --------------------------------------------------------

    def fill_recent_items(self, items: list[dict[str, str]], label_builder: Callable[[dict[str, str]], str]) -> None:
        """
        Fill recent items listbox from provided items.
        """
        assert self.recent_listbox is not None

        self.recent_listbox.delete(0, tk.END)
        for item in items:
            self.recent_listbox.insert(tk.END, label_builder(item))

    # --------------------------------------------------------
    # Form read/write
    # --------------------------------------------------------

    def read_get_request(self) -> GetRequest:
        assert self.product_entry is not None
        assert self.branch_entry is not None
        assert self.diff_commit_entry is not None

        product_name = self.product_entry.get().strip()
        branch = self._resolve_branch_value(self.branch_entry.get())
        diff_commit = self.diff_commit_entry.get().strip() or None

        return GetRequest(
            product_name=product_name,
            branch=branch,
            diff_commit=diff_commit,
        )

    def read_put_request(self) -> PutRequest:
        assert self.product_entry is not None
        assert self.branch_entry is not None
        assert self.commit_message_entry is not None
        assert self.version_entry is not None

        product_name = self.product_entry.get().strip()
        branch = self._resolve_branch_value(self.branch_entry.get())
        commit_message = self.commit_message_entry.get().strip() or None
        version = self.version_entry.get().strip() or None

        return PutRequest(
            product_name=product_name,
            branch=branch,
            commit_message=commit_message,
            version=version,
        )

    def fill_form_from_recent_item(self, item: dict[str, str]) -> None:
        """
        Fill form fields from selected recent item.
        """
        assert self.product_entry is not None
        assert self.branch_entry is not None
        assert self.commit_message_entry is not None
        assert self.version_entry is not None

        self.product_entry.delete(0, tk.END)
        self.product_entry.insert(0, item.get("product_name", ""))

        self.branch_entry.delete(0, tk.END)
        self.branch_entry.insert(0, item.get("branch", ""))

        self.commit_message_entry.delete(0, tk.END)
        self.version_entry.delete(0, tk.END)

    # --------------------------------------------------------
    # Dialogs
    # --------------------------------------------------------

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def ask_yes_no(self, title: str, message: str) -> bool:
        return messagebox.askyesno(title, message)

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def _resolve_branch_value(branch_text: str) -> str | None:
        """
        Convert UI branch text to optional value.
        """
        value = branch_text.strip()
        return value or None