from __future__ import annotations

import tkinter as tk

from s2t_tool.bootstrap import build_container
from s2t_tool.presentation.controller import S2TController
from s2t_tool.presentation.i18n import detect_language
from s2t_tool.presentation.view import S2TView


class S2TDesktopApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.container = build_container()
        language = detect_language(self.container.config.language)
        self.view = S2TView(self.root, language=language)
        self.controller = S2TController(
            root=self.root,
            view=self.view,
            container=self.container,
        )


def main_ui() -> None:
    app = S2TDesktopApp()
    app.root.mainloop()


if __name__ == "__main__":
    main_ui()
