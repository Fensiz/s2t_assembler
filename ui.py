from __future__ import annotations

from ui_app import S2TApp


def main_ui() -> None:
    app = S2TApp()
    app.root.mainloop()


if __name__ == "__main__":
    main_ui()