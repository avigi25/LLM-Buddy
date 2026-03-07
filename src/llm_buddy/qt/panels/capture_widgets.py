"""Capture source widgets – Extension server + Proxy recorder controls.

These are compact QWidget rows designed to be embedded inside the
Prompt Tracking panel's "Capture Sources" section.
"""

import os
import shutil
import sys
import json
import logging
import platform
import socket
import sqlite3
import subprocess
import threading
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, Slot, QTimer, QProcess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QDialog,
    QTabWidget, QTextBrowser, QPlainTextEdit,
)

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None


# ── Extension Server Widget ──────────────────────────────────────────

class ExtensionServerWidget(QWidget):
    """Compact one-row widget for starting / stopping the Flask API server."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._process: QProcess | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("<b>Browser Extension:</b>"))

        self._status = QLabel("Inactive")
        self._status.setStyleSheet("color: red;")
        layout.addWidget(self._status)
        layout.addSpacing(10)

        self._btn_start = QPushButton("Start")
        self._btn_start.setProperty("class", "start_action")
        self._btn_start.setToolTip("Start the Browser Extension server")
        self._btn_start.clicked.connect(self._start)
        layout.addWidget(self._btn_start)

        self._btn_stop = QPushButton("Stop")
        self._btn_stop.setProperty("class", "stop_action")
        self._btn_stop.setToolTip("Stop the Browser Extension server")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)
        layout.addWidget(self._btn_stop)

        btn_setup = QPushButton("Setup…")
        btn_setup.clicked.connect(self._show_setup)
        layout.addWidget(btn_setup)
        layout.addStretch()

        # Check if server already running
        self._check_status()

    @Slot()
    def _start(self) -> None:
        # Use active window as parent to preserve custom themes
        from PySide6.QtWidgets import QApplication
        parent_widget = QApplication.activeWindow() or self

        if self._process is not None:
            QMessageBox.information(parent_widget, "Server Running",
                                    "The extension server is already running.")
            return

        # Prevent running both at the same time
        if hasattr(self._mw, "_proxy_widget") and self._mw._proxy_widget._process is not None:
            QMessageBox.warning(
                parent_widget, "Conflict", 
                "The Proxy Recorder is currently running. Please stop it before starting the Extension Server."
            )
            return

        # Pre-flight: check Flask is importable
        try:
            import flask  # noqa: F401
        except ImportError:
            self._mw.log("Flask not installed — cannot start server")
            QMessageBox.critical(
                self, "Flask Not Installed",
                "The 'flask' package is required.\n"
                "Install with: pip install flask flask-cors")
            return

        # Reset stopping flag on start
        self._stopping = False
        self._process = QProcess(self)
        self._process.setProgram(sys.executable)
        self._process.setArguments(
            ["-m", "llm_buddy.recorders.api_server"])
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        self._process.start()

        QTimer.singleShot(2000, self._verify_started)
        self._mw.log("Starting extension server on port 5000...")

    def _verify_started(self):
        if self._process and self._process.state() == QProcess.Running:
            self._set_running()
            self._mw.log("Extension server started on port 5000")
        else:
            self._set_stopped()
            self._mw.log("Extension server failed to start")

    @Slot()
    def _stop(self) -> None:
        self._stopping = True
        if self._process is None:
            self._set_stopped()
            return
        self._process.terminate()
        if not self._process.waitForFinished(5000):
            self._process.kill()
        self._mw.log("Extension server stopped")
        self._set_stopped()

    @Slot()
    def _on_stderr(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardError().data()
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            self._mw.log(f"Server: {text}")

    @Slot()
    def _on_stdout(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardOutput().data()
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            self._mw.log(f"Server: {text}")

    @Slot()
    def _on_error(self, error) -> None:
        # If we are intentionally stopping, ignore the crashed error
        if getattr(self, "_stopping", False) and error == QProcess.Crashed:
            return

        error_names = {
            QProcess.FailedToStart: "Failed to start",
            QProcess.Crashed: "Process crashed",
            QProcess.Timedout: "Timed out",
            QProcess.WriteError: "Write error",
            QProcess.ReadError: "Read error",
            QProcess.UnknownError: "Unknown error",
        }
        msg = error_names.get(error, f"Error code {error}")
        self._mw.log(f"Extension server error: {msg}")
        logger.error("Extension server QProcess error: %s", msg)

    @Slot()
    def _on_finished(self) -> None:
        # Read any remaining stderr/stdout before cleaning up
        if self._process:
            stderr = self._process.readAllStandardError().data()
            text = stderr.decode("utf-8", errors="replace").strip()
            if text:
                self._mw.log(f"Server: {text}")
        self._set_stopped()

    def _set_running(self):
        self._status.setText("Running")
        self._status.setStyleSheet("color: green;")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._trigger_auto_refresh()

    def _trigger_auto_refresh(self):
        """Tell the prompts panel to start its auto-refresh timer."""
        panel = getattr(self._mw, "_prompts_panel", None)
        if panel and hasattr(panel, "start_auto_refresh"):
            panel.start_auto_refresh()

    def _set_stopped(self):
        self._status.setText("Inactive")
        self._status.setStyleSheet("color: red;")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._process = None

    def _check_status(self):
        if requests is None:
            return
        try:
            resp = requests.get("http://localhost:5000/ping", timeout=1)
            if resp.status_code == 200:
                self._set_running()
        except Exception:
            pass

    @Slot()
    def _show_setup(self) -> None:
        ext_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(__file__)))), "extension")
        
        # 1. Parent directly to MainWindow to prevent inherited paint glitches
        dlg = QDialog(self._mw)
        dlg.setWindowTitle("Install Browser Extension")
        dlg.resize(500, 280)

        # 2. Force the window manager to paint the background using our theme
        dlg.setAttribute(Qt.WA_StyledBackground, True)
        dlg.setAutoFillBackground(True)

        lay = QVBoxLayout(dlg)

        title_lbl = QLabel("Browser Extension Setup")
        font = title_lbl.font()
        font.setPointSize(14)
        font.setBold(True)
        title_lbl.setFont(font)
        lay.addWidget(title_lbl)

        txt_lbl = QLabel()
        txt_lbl.setTextFormat(Qt.MarkdownText)
        txt_lbl.setWordWrap(True)
        txt_lbl.setOpenExternalLinks(True)
        txt_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        
        markdown_text = f"""
