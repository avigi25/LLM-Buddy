"""QApplication bootstrap for LLM Buddy."""

import sys

from PySide6.QtWidgets import QApplication

from llm_buddy.qt.theme import apply_theme
from llm_buddy.qt.main_window import LLMBuddyWindow


def main() -> None:
    """Create the QApplication and show the main window."""
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
