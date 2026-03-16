"""Non-blocking toast notification widget for LLM Buddy.

ToastNotification: a QLabel that slides in from the bottom-right of its
parent window and auto-dismisses after a few seconds.

ToastManager: owned by the main window; call show(message, level) to
display a toast.  Multiple toasts stack vertically.
"""

from PySide6.QtCore import QPropertyAnimation, QRect, QTimer, Qt
from PySide6.QtWidgets import QLabel, QWidget


_STYLES = {
    "info":    "background:#1565c0; color:#fff; border-radius:6px; padding:10px 16px;",
    "success": "background:#2e7d32; color:#fff; border-radius:6px; padding:10px 16px;",
    "warning": "background:#e65100; color:#fff; border-radius:6px; padding:10px 16px;",
    "error":   "background:#b71c1c; color:#fff; border-radius:6px; padding:10px 16px;",
}

_DISPLAY_MS = 3000   # auto-dismiss after 3 s
_MARGIN     = 12     # distance from window edge
_TOAST_H    = 44     # fixed height per toast
_TOAST_W    = 320    # fixed width


class ToastNotification(QLabel):
    """A single auto-dismissing notification banner."""

    def __init__(self, message: str, level: str, manager: "ToastManager",
                 parent: QWidget):
        super().__init__(message, parent)
        self._manager = manager
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.setStyleSheet(_STYLES.get(level, _STYLES["info"]))
        self.setFixedSize(_TOAST_W, _TOAST_H)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.SubWindow)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._dismiss)
        self._dismiss_timer.start(_DISPLAY_MS)

        self.show()
        self.raise_()

    def _dismiss(self):
        self._manager._remove(self)
        self.deleteLater()


class ToastManager:
    """Manages a stack of active ToastNotification widgets.

    Attach to the main window via ``ToastManager(main_window)``.
    Call ``show(message, level)`` to display a notification.
    """

    def __init__(self, parent: QWidget):
        self._parent = parent
        self._toasts: list[ToastNotification] = []

    def show(self, message: str, level: str = "info") -> None:
        """Display a toast notification."""
        toast = ToastNotification(message, level, self, self._parent)
        self._toasts.append(toast)
        self._reposition()

    def _remove(self, toast: ToastNotification) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._reposition()

    def _reposition(self) -> None:
        """Stack toasts above the bottom-right corner of the parent."""
        pw = self._parent.width()
        ph = self._parent.height()
        x = pw - _TOAST_W - _MARGIN
        for i, toast in enumerate(reversed(self._toasts)):
            y = ph - _MARGIN - (i + 1) * (_TOAST_H + 4)
            toast.move(x, y)
            toast.raise_()
