"""Subprocess and system-proxy management — no GUI imports.

Consolidates logic from ``gui.mixin_extension`` and ``gui.mixin_proxy``
that deals with launching / stopping external processes and modifying
the Windows system proxy via the registry.
"""

import logging
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Port helpers
# --------------------------------------------------------------------------

def is_port_in_use(port: int) -> bool:
    """Return *True* if something is listening on *port*."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except (ConnectionRefusedError, OSError):
        return False


# --------------------------------------------------------------------------
# Flask extension server
# --------------------------------------------------------------------------

def build_flask_server_command() -> list:
    """Return the command list to start the Flask API server."""
    return [sys.executable, "-m", "llm_buddy.recorders.api_server"]


def check_extension_server(url: str = "http://localhost:5000") -> bool:
    """Return *True* if the extension server /ping endpoint responds."""
    try:
        import requests
        from urllib.parse import urljoin
        resp = requests.get(urljoin(url, "/ping"), timeout=1)
        return resp.status_code == 200
    except Exception:
        return False


# --------------------------------------------------------------------------
# Proxy recorder (mitmdump)
# --------------------------------------------------------------------------

def find_mitmdump_exe() -> str:
    """Locate the mitmdump executable in the same dir as the Python interpreter."""
    scripts_dir = os.path.dirname(sys.executable)
    name = "mitmdump.exe" if os.name == "nt" else "mitmdump"
    exe = os.path.join(scripts_dir, name)
    if not os.path.exists(exe):
        raise FileNotFoundError(f"mitmdump not found at {exe}")
    return exe


def build_mitmdump_command() -> list:
    """Return the command list to start mitmdump with the proxy addon."""
    addon_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "recorders", "proxy_recorder.py")
    exe = find_mitmdump_exe()
    return [exe, "--mode", "regular", "--listen-port", "8080",
            "-s", addon_path]


def get_popen_kwargs() -> dict:
    """Return platform-specific kwargs for subprocess.Popen on Windows."""
    kwargs = {}
    if os.name == "nt":
        CREATE_NO_WINDOW = 0x08000000
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    return kwargs


def kill_proxy_processes() -> None:
    """Force-kill any stray mitmdump / mitmproxy processes."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "mitmdump.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/F", "/IM", "mitmproxy.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(["pkill", "-f", "mitmdump"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "mitmproxy"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --------------------------------------------------------------------------
# Windows system proxy (registry)
# --------------------------------------------------------------------------

def enable_system_proxy() -> None:
    """Enable the Windows system proxy (127.0.0.1:8080).

    Raises RuntimeError on failure.
    """
    if platform.system() != "Windows":
        return
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ,
                          "127.0.0.1:8080")
        winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ,
                          "localhost;127.0.0.1;<local>")
        winreg.CloseKey(key)
        logger.info("System proxy enabled: 127.0.0.1:8080")
    except Exception as e:
        raise RuntimeError(f"Could not set system proxy: {e}") from e


def disable_system_proxy() -> None:
    """Disable the Windows system proxy.

    Raises RuntimeError on failure.
    """
    if platform.system() != "Windows":
        return
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        try:
            winreg.DeleteValue(key, "ProxyOverride")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        logger.info("System proxy disabled")
    except Exception as e:
        raise RuntimeError(f"Could not disable system proxy: {e}") from e


def ensure_proxy_disabled() -> None:
    """Safety: disable the system proxy if it's currently set to 8080.

    Silently ignores errors — intended to be called on app shutdown.
    """
    if platform.system() != "Windows":
        return
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            0, winreg.KEY_SET_VALUE | winreg.KEY_READ,
        )
        val, _ = winreg.QueryValueEx(key, "ProxyEnable")
        if val == 1:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            try:
                winreg.DeleteValue(key, "ProxyOverride")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


# --------------------------------------------------------------------------
# Certificate installation
# --------------------------------------------------------------------------

def get_mitmproxy_cert_path() -> Path:
    """Return the expected path to the mitmproxy CA certificate."""
    return Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.cer"


def is_cert_installed(cert_path: Optional[Path] = None) -> bool:
    """Check whether the mitmproxy CA certificate is already trusted."""
    if cert_path is None:
        cert_path = get_mitmproxy_cert_path()
    if not cert_path.exists():
        return False
    try:
        check = subprocess.run(
            ["certutil", "-verify", str(cert_path)],
            capture_output=True, text=True, timeout=10,
        )
        return check.returncode == 0
    except Exception:
        return False


def install_cert_windows(cert_path: Optional[Path] = None) -> bool:
    """Request UAC elevation to install the mitmproxy CA cert.

    Returns True if ShellExecuteW launched successfully (>32).
    """
    if cert_path is None:
        cert_path = get_mitmproxy_cert_path()
    if not cert_path.exists():
        raise FileNotFoundError(
            "The mitmproxy CA certificate hasn't been generated yet.")
    import ctypes
    args = f'-addstore Root "{cert_path}"'
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", "certutil", args, None, 1)
    return ret > 32
