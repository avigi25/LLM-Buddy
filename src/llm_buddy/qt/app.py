"""QApplication bootstrap for LLM Buddy."""

import os
import sys


def _setup_frozen_env() -> None:
    """Configure the environment for a PyInstaller-frozen build."""
    if not getattr(sys, "frozen", False):
        return
    app_dir = os.path.dirname(sys.executable)
    os.chdir(app_dir)
    os.environ.setdefault(
        "TIKTOKEN_CACHE_DIR",
        os.path.join(app_dir, "data", ".tiktoken_cache"),
    )


def main() -> None:
    """Create the QApplication and show the main window."""
    _setup_frozen_env()

    from PySide6.QtWidgets import QApplication
    from llm_buddy.qt.theme import apply_theme
    from llm_buddy.qt.main_window import LLMBuddyWindow

    app = QApplication(sys.argv)
    app.setApplicationName("LLM Buddy")
    app.setOrganizationName("LLM Buddy")

    # Default to light theme
    apply_theme(app, "Light")

    window = LLMBuddyWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
