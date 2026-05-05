from __future__ import annotations

import tkinter as tk

from s2t_tool.adapters.system.dependency_manager import ensure_dependencies
from s2t_tool.app.bootstrap import build_container
from s2t_tool.adapters.ui.controller import S2TController
from s2t_tool.adapters.ui.i18n import detect_language
from s2t_tool.adapters.ui.view import S2TView


class S2TDesktopApp:
    def __init__(self) -> None:
        ensure_dependencies()
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