To install the LLM Buddy extension:

1. Open Chrome or Edge and go to **Extensions** (e.g., `chrome://extensions/`)
2. Enable **Developer mode** (usually a toggle in the top right)
3. Click **Load unpacked**
4. Navigate to and select the following folder:

`{ext_dir}`

*The extension captures prompts from ChatGPT, Claude, Gemini, and Perplexity.*
"""
        txt_lbl.setText(markdown_text)
        lay.addWidget(txt_lbl)

        lay.addStretch() # Pushes the close button neatly to the bottom

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        lay.addWidget(btn_close, alignment=Qt.AlignRight)
        
        dlg.exec()

    def stop_server(self):
        """Cleanup on app close."""
        if self._process and self._process.state() == QProcess.Running:
            self._process.terminate()
            self._process.waitForFinished(3000)


# ── Proxy Recorder Widget ────────────────────────────────────────────

class ProxyRecorderWidget(QWidget):
    """Compact one-row widget for starting / stopping the proxy recorder."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._process: QProcess | None = None
        self._proxy_was_configured = False
        self._stopping = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("<b>Proxy Recorder:</b>"))

        self._status = QLabel("Inactive")
        self._status.setStyleSheet("color: red;")
        layout.addWidget(self._status)
        layout.addSpacing(10)

        self._btn_start = QPushButton("Start")
        self._btn_start.setProperty("class", "start_action")
        self._btn_start.setToolTip("Start the Proxy Recorder (mitmproxy on port 8080)")
        self._btn_start.clicked.connect(self._start)
        layout.addWidget(self._btn_start)

        self._btn_stop = QPushButton("Stop")
        self._btn_stop.setProperty("class", "stop_action")
        self._btn_stop.setToolTip("Stop the Proxy Recorder") 
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)
        layout.addWidget(self._btn_stop)

        btn_guide = QPushButton("Setup Guide")
        btn_guide.clicked.connect(self._show_guide)
        layout.addWidget(btn_guide)

        btn_import = QPushButton("Import DB")
        btn_import.clicked.connect(self._import_db)
        layout.addWidget(btn_import)
        layout.addStretch()

    # -- Start / Stop --------------------------------------------------

    @staticmethod
    def _find_mitmdump() -> str | None:
        """Locate the mitmdump executable, searching common locations."""
        exe_name = "mitmdump.exe" if os.name == "nt" else "mitmdump"

        # 1. Same directory as sys.executable (works inside a venv)
        candidate = os.path.join(os.path.dirname(sys.executable), exe_name)
        if os.path.isfile(candidate):
            return candidate

        # 2. Scripts/ subdirectory (system Python on Windows)
        if os.name == "nt":
            candidate = os.path.join(
                os.path.dirname(sys.executable), "Scripts", exe_name)
            if os.path.isfile(candidate):
                return candidate

        # 3. User-level Scripts (pip install --user on Windows)
        if os.name == "nt":
            user_scripts = os.path.join(
                os.environ.get("APPDATA", ""),
                "Python",
                f"Python{sys.version_info.major}{sys.version_info.minor}",
                "Scripts", exe_name)
            if os.path.isfile(user_scripts):
                return user_scripts

        # 4. Fall back to PATH lookup
        found = shutil.which(exe_name)
        if found:
            return found

        return None

    @Slot()
    def _start(self) -> None:
        # Use active window as parent to preserve custom themes
        from PySide6.QtWidgets import QApplication
        parent_widget = QApplication.activeWindow() or self

        if self._process is not None:
            QMessageBox.information(parent_widget, "Proxy Running",
                                    "The proxy recorder is already running.")
            return

        # Prevent running both at the same time
        if hasattr(self._mw, "_ext_widget") and self._mw._ext_widget._process is not None:
            QMessageBox.warning(
                parent_widget, "Conflict", 
                "The Browser Extension server is currently running. Please stop it before starting the Proxy Recorder."
            )
            return

        # reset stopping flag on start
        self._stopping = False

        if self._is_port_in_use(8080):
            QMessageBox.warning(
                self, "Port In Use",
                "Port 8080 is already in use.\nStop the other process first.")
            return

        try:
            addon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "recorders", "proxy_recorder.py")

            mitmdump = self._find_mitmdump()
            if not mitmdump:
                QMessageBox.critical(
                    self, "mitmdump not found",
                    "Could not locate mitmdump.\n"
                    "Install mitmproxy or ensure it's on PATH.")
                return

            self._mw.log(f"Using mitmdump at: {mitmdump}")
            self._mw.log("Launching mitmdump on port 8080…")

            self._process = QProcess(self)
            self._process.setProgram(mitmdump)
            self._process.setArguments([
                "-p", "8080",
                "-s", addon_path,
                "--set", "block_global=false",
            ])
            self._process.readyReadStandardError.connect(self._on_stderr)
            self._process.readyReadStandardOutput.connect(self._on_stdout)
            self._process.finished.connect(self._on_finished)
            self._process.errorOccurred.connect(self._on_error)

            self._process.start()

            # Poll readiness and then optionally enable system proxy
            self._status.setText("Starting…")
            self._status.setStyleSheet("color: orange;")
            self._btn_start.setEnabled(False)
            self._btn_stop.setEnabled(True)

            self._poll_ready(attempts=15)

        except Exception as e:
            self._mw.log(f"Error starting proxy recorder: {e}")
            logger.exception("Error starting proxy recorder")
            self._set_stopped()

    def _trigger_auto_refresh(self):
        """Tell the prompts panel to start its auto-refresh timer."""
        panel = getattr(self._mw, "_prompts_panel", None)
        if panel and hasattr(panel, "start_auto_refresh"):
            panel.start_auto_refresh()

    def _poll_ready(self, attempts: int) -> None:
        if self._process is None or self._process.state() != QProcess.Running:
            self._mw.log("mitmdump exited prematurely")
            self._set_stopped()
            return
        if self._is_port_in_use(8080):
            self._status.setText("Running")
            self._status.setStyleSheet("color: green;")
            self._mw.log("Proxy recorder ready on port 8080")
            self._trigger_auto_refresh()
            # Offer system proxy on Windows
            if os.name == "nt" and not self._proxy_was_configured:
                # UX FIX: Use the active window as the parent to prevent black background rendering glitch
                from PySide6.QtWidgets import QApplication
                parent_widget = QApplication.activeWindow() or self
                
                answer = QMessageBox.question(
                    parent_widget, "Configure System Proxy?",
                    "Route browser traffic through the proxy?\n"
                    "(Undone when you click 'Stop Proxy'.)",
                    QMessageBox.Yes | QMessageBox.No)
                if answer == QMessageBox.Yes:
                    self._enable_system_proxy()
            return
        if attempts <= 0:
            self._mw.log("Timeout waiting for mitmdump")
            self._set_stopped()
            if self._process:
                self._process.kill()
            return
        self._status.setText(f"Starting\u2026 ({attempts}s)")
        QTimer.singleShot(
            1000, lambda: self._poll_ready(attempts - 1))

    @Slot()
    def _stop(self) -> None:
        # NEW: mark intentional stop so we can suppress Crashed noise
        self._stopping = True

        if self._proxy_was_configured and os.name == "nt":
            self._disable_system_proxy()

        if self._process and self._process.state() == QProcess.Running:
            self._process.terminate()
            if not self._process.waitForFinished(5000):
                self._process.kill()

        # Also kill strays
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/IM", "mitmdump.exe"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)

        self._mw.log("Proxy recorder stopped")
        self._set_stopped()

    @Slot()
    def _on_stderr(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardError().data()
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            for line in text.splitlines():
                self._mw.log(f"[mitmdump] {line}")

    @Slot()
    def _on_stdout(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardOutput().data()
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            for line in text.splitlines():
                self._mw.log(f"[mitmdump] {line}")

    @Slot()
    def _on_error(self, error) -> None:
        # NEW: if we're intentionally stopping, suppress the scary "Process crashed"
        if getattr(self, "_stopping", False) and error == QProcess.Crashed:
            logger.info("Proxy process reported 'Crashed' during intentional stop; ignoring.")
            return

        error_names = {
            QProcess.FailedToStart: "Failed to start",
            QProcess.Crashed: "Process crashed",
            QProcess.Timedout: "Timed out",
            QProcess.WriteError: "Write error",
            QProcess.ReadError: "Read error",
            QProcess.UnknownError: "Unknown error",
        }
        msg = error_names.get(error, f"Error code {error}")
        self._mw.log(f"Proxy error: {msg}")
        logger.error("Proxy QProcess error: %s", msg)

    @Slot()
    def _on_finished(self) -> None:
        # Read any remaining stderr before cleaning up
        if self._process:
            stderr = self._process.readAllStandardError().data()
            text = stderr.decode("utf-8", errors="replace").strip()
            if text:
                for line in text.splitlines():
                    self._mw.log(f"[mitmdump] {line}")

        # NEW: if it finished without us stopping, surface that
        if not getattr(self, "_stopping", False):
            # Not always an "error", but it helps explain unexpected stops
            self._mw.log("Proxy recorder exited.")

        self._set_stopped()

    def _set_stopped(self):
        self._status.setText("Inactive")
        self._status.setStyleSheet("color: red;")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._process = None

    @staticmethod
    def _is_port_in_use(port: int) -> bool:
        try:
            with socket.create_connection(
                    ("127.0.0.1", port), timeout=0.3):
                return True
        except (ConnectionRefusedError, OSError):
            return False

    # -- Windows proxy helpers -----------------------------------------

    def _enable_system_proxy(self):
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "127.0.0.1:8080")
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "localhost;127.0.0.1;<local>")
            winreg.CloseKey(key)
            self._proxy_was_configured = True
            self._mw.log("System proxy enabled: 127.0.0.1:8080")
            
            # Use the active window as parent to match the theme and prevent rendering glitches
            from PySide6.QtWidgets import QApplication
            parent_widget = QApplication.activeWindow() or self
            
            QMessageBox.information(
                parent_widget,
                "Proxy Enabled",
                "The system proxy has been successfully enabled."
            )
            
        except Exception as e:
            self._mw.log(f"Failed to set system proxy: {e}")

    def _disable_system_proxy(self):
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            try:
                winreg.DeleteValue(key, "ProxyOverride")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            self._proxy_was_configured = False
            self._mw.log("System proxy disabled")
            
            # Use the active window as parent to match the theme and prevent rendering glitches
            from PySide6.QtWidgets import QApplication
            parent_widget = QApplication.activeWindow() or self
            
            QMessageBox.information(
                parent_widget, 
                "Proxy Disabled", 
                "The system proxy has been successfully disabled."
            )
            
        except Exception as e:
            self._mw.log(f"Failed to disable proxy: {e}")

    def ensure_proxy_disabled(self):
        """Safety: disable proxy if we configured it (call on close)."""
        if os.name != "nt" or not self._proxy_was_configured:
            return
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion"
                r"\Internet Settings",
                0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if val == 1:
                winreg.SetValueEx(key, "ProxyEnable", 0,
                                  winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
        except Exception:
            pass

    # -- Setup guide ---------------------------------------------------

    # ── Setup guide ───────────────────────────────────────────────────

    @Slot()
    def _show_guide(self) -> None:
        # 1. Parent directly to MainWindow
        dlg = QDialog(self._mw)
        dlg.setWindowTitle("Proxy Recorder \u2013 Setup Guide")
        dlg.resize(620, 520)

        # 2. Force the background to paint correctly across all themes
        dlg.setAttribute(Qt.WA_StyledBackground, True)
        dlg.setAutoFillBackground(True)

        lay = QVBoxLayout(dlg)

        # 3. Use standard QLabels for titles instead of <h3>
        title_lbl = QLabel("Proxy Recorder Setup")
        font = title_lbl.font()
        font.setPointSize(14)
        font.setBold(True)
        title_lbl.setFont(font)
        lay.addWidget(title_lbl)

        desc_lbl = QLabel(
            "The proxy recorder uses mitmproxy to intercept browser "
            "traffic to LLM websites.")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)

        tabs = QTabWidget()
        tabs.addTab(self._guide_proxy_tab(dlg), "Step 1: Browser Proxy")
        tabs.addTab(self._guide_cert_tab(), "Step 2: CA Certificate")
        tabs.addTab(self._guide_verify_tab(), "Step 3: Verify")
        lay.addWidget(tabs)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        lay.addWidget(btn_close, alignment=Qt.AlignRight)
        dlg.exec()

    def _guide_proxy_tab(self, parent) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        
        lbl_info = QLabel()
        lbl_info.setTextFormat(Qt.MarkdownText)
        lbl_info.setText("Your browser must route traffic through **127.0.0.1:8080**.")
        lay.addWidget(lbl_info)

        if platform.system() == "Windows":
            lbl_opt_a = QLabel()
            lbl_opt_a.setTextFormat(Qt.MarkdownText)
            lbl_opt_a.setText("**Option A: Auto-configure**")
            lay.addWidget(lbl_opt_a)
            
            row = QHBoxLayout()
            be = QPushButton("Enable System Proxy")
            be.clicked.connect(self._enable_system_proxy)
            row.addWidget(be)
            bd = QPushButton("Disable System Proxy")
            bd.clicked.connect(self._disable_system_proxy)
            row.addWidget(bd)
            row.addStretch()
            lay.addLayout(row)

        lbl_opt_b = QLabel()
        lbl_opt_b.setTextFormat(Qt.MarkdownText)
        lbl_opt_b.setText("**Manual setup:**")
        lay.addWidget(lbl_opt_b)

        # Replace QTextBrowser with selectable QLabel
        txt_lbl = QLabel()
        txt_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        txt_lbl.setWordWrap(True)
        txt_lbl.setText(
            "Chrome / Edge (uses system proxy on Windows):\n"
            "  Settings > System > Open proxy settings\n"
            "  Address: 127.0.0.1   Port: 8080\n\n"
            "Firefox (own proxy settings):\n"
            "  Settings > Network Settings\n"
            "  Manual: 127.0.0.1 : 8080\n"
            "  Check 'Also use for HTTPS'")
        lay.addWidget(txt_lbl)
        lay.addStretch()
        return w

    def _guide_cert_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        cert_path = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.cer"
        
        # Replace <span> HTML with Qt style sheets for theme stability
        status_lbl = QLabel()
        if cert_path.exists():
            status_lbl.setText("Certificate found!")
            status_lbl.setStyleSheet("color: #2e7d32; font-weight: bold;") # Green
        else:
            status_lbl.setText("Certificate not found yet. Start the proxy once.")
            status_lbl.setStyleSheet("color: #ef6c00; font-weight: bold;") # Orange
        lay.addWidget(status_lbl)

        loc_lbl = QLabel(f"Location: {cert_path}")
        loc_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        loc_lbl.setWordWrap(True)
        lay.addWidget(loc_lbl)

        if platform.system() == "Windows":
            btn = QPushButton("Install CA Certificate")
            btn.clicked.connect(
                lambda: self._install_cert(cert_path))
            lay.addWidget(btn)
        lay.addStretch()
        return w

    def _guide_verify_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        
        # Replace QTextBrowser with selectable QLabel
        txt_lbl = QLabel()
        txt_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        txt_lbl.setWordWrap(True)
        txt_lbl.setText(
            "1. Click 'Start Proxy' in LLM Buddy\n"
            "2. Open browser \u2192 https://chatgpt.com\n"
            "   - Page loads: setup works!\n"
            "   - Cert error: install certificate (Step 2)\n"
            "   - No load: proxy not configured (Step 1)\n"
            "3. Type a prompt and send it\n"
            "4. Click 'Import DB' or wait for auto-refresh\n\n"
            "Tip: You only do this setup once.")
        lay.addWidget(txt_lbl)
        lay.addStretch()
        return w

    def _install_cert(self, cert_path: Path) -> None:
        if not cert_path.exists():
            QMessageBox.warning(
                self, "Not Found",
                "Certificate not generated yet. Start the proxy first.")
            return
        try:
            import ctypes
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "certutil",
                f'-addstore Root "{cert_path}"', None, 1)
            if ret > 32:
                self._mw.log("Certificate install launched")
                QMessageBox.information(
                    self, "Certificate Install",
                    "A UAC prompt should appear. Click Yes.")
            else:
                QMessageBox.warning(self, "Error",
                                    f"ShellExecute returned {ret}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -- Import from SQLite -------------------------------------------

    @Slot()
    def _import_db(self) -> None:
        base = (os.path.dirname(os.path.abspath(sys.argv[0]))
                if sys.argv[0] else os.getcwd())
        db_path = os.path.join(base, "llm-proxy-recorder", "prompts.db")
        json_path = os.path.join(base, "prompts.json")

        if not os.path.exists(db_path):
            db_path = os.path.join(os.getcwd(), "prompts.db")
            if not os.path.exists(db_path):
                QMessageBox.information(
                    self, "Database Not Found",
                    "No proxy database found.\n"
                    "It's created when the proxy captures a prompt.")
                return

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM prompts ORDER BY timestamp DESC")
            rows = cur.fetchall()

            existing = []
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            ids = {p.get("id") for p in existing}

            added = 0
            for row in rows:
                if row["id"] not in ids:
                    cur.execute(
                        "SELECT file_path FROM file_associations "
                        "WHERE prompt_id = ?", (row["id"],))
                    files = [r["file_path"] for r in cur.fetchall()]
                    existing.append({
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "prompt_text": row["prompt_text"],
                        "response_text": row["response_text"] or "",
                        "description": (row["description"]
                                        or f"Prompt from {row['llm_name']}"),
                        "model": row["llm_name"],
                        "files": files,
                    })
                    added += 1

            if added:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(existing, f, indent=4)
                self._mw.log(f"Imported {added} prompts from SQLite")
                self._mw.prompt_database.load()
                QMessageBox.information(
                    self, "Import", f"Imported {added} prompts.")
            else:
                QMessageBox.information(
                    self, "Import", "No new prompts to import.")
            conn.close()
        except Exception as e:
            self._mw.log(f"Error importing: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def stop_proxy(self):
        """Cleanup on app close."""
        if self._process and self._process.state() == QProcess.Running:
            if self._proxy_was_configured and os.name == "nt":
                self._disable_system_proxy()
            self._process.terminate()
            self._process.waitForFinished(3000)
        self.ensure_proxy_disabled()