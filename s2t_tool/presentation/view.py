from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable

from s2t_tool.app_info import APP_VERSION
from s2t_tool.presentation.form_models import GetRequest, PutRequest
from s2t_tool.presentation.i18n import detect_language, tr


class S2TView:
    BG = "#f3f5f8"
    PANEL_BG = "#ffffff"
    BORDER = "#d9e1ea"
    TEXT = "#122033"
    MUTED = "#64748b"
    DANGER = "#b91c1c"
    BUTTON_TEXT = "#122033"
    INPUT_BG = "#fbfcfe"
    OPTIONAL_INPUT_BG = "#f2f5f9"
    STATUS_BG = "#0f172a"
    STATUS_TEXT = "#e2e8f0"

    def __init__(self, root: tk.Tk) -> None:
        self.language = detect_language()
        self.root = root
        self.root.title(tr("app_title", self.language))
        self.root.geometry("640x500")
        self.root.minsize(620, 460)
        self.root.configure(bg=self.BG)

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

        self._build_fonts()
        self.build()

    def _build_fonts(self) -> None:
        self.section_font = ("Helvetica", 8, "bold")
        self.label_font = ("Helvetica", 8, "bold")
        self.body_font = ("Helvetica", 8)
        self.button_font = ("Helvetica", 8, "bold")
        self.status_font = ("Menlo", 8)
        self.version_font = ("Helvetica", 8, "bold")

    def build(self) -> None:
        shell = tk.Frame(self.root, bg=self.BG)
        shell.pack(fill="both", expand=True, padx=8, pady=6)

        content = tk.Frame(shell, bg=self.BG)
        content.pack(fill="x", pady=(2, 0))
        content.grid_columnconfigure(0, weight=0)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=0)
        content.grid_rowconfigure(1, weight=1)

        self._build_actions_panel(content, row=0, column=0, rowspan=2)
        self._build_form_panel(content, row=0, column=1)
        self._build_recent_panel(content, row=1, column=1)
        self._build_status_panel(shell)

    def _panel(self, parent: tk.Widget, title: str | None = None) -> tuple[tk.Frame, tk.Frame]:
        frame = tk.Frame(
            parent,
            bg=self.PANEL_BG,
            highlightbackground=self.BORDER,
            highlightthickness=1,
            bd=0,
        )

        if title:
            header = tk.Frame(frame, bg=self.PANEL_BG)
            header.pack(fill="x", padx=8, pady=(6, 1))
            tk.Label(
                header,
                text=title,
                font=self.section_font,
                fg=self.TEXT,
                bg=self.PANEL_BG,
            ).pack(anchor="w")

        body = tk.Frame(frame, bg=self.PANEL_BG)
        body.pack(fill="both", expand=True, padx=8, pady=(6 if title else 8, 8))
        return frame, body

    def _build_form_panel(self, parent: tk.Widget, row: int | None = None, column: int | None = None) -> None:
        panel, body = self._panel(parent)
        if row is None or column is None:
            panel.pack(fill="x", pady=(2, 0))
        else:
            panel.grid(row=row, column=column, sticky="ew", padx=(4, 0), pady=(2, 0))

        row1 = tk.Frame(body, bg=self.PANEL_BG)
        row1.pack(fill="x")

        product_block = tk.Frame(row1, bg=self.PANEL_BG)
        product_block.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._field_label(product_block, tr("product", self.language))
        self.product_entry = self._entry(product_block)
        self.product_entry.pack(fill="x")

        branch_block = tk.Frame(row1, bg=self.PANEL_BG, width=230)
        branch_block.pack(side="left", fill="x")
        self._field_label(branch_block, tr("branch_or_commit", self.language))
        self.branch_entry = self._entry(branch_block)
        self._mark_optional_entry(self.branch_entry)
        self.branch_entry.pack(fill="x")

        row2 = tk.Frame(body, bg=self.PANEL_BG)
        row2.pack(fill="x", pady=(6, 0))

        commit_block = tk.Frame(row2, bg=self.PANEL_BG)
        commit_block.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._field_label(commit_block, tr("commit_message", self.language))
        self.commit_message_entry = self._entry(commit_block)
        self._mark_optional_entry(self.commit_message_entry)
        self.commit_message_entry.pack(fill="x")

        version_block = tk.Frame(row2, bg=self.PANEL_BG)
        version_block.pack(side="left", padx=(0, 6))
        self._field_label(version_block, tr("version_override", self.language))
        self.version_entry = self._entry(version_block, width=8)
        self._mark_optional_entry(self.version_entry)
        self.version_entry.pack(fill="x")

        diff_block = tk.Frame(row2, bg=self.PANEL_BG)
        diff_block.pack(side="left")
        self._field_label(diff_block, tr("diff_against_commit", self.language))
        self.diff_commit_entry = self._entry(diff_block, width=12)
        self._mark_optional_entry(self.diff_commit_entry)
        self.diff_commit_entry.pack(fill="x")

    def _build_actions_panel(
        self,
        parent: tk.Widget,
        row: int | None = None,
        column: int | None = None,
        rowspan: int = 1,
    ) -> None:
        panel, body = self._panel(parent, tr("actions", self.language))
        if row is None or column is None:
            panel.pack(anchor="ne", fill="y")
        else:
            panel.grid(row=row, column=column, rowspan=rowspan, sticky="ns", padx=(0, 4), pady=(2, 0))

        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)

        toolbar = tk.Frame(body, bg=self.PANEL_BG)
        toolbar.grid(row=0, column=0, sticky="n")

        self.get_button = tk.Button(
            toolbar,
            text=tr("get_export", self.language),
            width=10,
            bg="#ccefe8",
            fg=self.BUTTON_TEXT,
            activebackground="#b7e6dc",
            activeforeground=self.BUTTON_TEXT,
            relief="flat",
            bd=0,
            font=self.button_font,
            padx=6,
            pady=4,
            cursor="hand2",
        )
        self.get_button.pack(fill="x")

        self.put_button = tk.Button(
            toolbar,
            text=tr("put_publish", self.language),
            width=10,
            bg="#dbeafe",
            fg=self.BUTTON_TEXT,
            activebackground="#bfdbfe",
            activeforeground=self.BUTTON_TEXT,
            relief="flat",
            bd=0,
            font=self.button_font,
            padx=6,
            pady=4,
            cursor="hand2",
        )
        self.put_button.pack(fill="x", pady=(6, 0))

        self.open_folder_button = tk.Button(
            toolbar,
            text=tr("open_excel_folder", self.language),
            bg="#e2e8f0",
            fg=self.TEXT,
            activebackground="#cbd5e1",
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            font=self.button_font,
            padx=6,
            pady=4,
            cursor="hand2",
        )
        self.open_folder_button.pack(fill="x", pady=(6, 0))

        tk.Checkbutton(
            body,
            text=tr("open_after_get", self.language).replace(" после ", "\nпосле ", 1),
            variable=self.open_after_get_var,
            bg=self.PANEL_BG,
            fg=self.TEXT,
            activebackground=self.PANEL_BG,
            activeforeground=self.TEXT,
            selectcolor=self.PANEL_BG,
            font=self.body_font,
            highlightthickness=0,
        ).grid(row=1, column=0, sticky="n", pady=(8, 0))

        self.version_container = tk.Frame(body, bg=self.PANEL_BG, highlightthickness=0, bd=0)
        self.version_container.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        self.version_label = tk.Label(
            self.version_container,
            text=tr("version_short", self.language, version=APP_VERSION),
            cursor="hand2",
            padx=7,
            pady=2,
            bg="#e2e8f0",
            fg=self.TEXT,
            font=self.version_font,
        )
        self.version_label.pack(fill="x")

    def _build_recent_panel(self, parent: tk.Widget, row: int | None = None, column: int | None = None) -> None:
        panel, body = self._panel(parent, tr("recent_targets", self.language))
        if row is None or column is None:
            panel.pack(fill="x", pady=(4, 0))
        else:
            panel.grid(row=row, column=column, sticky="nsew", padx=(4, 0), pady=(4, 0))

        self.recent_listbox = tk.Listbox(
            body,
            height=5,
            bd=0,
            highlightthickness=0,
            bg=self.INPUT_BG,
            fg=self.TEXT,
            selectbackground="#dbeafe",
            selectforeground=self.TEXT,
            activestyle="none",
            font=self.body_font,
        )
        scrollbar = tk.Scrollbar(body, orient="vertical", command=self.recent_listbox.yview)
        self.recent_listbox.configure(yscrollcommand=scrollbar.set)
        self.recent_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_status_panel(self, parent: tk.Widget) -> None:
        panel, body = self._panel(parent, tr("execution_log", self.language))
        panel.pack(fill="both", expand=True, pady=(4, 0))

        self.status_text = tk.Text(
            body,
            height=7,
            state="disabled",
            bd=0,
            highlightthickness=0,
            bg=self.STATUS_BG,
            fg=self.STATUS_TEXT,
            insertbackground=self.STATUS_TEXT,
            font=self.status_font,
            padx=7,
            pady=7,
            wrap="word",
        )
        self.status_text.pack(fill="both", expand=True)

    def _field_label(self, parent: tk.Widget, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            font=self.label_font,
            fg=self.TEXT,
            bg=self.PANEL_BG,
        ).pack(anchor="w", pady=(0, 2))

    def _entry(self, parent: tk.Widget, width: int | None = None) -> tk.Entry:
        return tk.Entry(
            parent,
            bg=self.INPUT_BG,
            fg=self.TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            highlightcolor="#94a3b8",
            insertbackground=self.TEXT,
            font=self.body_font,
            width=width,
        )

    def _mark_optional_entry(self, entry: tk.Entry) -> None:
        entry.configure(bg=self.OPTIONAL_INPUT_BG)

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

    def set_status(self, message: str) -> None:
        assert self.status_text is not None
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", tk.END)
        self.status_text.insert(tk.END, message)
        self.status_text.see(tk.END)
        self.status_text.configure(state="disabled")

    def append_status(self, message: str) -> None:
        assert self.status_text is not None
        self.status_text.configure(state="normal")
        existing = self.status_text.get("1.0", "end-1c")
        if existing:
            self.status_text.insert(tk.END, "\n")
        self.status_text.insert(tk.END, message)
        self.status_text.see(tk.END)
        self.status_text.configure(state="disabled")

    def set_action_buttons_enabled(self, enabled: bool) -> None:
        assert self.get_button is not None
        assert self.put_button is not None
        state = "normal" if enabled else "disabled"
        self.get_button.config(state=state)
        self.put_button.config(state=state)

    def set_update_available(self, available: bool, latest_version: str | None = None) -> None:
        assert self.version_container is not None
        assert self.version_label is not None

        if available:
            self.version_container.config(
                highlightbackground=self.DANGER,
                highlightcolor=self.DANGER,
                highlightthickness=2,
            )
            if latest_version:
                self.version_label.config(
                    text=tr("version_update", self.language, current=APP_VERSION, latest=latest_version),
                    bg="#fee2e2",
                    fg=self.DANGER,
                )
            else:
                self.version_label.config(
                    text=tr("version_available", self.language, current=APP_VERSION),
                    bg="#fee2e2",
                    fg=self.DANGER,
                )
        else:
            self.version_container.config(highlightthickness=0)
            self.version_label.config(
                text=tr("version_short", self.language, version=APP_VERSION),
                bg="#e2e8f0",
                fg=self.TEXT,
            )

    def set_version_text(self, text: str) -> None:
        assert self.version_label is not None
        self.version_label.config(text=text)

    def fill_recent_items(
        self,
        items: list[dict[str, str]],
        label_builder: Callable[[dict[str, str]], str],
    ) -> None:
        assert self.recent_listbox is not None
        self.recent_listbox.delete(0, tk.END)
        for item in items:
            self.recent_listbox.insert(tk.END, label_builder(item))

    def read_get_request(self) -> GetRequest:
        assert self.product_entry is not None
        assert self.branch_entry is not None
        assert self.diff_commit_entry is not None
        return GetRequest(
            product_name=self.product_entry.get().strip(),
            branch=self._resolve_branch_value(self.branch_entry.get()),
            diff_commit=self.diff_commit_entry.get().strip() or None,
        )

    def read_put_request(self) -> PutRequest:
        assert self.product_entry is not None
        assert self.branch_entry is not None
        assert self.commit_message_entry is not None
        assert self.version_entry is not None
        return PutRequest(
            product_name=self.product_entry.get().strip(),
            branch=self._resolve_branch_value(self.branch_entry.get()),
            commit_message=self.commit_message_entry.get().strip() or None,
            version=self.version_entry.get().strip() or None,
        )

    def fill_form_from_recent_item(self, item: dict[str, str]) -> None:
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

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def ask_yes_no(self, title: str, message: str) -> bool:
        return messagebox.askyesno(title, message)

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    @staticmethod
    def _resolve_branch_value(branch_text: str) -> str | None:
        value = branch_text.strip()
        return value or None
