LLM_BUDDY_MARKER: @§A_4a26e87a@

@§A_4a26e87a@ C:/LLM Buddy\build.py

"""Build script for creating LLM Buddy Windows executables.

Usage:
    python build.py          Build the distribution
    python build.py clean    Remove build artifacts
    python build.py test     Build and run a quick smoke test
"""

import os
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
SPEC_FILE = os.path.join(PROJECT_ROOT, "llm_buddy.spec")
APP_NAME = "LLM Buddy"


def clean():
    """Remove build artifacts."""
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            print(f"Removing {d}")
            shutil.rmtree(d)
    print("Clean complete.")


def build():
    """Run PyInstaller with the spec file."""
    # Ensure PyInstaller is available
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Pre-cache tiktoken encoding data
    print("Pre-caching tiktoken encodings...")
    try:
        import tiktoken
        tiktoken.get_encoding("cl100k_base")
        print("  cl100k_base cached.")
    except Exception as e:
        print(f"  Warning: {e}")

    # Run PyInstaller
    print("\nBuilding with PyInstaller...")
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        SPEC_FILE,
        "--noconfirm",
        "--clean",
    ], cwd=PROJECT_ROOT)

    # Create runtime directories in dist
    dist_app = os.path.join(DIST_DIR, APP_NAME)
    for d in ["data", "logs"]:
        os.makedirs(os.path.join(dist_app, d), exist_ok=True)

    print(f"\nBuild complete!")
    print(f"  Output:     {dist_app}")
    print(f"  GUI:        {os.path.join(dist_app, 'LLM Buddy.exe')}")
    print(f"  MCP:        {os.path.join(dist_app, 'llm-buddy-mcp.exe')}")
    print(f"  Proxy:      {os.path.join(dist_app, 'llm-buddy-proxy.exe')}")
    print(f"  Extension:  {os.path.join(dist_app, 'extension')}")


def smoke_test():
    """Verify the exe starts without immediate crash."""
    exe = os.path.join(DIST_DIR, APP_NAME, "LLM Buddy.exe")
    if not os.path.exists(exe):
        print("Build not found. Run 'python build.py' first.")
        return
    print(f"Smoke test: launching {exe} ...")
    proc = subprocess.Popen(
        [exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        proc.wait(timeout=5)
        print(f"  Exited with code {proc.returncode}")
        if proc.returncode != 0:
            print(f"  stderr: {proc.stderr.read().decode()[:500]}")
    except subprocess.TimeoutExpired:
        print("  Still running after 5s (good — GUI is alive)")
        proc.terminate()


if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "build"
    if cmd == "clean":
        clean()
    elif cmd == "test":
        build()
        smoke_test()
    elif cmd == "build":
        build()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python build.py [build|clean|test]")
        sys.exit(1)


@§A_4a26e87a@ C:/LLM Buddy\install.bat

@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   LLM Buddy - Windows Installer
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.9+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during install!
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Found Python %PYVER%
echo.

:: Save install directory
set "INSTALL_DIR=%~dp0"

:: Clear any stale proxy left over from a previous proxy recorder session
:: (A leftover proxy breaks pip because it tries to connect to 127.0.0.1:8080)
for /f "tokens=3" %%v in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2^>nul ^| findstr ProxyEnable') do (
    if "%%v"=="0x1" (
        echo NOTE: Clearing stale system proxy before install...
        reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul 2>nul
    )
)

:: Create virtual environment
if not exist "%INSTALL_DIR%.venv" (
    echo [1/4] Creating virtual environment...
    python -m venv "%INSTALL_DIR%.venv"
) else (
    echo [1/4] Virtual environment already exists.
)

:: Activate and install
echo [2/4] Installing LLM Buddy...
call "%INSTALL_DIR%.venv\Scripts\activate.bat"
pip install -e "%INSTALL_DIR%." --quiet 2>nul
if errorlevel 1 (
    pip install -e "%INSTALL_DIR%."
)

:: Install all optional extras by default (easier for end users)
echo [3/4] Installing optional components...
pip install -e "%INSTALL_DIR%.[all]" --quiet 2>nul
if errorlevel 1 (
    echo          Some optional components could not be installed.
    echo          The core application will still work fine.
)

:: Create the launcher batch file
echo [4/4] Creating launcher...
(
echo @echo off
echo cd /d "%%~dp0"
echo if exist ".venv\Scripts\activate.bat" (
echo     call ".venv\Scripts\activate.bat"
echo     start "" pythonw -m llm_buddy
echo ^) else (
echo     start "" python -m llm_buddy
echo ^)
) > "%INSTALL_DIR%LLM Buddy.bat"

:: Create Desktop shortcut via temp VBScript
:: Use Shell.Application to find the real Desktop (works with OneDrive too)
set "TARGET=%INSTALL_DIR%LLM Buddy.bat"
echo Creating desktop shortcut...
set "VBSTMP=%TEMP%\make_shortcut.vbs"
> "%VBSTMP%" echo Set shell = CreateObject("Shell.Application")
>>"%VBSTMP%" echo desktopPath = shell.Namespace(0).Self.Path
>>"%VBSTMP%" echo Set ws = CreateObject("WScript.Shell")
>>"%VBSTMP%" echo Set sc = ws.CreateShortcut(desktopPath ^& "\LLM Buddy.lnk")
>>"%VBSTMP%" echo sc.TargetPath = "%TARGET%"
>>"%VBSTMP%" echo sc.WorkingDirectory = "%INSTALL_DIR%"
>>"%VBSTMP%" echo sc.Description = "LLM Buddy - Prompt Recording and Management"
>>"%VBSTMP%" echo sc.IconLocation = "%INSTALL_DIR%icon.ico"
>>"%VBSTMP%" echo sc.Save
>>"%VBSTMP%" echo WScript.Echo desktopPath ^& "\LLM Buddy.lnk"
for /f "delims=" %%p in ('cscript //nologo "%VBSTMP%" 2^>nul') do set "SHORTCUT=%%p"
del "%VBSTMP%" 2>nul

if defined SHORTCUT (
    if exist "%SHORTCUT%" (
        echo Desktop shortcut created!
    ) else (
        echo Could not create desktop shortcut, but you can double-click:
        echo   %TARGET%
    )
) else (
    echo Could not create desktop shortcut, but you can double-click:
    echo   %TARGET%
)

echo.
echo ================================================
echo   Installation Complete!
echo ================================================
echo.
echo   To launch LLM Buddy:
echo     - Double-click "LLM Buddy" on your Desktop
echo     - Or double-click "LLM Buddy.bat" in this folder
echo.

:: Ask about Claude Desktop configuration
set /p CLAUDE="Configure Claude Desktop MCP integration? [y/n]: "
if /i "%CLAUDE%"=="y" (
    llm-buddy configure
)

:: Launch the app
echo.
echo Launching LLM Buddy...
start "" "%INSTALL_DIR%.venv\Scripts\pythonw.exe" -m llm_buddy
echo.
echo You can close this window now.
pause


@§A_4a26e87a@ C:/LLM Buddy\install.sh

#!/usr/bin/env bash
set -e

echo "================================================"
echo "  LLM Buddy - Mac/Linux Installer"
echo "================================================"
echo

# Determine script directory (works even if called from elsewhere)
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is not installed."
    echo
    echo "Install it from: https://www.python.org/downloads/"
    echo "  or via your package manager (brew install python3, apt install python3, etc.)"
    exit 1
fi

PYVER=$(python3 --version 2>&1)
echo "Found $PYVER"
echo

# Create virtual environment
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv "$INSTALL_DIR/.venv"
else
    echo "[1/4] Virtual environment already exists."
fi

# Activate and install
echo "[2/4] Installing LLM Buddy..."
source "$INSTALL_DIR/.venv/bin/activate"
pip install -e "$INSTALL_DIR" --quiet 2>/dev/null || pip install -e "$INSTALL_DIR"

# Install all optional extras by default
echo "[3/4] Installing optional components..."
pip install -e "$INSTALL_DIR[all]" --quiet 2>/dev/null || \
    echo "         Some optional components could not be installed."
    echo "         The core application will still work fine."

# Create launcher script
echo "[4/4] Creating launcher..."
cat > "$INSTALL_DIR/LLM Buddy.command" << 'LAUNCHER'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/.venv/bin/activate"
python -m llm_buddy
LAUNCHER
chmod +x "$INSTALL_DIR/LLM Buddy.command"

# On macOS, also create a Desktop alias if possible
if [ "$(uname)" = "Darwin" ]; then
    DESKTOP="$HOME/Desktop"
    if [ -d "$DESKTOP" ]; then
        ln -sf "$INSTALL_DIR/LLM Buddy.command" "$DESKTOP/LLM Buddy.command" 2>/dev/null && \
            echo "Desktop shortcut created!" || \
            echo "Could not create desktop shortcut."
    fi
fi

echo
echo "================================================"
echo "  Installation Complete!"
echo "================================================"
echo
echo "  To launch LLM Buddy:"
echo "    - Double-click \"LLM Buddy.command\" in this folder"
if [ "$(uname)" = "Darwin" ]; then
    echo "    - Or double-click \"LLM Buddy\" on your Desktop"
fi
echo

# Ask about Claude Desktop
read -rp "Configure Claude Desktop MCP integration? [y/n]: " CLAUDE
if [[ "${CLAUDE,,}" == "y" ]]; then
    llm-buddy configure
fi

# Launch the app
echo
echo "Launching LLM Buddy..."
python -m llm_buddy &


@§A_4a26e87a@ C:/LLM Buddy\pyproject.toml

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "llm-buddy"
version = "3.1.0"
description = "Universal prompt recording and management system for LLM services"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.9"
authors = [
    {name = "Anthony Vigil", email = "anthony.vigil@usf.edu"},
]
keywords = ["llm", "prompt", "recording", "chatgpt", "claude", "gemini"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Documentation",
]
dependencies = [
    "tiktoken>=0.5.0",
    "watchdog>=3.0.0",
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
    "PySide6>=6.6.0",
]

[project.optional-dependencies]
proxy = ["mitmproxy>=9.0.1"]
server = ["flask>=2.3.3", "flask-cors>=4.0.0"]
mcp = ["mcp>=0.9.0"]
all = [
    "mitmproxy>=9.0.1",
    "flask>=2.3.3",
    "flask-cors>=4.0.0",
    "mcp>=0.9.0",
]

[project.scripts]
llm-buddy = "llm_buddy.cli:main"

[project.urls]
Homepage = "https://github.com/avigi25/LLM-Buddy"

[tool.setuptools.packages.find]
where = ["src"]


@§A_4a26e87a@ C:/LLM Buddy\README.md

# LLM Buddy

A Computer-Aided Method Engineering (CAME) tool for documenting LLM-augmented research through prompt-centric auditable development.

[![DOI](http://img.shields.io/badge/DOI-10.5281/zenodo.1135937826-1073c8?labelColor=000000)](https://doi.org/10.5281/zenodo.18274813)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-3.1.0-green)](https://github.com/avigi25/LLM-Buddy/releases)

## Research Context

**This tool was developed as part of doctoral research at the University of South Florida's Muma College of Business.**

LLM Buddy was created to address methodological challenges in conducting rigorous research with Large Language Models. It was used to document 1,555 prompts across multiple Elaborated Action Design Research (eADR) cycles, enabling the discovery of the "Conversational Forking" methodology and providing unprecedented documentation of AI-augmented development processes.

A prototype paper, *"LLM Buddy: An AI-Augmented Research Environment for Auditable Design Science,"* was submitted to the [DESRIST 2026](https://desrist2026.org/) Prototypes Track.

**Note**: The original research prompt corpus remains proprietary. This repository provides the tool and representative examples to enable replication of the methodology.

## Demo

https://github.com/user-attachments/assets/784748b0-12cc-47bb-b325-5cfb57190743

Link to download the video demo is available here: [Demo Video](demo/LLM_Buddy_Demo.mp4)

Link to download an LLM-readable markdown snapshot of the codebase for inspection: [Single File Source Code](research-artifacts/llm-buddy-codebase-snapshot-v3.1.0.md)

## Overview

LLM Buddy is a desktop application for capturing, organizing, and analyzing prompts and responses from all major LLM services. It combines proxy-based recording, a Chrome extension, MCP integration, and a modern Qt GUI to help researchers and developers maintain a complete, auditable record of their AI interactions.

### Key Features

- **Universal Prompt + Response Capture** — Records both prompts and LLM responses from ChatGPT, Claude, Gemini, Perplexity, and more via four independent capture methods.
- **Chrome Extension** — Automatic DOM-based capture from web LLM interfaces with zero configuration. Detects when streaming completes and sends both sides of the conversation to the local database.
- **HTTPS Proxy Recorder** — Intercepts API-level traffic via mitmproxy for programmatic LLM calls.
- **Claude Desktop MCP Integration** — Native Model Context Protocol server for automatic recording from Claude Desktop.
- **Modern Qt GUI** — Professional PySide6/Qt 6 interface with Light, Dark, and Blue Accent themes, keyboard shortcuts, and a live status bar.
- **Analytics Dashboard** — Charts showing prompt frequency over time, LLM platform distribution, token usage trends, and an activity timeline with date-range filtering.
- **Conversational Forking** — Visual tree-based prompt explorer for creating, branching, merging, and checking out conversation branches with fork-point metadata and strategy tracking.
- **Research Sessions** — Named sessions to group work into bounded periods, with auto-generated summaries and markdown export for research documentation.
- **Auto-Backup & Rollback** — Monitor project files for changes and automatically create timestamped backups. Restore any file from a previous backup with a diff preview.
- **Research Notes** — Timestamped project notes that serve as an audit trail for AI-assisted development decisions.
- **Profiles** — Save and load named configurations (selected folders, filters, headers) for switching between projects.
- **File & Token Management** — Select files and folders, filter by extension, and see real-time token counts. Combine files into a single prompt-ready text block.
- **Unified Database** — Single SQLite database (`llm_buddy.db`) storing all prompts, eADR notes, sessions, and conversation trees locally.

<!-- SCREENSHOT: Analytics Dashboard — show the charts tab with prompt frequency,
     LLM distribution pie chart, and token usage trends visible.
![Analytics Dashboard](docs/images/analytics-dashboard.png)
-->

<!-- SCREENSHOT: Conversational Forking — show the Prompt Explorer tab with a
     branching tree visualization containing multiple branches and fork points.
![Conversational Forking](docs/images/forking-tree.png)
-->

<!-- SCREENSHOT: Theme comparison — side-by-side or stacked showing the same tab
     in Light, Dark, and Blue Accent themes. Optional but nice to have.
![Themes](docs/images/themes-comparison.png)
-->

## Installation

Requires **Python 3.9+**.

### Windows

```bash
git clone https://github.com/avigi25/LLM-Buddy.git
cd LLM-Buddy
install.bat
```

The installer creates a virtual environment, installs dependencies, places an **LLM Buddy** shortcut on your Desktop, and optionally configures Claude Desktop MCP integration.

<!-- GIF: Windows installation — show running install.bat from start to finish,
     ending with the desktop shortcut and app launch. Speed up to ~15-20 seconds.
![Windows Installation](docs/images/windows-install.gif)
-->

### macOS / Linux

```bash
git clone https://github.com/avigi25/LLM-Buddy.git
cd LLM-Buddy
chmod +x install.sh
./install.sh
```

### Manual (pip)

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e .             # core only
pip install -e ".[all]"      # core + all optional components
```

Optional dependency groups: `proxy` (mitmproxy), `server` (Flask + Flask-CORS), `mcp` (Claude Desktop MCP), `all`.

## Usage

```
llm-buddy                  # Launch the GUI (default)
llm-buddy gui              # Launch the Qt GUI explicitly
llm-buddy server           # Start the Flask API server (port 5000)
llm-buddy server --port N  # Start on a custom port
llm-buddy proxy            # Start the HTTPS proxy recorder (port 8080)
llm-buddy proxy --port N   # Start the proxy on a custom port
llm-buddy mcp              # Start the MCP recorder for Claude Desktop
llm-buddy configure        # Configure Claude Desktop MCP integration
llm-buddy start-all        # Start API server + GUI together
```

## Architecture

```
+------------------+   +------------------+   +--------------+
|  Proxy Recorder  |   |  MCP Server      |   |  Flask API   |
|  (mitmproxy)     |   |  (Claude Desktop)|   |  (Extension) |
+--------+---------+   +--------+---------+   +------+-------+
         |                       |                    |
         v                       v                    v
    +----+--------------------------------------------+----+
    |              Unified PromptDatabase                   |
    |           (SQLite — llm_buddy.db)                     |
    +---------------------------+---------------------------+
                                |
                                v
                     +----------+----------+
                     |    GUI Application   |
                     |   (PySide6 / Qt 6)   |
                     +---------------------+
```

All capture methods write to the same `llm_buddy.db` database. The GUI auto-refreshes when a capture source is active.

## Prompt Capture Methods

Both the user's prompt (input) and the LLM's response (output) are captured and stored together.

### 1. Chrome Extension (Easiest)

Best for capturing from web-based LLM chat interfaces.

1. In the **Prompt Tracking** tab, find the **Capture Sources** section and click **Start Server**.
2. In Chrome, go to `chrome://extensions`, enable **Developer mode**, click **Load unpacked**, and select the `extension/` folder.
3. Use ChatGPT, Claude, Gemini, or Perplexity as normal. Prompts and responses are captured automatically.

<!-- SCREENSHOT: Chrome extension popup — show the extension popup with connection
     status and recent capture count while on a supported LLM site.
![Chrome Extension Popup](docs/images/extension-popup.png)
-->

The extension watches the DOM for the assistant's reply after each prompt submission, waits for the response to finish streaming, and sends both to the API server.

**Supported sites:** ChatGPT, Claude, Gemini, Perplexity, Grok, DeepSeek, Le Chat (Mistral), HuggingChat, Meta AI, Copilot, You.com, and Phind.

<!-- GIF: Chrome Extension capture in action — show sending a prompt in ChatGPT/Claude,
     then the prompt + response appearing in the Prompt Tracking tab automatically.
![Chrome Extension Capture](docs/images/extension-capture.gif)
-->

### 2. Claude Desktop (MCP)

Best if you primarily use the Claude Desktop app.

```bash
llm-buddy configure
```

This registers LLM Buddy's MCP server with Claude Desktop. Restart Claude Desktop and all prompts are recorded automatically.

The MCP server exposes the following tools to Claude Desktop:

| Tool | Description |
|------|-------------|
| `auto_record_prompt` | Silently records each user message and previous response on every turn |
| `toggle_auto_recording` | Enable or disable automatic recording |
| `register_active_files` | Associate specific file paths with subsequent prompts |
| `active_project_files` | Scan a project directory and register all matching files |
| `list_prompts` | List the most recent recorded prompts |
| `test_database_write` | Verify write access to the database |

<!-- SCREENSHOT: Claude Desktop with LLM Buddy MCP active — show Claude Desktop
     with a conversation where prompts are being silently recorded. Or show the
     Claude Desktop MCP config JSON.
![Claude Desktop MCP](docs/images/mcp-claude-desktop.png)
-->

### 3. HTTPS Proxy (Advanced)

Best for capturing API-level traffic including programmatic LLM calls.

In the **Prompt Tracking** tab, click **Start Proxy** in the Capture Sources section. This starts a mitmproxy instance on port 8080 and configures the system proxy. Both requests and responses are parsed and recorded. The proxy is automatically disabled when you stop it or close the app.

**Supported services:** OpenAI, Anthropic, Google Gemini, Perplexity, Grok/xAI, Mistral, DeepSeek, OpenRouter, Cohere, Together AI, Groq, DeepInfra, HuggingChat, Meta AI, Microsoft Copilot, You.com, Phind, and any OpenAI-compatible API.

<!-- GIF: Proxy capture — show clicking Start Proxy in the GUI, then making an API
     call (e.g. curl or a Python script), and the prompt appearing in the tracker.
![Proxy Capture](docs/images/proxy-capture.gif)
-->

### 4. Manual Entry

In the **Prompt Tracking** tab, use the **New Prompt** form to type or paste a prompt, select the LLM used, and click **Record Prompt**.

## REST API Endpoints

The Flask API server (started via `llm-buddy server` or the GUI's **Start Server** button) exposes these endpoints on `http://localhost:5000`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ping` | GET | Health check — returns status and prompt count |
| `/record_prompt` | POST | Record a new prompt (used by the Chrome extension) |
| `/prompts` | GET | Retrieve all recorded prompts |
| `/update_response` | POST | Update the response text for a previously recorded prompt |
| `/update_conversation_id` | POST | Update the conversation ID for a prompt |
| `/associate_prompt` | POST | Associate a file path with an existing prompt |

## GUI Tabs

<!-- SCREENSHOT: Tab bar showing all 12 tabs, or a 2x3 grid of screenshots showing
     the most important tabs: Prompt Tracking, Prompt Explorer, Sessions, Analytics,
     Auto-Backup, and Research Notes.
![GUI Tabs Overview](docs/images/gui-tabs-overview.png)
-->

| Tab | Purpose |
|-----|---------|
| **Research Notes** | Timestamped project notes for tracking decisions and progress |
| **Prompt Tracking** | Unified prompt/response history, capture source controls, file associations |
| **Prompt Explorer** | Visual conversational forking tree with branch management |
| **Sessions** | Named research sessions with auto-generated summaries and markdown export |
| **Analytics** | Charts for prompt frequency, LLM distribution, token usage, and activity timeline |
| **Preview** | Live preview of combined file text with dual token counts |
| **Compare Files** | Side-by-side diff viewer for any two text files |
| **Auto-Backup** | Configure and monitor automatic file backups |
| **Rollback** | Browse backups, preview diffs, restore files |
| **Logs** | Real-time application event log |
| **Help** | Built-in usage instructions and keyboard shortcuts |
| **About** | Version and dependency info |

<!-- SCREENSHOT: Sessions panel — show an active session with timer, prompt count,
     and the session list with completed sessions.
![Sessions Panel](docs/images/sessions-panel.png)
-->

<!-- SCREENSHOT: Rollback panel — show the backup browser with a diff preview
     comparing a current file against a previous backup version.
![Rollback Panel](docs/images/rollback-panel.png)
-->

## Building Standalone Executables

LLM Buddy can be packaged into standalone Windows executables using PyInstaller:

```bash
python build.py          # Build the distribution
python build.py clean    # Remove build artifacts
python build.py test     # Build and run a quick smoke test
```

The build produces three executables in `dist/LLM Buddy/`:

| Executable | Description |
|------------|-------------|
| `LLM Buddy.exe` | Main GUI application |
| `llm-buddy-mcp.exe` | MCP recorder for Claude Desktop |
| `llm-buddy-proxy.exe` | Standalone HTTPS proxy recorder |

The `extension/` folder is also included in the distribution for loading the Chrome extension.

## Project Structure

```
LLM-Buddy/
├── src/llm_buddy/
│   ├── cli.py                    # CLI entry point
│   ├── paths.py                  # Centralized path resolution (dev + frozen)
│   ├── core/
│   │   ├── backup.py             # Auto-backup logic
│   │   ├── database.py           # Unified prompt database (SQLite)
│   │   ├── eadr.py               # eADR note storage
│   │   ├── forking.py            # Conversational forking support
│   │   ├── profiles.py           # Profile save/load
│   │   ├── rollback.py           # File restoration and diffing
│   │   ├── sessions.py           # Research session management
│   │   └── tokens.py             # Token counting and text combining
│   ├── services/
│   │   ├── analytics_service.py  # Analytics data aggregation
│   │   ├── backup_service.py     # Backup orchestration
│   │   ├── file_service.py       # File scanning and filtering
│   │   ├── preview_service.py    # Preview text and eADR note generation
│   │   ├── prompt_service.py     # Prompt CRUD and file association
│   │   └── subprocess_manager.py # Background process and system proxy management
│   ├── qt/                       # PySide6 GUI
│   │   ├── app.py                # QApplication bootstrap
│   │   ├── main_window.py        # Main window, signals, menus, status bar
│   │   ├── theme.py              # Light, Dark, Blue Accent themes
│   │   ├── widgets/
│   │   │   └── toast.py          # Toast notification widget
│   │   └── panels/
│   │       ├── analytics_panel.py    # QtCharts analytics dashboard
│   │       ├── backup_panel.py       # Auto-backup with watchdog
│   │       ├── capture_widgets.py    # Extension server + proxy recorder
│   │       ├── compare_panel.py      # Side-by-side comparison
│   │       ├── control_panel.py      # File/folder selection and filters
│   │       ├── eadr_panel.py         # eADR Notes editor
│   │       ├── forking_panel.py      # Conversational forking visualization
│   │       ├── help_panel.py         # Help and About panels
│   │       ├── log_panel.py          # Application log
│   │       ├── preview_panel.py      # Combined text preview
│   │       ├── prompts_panel.py      # Prompt tracking and history
│   │       ├── rollback_panel.py     # File restoration from backups
│   │       └── sessions_panel.py     # Research session management
│   ├── recorders/
│   │   ├── api_server.py         # Flask REST API for prompt recording
│   │   ├── mcp_recorder.py       # Claude Desktop MCP server
│   │   ├── proxy_recorder.py     # mitmproxy-based HTTPS recorder
│   │   └── proxy_runner.py       # Programmatic mitmproxy entry point (PyInstaller)
│   └── scripts/
│       └── configure_claude.py   # Claude Desktop MCP setup
├── extension/                    # Chrome extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── interceptor.js
│   ├── popup.html
│   └── popup.js
├── tests/
├── build.py                      # PyInstaller build script
├── install.bat                   # Windows installer
├── install.sh                    # macOS/Linux installer
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

## Privacy & Security

All data is stored locally on your machine. There is no cloud sync, no telemetry, and no usage tracking. The HTTPS proxy should only be used for LLM services you own accounts for — see the Help tab in the app for detailed proxy security guidance.

## Technical Limitations

### Single-User, Local-Only Architecture

LLM Buddy is designed as a single-user desktop tool. All data is stored in a local SQLite database (`llm_buddy.db`) with no concurrent-access locking beyond SQLite's default file-level locks. Running multiple instances of the GUI simultaneously against the same database may result in "database locked" errors. There is no multi-user collaboration, cloud sync, or remote access capability.

### Chrome Extension DOM Fragility

The Chrome extension captures prompts and responses by querying DOM selectors specific to each supported LLM website (e.g., `#prompt-textarea` for ChatGPT, `.ProseMirror` for Claude). These selectors are inherently brittle — when an LLM provider redesigns their web interface, capture may silently break until the extension's `content.js` is updated with the new selectors. The extension currently supports ChatGPT, Claude, Gemini, Perplexity, Grok, DeepSeek, Le Chat (Mistral), HuggingChat, Meta AI, Copilot, You.com, and Phind, but each requires site-specific maintenance.

### HTTPS Proxy Certificate Requirements

The mitmproxy-based recorder requires installing a self-signed root certificate to intercept HTTPS traffic. This is a one-time setup per machine but can interfere with other applications if the system proxy is left enabled. The proxy and extension server cannot run simultaneously — only one capture source can be active at a time. Additionally, the proxy should never be used for sensitive traffic (banking, email) as it performs full TLS interception.

### Text-Only File Processing

The file aggregation and rollback features operate on plain text files only (source code, markdown, config files, etc.). Binary formats such as PDFs, Word documents, images, and compiled files are not supported for token counting, combining, or diff-based rollback. Complex document formats with embedded media present ongoing parsing challenges for the text processing pipeline.

### Token Counting Approximation

Token counts use OpenAI's `tiktoken` library with the `cl100k_base` encoding (GPT-4 tokenizer). This provides accurate counts for OpenAI models but is only an approximation for other LLMs (Claude, Gemini, Mistral, etc.) which use different tokenizers. Actual token usage on non-OpenAI platforms may differ by 5–15%.

### Platform-Specific Considerations

The application is primarily developed and tested on Windows. The macOS and Linux installers (`install.sh`) follow the same logic but PySide6/Qt 6 rendering may vary across Linux desktop environments and window managers. The system proxy auto-configuration (used by the HTTPS proxy recorder) uses Windows registry APIs on Windows and may require manual proxy configuration on some Linux distributions.

### No Git Integration

LLM Buddy provides its own file-to-prompt association system for tracking which files were involved in each prompt, but there is no automatic linking between prompts and Git commits, branches, or diffs. Correlating prompt activity with version control history currently requires manual cross-referencing by timestamp.

### Converging IDE-Integrated LLM Features

The LLM provider landscape is rapidly evolving in ways that overlap with LLM Buddy's feature set. Anthropic's Claude Code extension for VS Code now offers built-in conversation history, checkpoints, and the ability to fork conversations — capabilities that closely parallel LLM Buddy's session management and conversational forking features. Meanwhile, VS Code's February 2026 release (v1.110) introduced native chat session forking, context compaction, and third-party agent support for both Claude and OpenAI Codex directly through GitHub Copilot. Chat histories from Claude Code sessions are even syncing into GitHub Copilot's history panel automatically. As these IDE-native integrations mature, the standalone capture and session management value of a tool like LLM Buddy may diminish for developers already working within these ecosystems. However, LLM Buddy's cross-platform, provider-agnostic approach — capturing from any LLM service into a single unified database — and its research-oriented features (eADR notes, analytics, file-to-prompt association) remain differentiated from any single vendor's IDE integration.

### Evaluation Scope

The current evaluation is based on a single-researcher longitudinal study (1,555 prompts across six eADR iterations). Broader validation with multiple research teams across different DSR projects is needed to assess generalizability of the tool and methodology.

## Disclaimer

This software is provided for educational and research purposes only. LLM Buddy interacts with third-party services (including ChatGPT, Claude, Gemini, and others) by intercepting web traffic and DOM content. These techniques may conflict with the terms of service of individual LLM providers. Users are solely responsible for ensuring their use of this tool complies with all applicable terms of service, laws, and regulations.

This software is provided "as is" without warranty of any kind, express or implied. The authors assume no responsibility or liability for any consequences arising from the use of this tool. Features that depend on third-party website structures or APIs may break at any time without notice due to changes made by those providers.

## Citation

If you use LLM Buddy in your research, please cite:

```bibtex
@phdthesis{vigil2026adaptive,
  title={Adaptive Multi-Agent Intelligence: A Dynamic Data Management System
         for Enhanced Data Quality and Reconciliation},
  author={Vigil, Anthony Taeyang},
  year={2026},
  school={University of South Florida}
}
```

For the tool itself:

```bibtex
@software{vigil2026llmbuddy,
  author = {Vigil, Anthony Taeyang},
  title = {LLM Buddy: A Computer-Aided Method Engineering Tool
           for LLM-Augmented Research},
  year = {2025},
  url = {https://github.com/avigi25/LLM-Buddy},
  version = {3.1.0}
}
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

Anthony Vigil — anthony.vigil@usf.edu

**Version**: 3.1.0
**Last Updated**: March 2026

@§A_4a26e87a@ C:/LLM Buddy\requirements.txt

tiktoken>=0.5.0
watchdog>=3.0.0
requests>=2.31.0
python-dotenv>=1.0.0
PySide6>=6.6.0


@§A_4a26e87a@ C:/LLM Buddy\extension\background.js

/**
 * LLM Buddy - Background Service Worker
 * Receives prompts from content scripts and sends them to the Flask API.
 */

const DEFAULT_SERVER = "http://localhost:5000";

// Get the configured server URL
async function getServerUrl() {
  const result = await chrome.storage.local.get(["serverUrl"]);
  return result.serverUrl || DEFAULT_SERVER;
}

// Send a prompt to the LLM Buddy server
async function sendPrompt(data) {
  const serverUrl = await getServerUrl();
  try {
    const response = await fetch(`${serverUrl}/record_prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (response.ok) {
      const result = await response.json();
      // Update badge to show it's working
      chrome.action.setBadgeBackgroundColor({ color: "#4CAF50" });
      const countResult = await chrome.storage.local.get(["promptCount"]);
      const count = (countResult.promptCount || 0) + 1;
      await chrome.storage.local.set({ promptCount: count });
      chrome.action.setBadgeText({ text: String(count) });
      return result;
    } else {
      console.error("LLM Buddy: Server error", response.status);
      chrome.action.setBadgeBackgroundColor({ color: "#F44336" });
      chrome.action.setBadgeText({ text: "!" });
    }
  } catch (err) {
    console.error("LLM Buddy: Could not reach server", err.message);
    chrome.action.setBadgeBackgroundColor({ color: "#F44336" });
    chrome.action.setBadgeText({ text: "!" });
  }
  return null;
}

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PROMPT_CAPTURED") {
    sendPrompt(message.data).then((result) => {
      sendResponse({ success: !!result, result });
    });
    return true; // async response
  }

  if (message.type === "RESPONSE_CAPTURED") {
    sendResponse({ success: true }); // ack immediately
    updateResponse(message.data);    // fire-and-forget
    return false;
  }

  if (message.type === "CONVERSATION_ID_UPDATE") {
    sendResponse({ success: true });
    updateConversationId(message.data);
    return false;
  }

  if (message.type === "CHECK_SERVER") {
    getServerUrl().then(async (url) => {
      try {
        const resp = await fetch(`${url}/ping`);
        const data = await resp.json();
        sendResponse({ connected: true, data });
      } catch {
        sendResponse({ connected: false });
      }
    });
    return true;
  }
});

// Send a response update to the LLM Buddy server
async function updateResponse(data) {
  const serverUrl = await getServerUrl();
  try {
    const response = await fetch(`${serverUrl}/update_response`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt_id: data.promptId,
        response_text: data.responseText,
      }),
    });
    if (response.ok) {
      console.log("LLM Buddy: response saved for prompt", data.promptId);
    } else {
      console.error("LLM Buddy: failed to save response", response.status);
    }
  } catch (err) {
    console.error("LLM Buddy: could not send response", err.message);
  }
}

// Update the conversation_id for a prompt (used when the first message
// in a ChatGPT conversation gets a fallback ID that is corrected after
// the response arrives and the URL changes).
async function updateConversationId(data) {
  const serverUrl = await getServerUrl();
  try {
    const response = await fetch(`${serverUrl}/update_conversation_id`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt_id: data.promptId,
        conversation_id: data.conversationId,
      }),
    });
    if (response.ok) {
      console.log("LLM Buddy: conversation_id updated for prompt", data.promptId);
    } else {
      console.error("LLM Buddy: failed to update conversation_id", response.status);
    }
  } catch (err) {
    console.error("LLM Buddy: could not update conversation_id", err.message);
  }
}

// Clear badge and inject content scripts into already-open tabs on install/update
chrome.runtime.onInstalled.addListener(() => {
  // Reset prompt count
  chrome.storage.local.set({ promptCount: 0 });
  chrome.action.setBadgeText({ text: "" });

  // Get the matching URLs and scripts directly from the manifest
  const manifest = chrome.runtime.getManifest();
  const contentScripts = manifest.content_scripts[0];

  // Query all open tabs that match the LLM websites
  chrome.tabs.query({ url: contentScripts.matches }, (tabs) => {
    if (!tabs) return;
    
    // Inject the content script into each matching tab
    for (const tab of tabs) {
      // Ignore chrome:// or other restricted URLs just to be safe
      if (tab.url.startsWith("chrome://") || tab.url.startsWith("edge://")) continue;
      
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: contentScripts.js
      }).catch(err => {
        console.warn(`LLM Buddy: Could not inject into tab ${tab.id}`, err);
      });
    }
  });
});

@§A_4a26e87a@ C:/LLM Buddy\extension\content.js

/**
 * LLM Buddy - Content Script
 * Captures prompts AND responses from LLM websites.
 *
 * Supported sites:
 * - ChatGPT  (chatgpt.com, chat.openai.com)
 * - Claude   (claude.ai)
 * - Gemini   (gemini.google.com)
 * - Perplexity (perplexity.ai)
 * - Grok     (grok.com)
 * - DeepSeek (chat.deepseek.com)
 * - Le Chat  (chat.mistral.ai)
 * - HuggingChat (huggingface.co/chat)
 * - Meta AI  (meta.ai)
 * - Copilot  (copilot.microsoft.com)
 * - You.com  (you.com)
 * - Phind    (phind.com)
 */

(function () {
  "use strict";

  // Debug mode: run localStorage.setItem("llmBuddyDebug","1") in DevTools console to enable.
  // Shows which DOM selectors matched and when responses are detected.
  const DEBUG = (localStorage.getItem("llmBuddyDebug") === "1");
  function dbg(...args) { if (DEBUG) console.log("[LLM Buddy DBG]", ...args); }

  // Prevent double-injection
  if (window.__llmBuddyInjected) return;
  window.__llmBuddyInjected = true;

  const SITE = detectSite();
  if (!SITE) return;

  let lastPrompt = "";
  let lastConversationId = null;
  let debounceTimer = null;
  let lastPromptId = null;

  console.log(`LLM Buddy: monitoring ${SITE} for prompts and responses`);

  // --- Site detection ---
  function detectSite() {
    const host = location.hostname;
    if (host.includes("chatgpt.com") || host.includes("chat.openai.com")) return "ChatGPT";
    if (host.includes("claude.ai")) return "Claude";
    if (host.includes("gemini.google.com")) return "Gemini";
    if (host.includes("perplexity.ai")) return "Perplexity";
    if (host.includes("grok.com")) return "Grok";
    if (host.includes("chat.deepseek.com")) return "DeepSeek";
    if (host.includes("chat.mistral.ai")) return "Le Chat";
    if (host.includes("huggingface.co") && location.pathname.startsWith("/chat")) return "HuggingChat";
    if (host.includes("meta.ai")) return "Meta AI";
    if (host.includes("copilot.microsoft.com")) return "Copilot";
    if (host.includes("you.com")) return "You.com";
    if (host.includes("phind.com")) return "Phind";
    return null;
  }

  // --- Conversation ID extraction from URL ---
  function extractConversationId() {
    const path = location.pathname;
    // Claude.ai: /chat/{uuid}
    const claudeMatch = path.match(/\/chat\/([0-9a-f-]{8,})/i);
    if (claudeMatch) return claudeMatch[1];
    // ChatGPT: /c/{uuid}
    const gptMatch = path.match(/\/c\/([0-9a-f-]{8,})/i);
    if (gptMatch) return gptMatch[1];
    // Generic: last path segment if it looks like an ID (>= 8 chars, alphanumeric/dash/underscore)
    const segments = path.split("/").filter(Boolean);
    const last = segments[segments.length - 1] || "";
    if (last.length >= 8 && /^[a-z0-9_-]+$/i.test(last)) return last;
    // Fallback: hostname + path (stable within a conversation page)
    return location.hostname + path;
  }

  // --- Prompt extraction ---
  function getPromptText() {
    let text = "";

    if (SITE === "ChatGPT") {
      const el =
        document.querySelector("#prompt-textarea") ||
        document.querySelector('textarea[data-id="root"]') ||
        document.querySelector("textarea") ||
        document.querySelector('[contenteditable="true"]');
      if (el) text = el.innerText || el.value || "";
    }

    if (SITE === "Claude") {
      const el =
        document.querySelector('[contenteditable="true"].ProseMirror') ||
        document.querySelector('[contenteditable="true"]') ||
        document.querySelector("textarea");
      if (el) text = el.innerText || el.value || "";
    }

    if (SITE === "Gemini") {
      const el =
        document.querySelector(".ql-editor") ||
        document.querySelector('[contenteditable="true"]') ||
        document.querySelector("textarea");
      if (el) text = el.innerText || el.value || "";
    }

    if (SITE === "Perplexity") {
      const el =
        document.querySelector('[contenteditable="true"][data-placeholder]') ||
        document.querySelector("textarea") ||
        document.querySelector('[contenteditable="true"]');
      if (el) { dbg("Perplexity prompt selector matched", el); text = el.innerText || el.value || ""; }
    }

    // Generic fallback for Grok, DeepSeek, Le Chat, HuggingChat,
    // Meta AI, Copilot, You.com, Phind, and any future providers
    if (!text) {
      const el =
        document.querySelector('[role="textbox"]') ||
        document.querySelector("textarea") ||
        document.querySelector('[contenteditable="true"]');
      if (el) text = el.innerText || el.value || "";
    }

    return text.trim();
  }

  // --- Claude: extract response text without extended-thinking sections ---
  // Claude streams its thinking process first (visible in a collapsible <details> block
  // labelled "Claude's thinking"), then streams the actual prose response.
  // Without this, the MutationObserver fires during the thinking phase and captures
  // thinking output instead of (or mixed with) the real answer.
  function claudeExtractResponseText(turnEl) {
    if (!turnEl) return "";
    // Clone so we can mutate freely
    const clone = turnEl.cloneNode(true);
    // Remove thinking containers: <details> elements and any element marked as thinking
    clone.querySelectorAll(
      'details, [class*="thinking"], [data-is-thinking], [data-testid*="thinking"]'
    ).forEach(n => n.remove());
    // textContent works on detached nodes (innerText requires layout)
    const withoutThinking = clone.textContent.trim();
    // If stripping thinking left real content, use it; otherwise fall back to full text
    // (handles edge case where the entire response is just the thinking block)
    if (withoutThinking.length > 10) {
      dbg("Claude: response after stripping thinking =", withoutThinking.length, "chars");
      return withoutThinking;
    }
    dbg("Claude: thinking strip left nothing, using full innerText");
    return turnEl.innerText.trim();
  }

  // --- Response extraction from DOM ---
  function getLastAssistantMessage() {
    let el = null;

    if (SITE === "ChatGPT") {
      const msgs = document.querySelectorAll(
        '[data-message-author-role="assistant"], [data-message-author="assistant"], .agent-turn'
      );
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        const md = el.querySelector(".markdown, .prose");
        if (md) el = md;
      }
      if (el) { dbg("ChatGPT response selector matched", el); return el.innerText.trim(); }
    }

    if (SITE === "Claude") {
      // Use stable data-testid — filter out human turns (they have a contenteditable child)
      const turns = document.querySelectorAll('[data-testid="conversation-turn"]');
      const assistantTurns = Array.from(turns).filter(t => !t.querySelector('[contenteditable="true"]'));
      if (assistantTurns.length > 0) {
        el = assistantTurns[assistantTurns.length - 1];
        dbg("Claude response selector: data-testid conversation-turn (assistant)", el);
        // Strip extended-thinking sections (<details> elements) so we don't capture
        // Claude's thinking output instead of its final prose response.
        return claudeExtractResponseText(el);
      }
      // Fallback: data-is-streaming attribute
      const streaming = document.querySelectorAll('[data-is-streaming]');
      if (streaming.length > 0) {
        el = streaming[streaming.length - 1];
        dbg("Claude response selector: data-is-streaming", el);
        return claudeExtractResponseText(el);
      }
    }

    if (SITE === "Gemini") {
      // model-response is a custom element; try shadow root first, then textContent
      const modelResponses = document.querySelectorAll("model-response");
      if (modelResponses.length > 0) {
        const last = modelResponses[modelResponses.length - 1];
        const shadowContent = last.shadowRoot?.querySelector(".response-content, .markdown");
        const text = shadowContent ? shadowContent.innerText : last.innerText || last.textContent;
        if (text && text.trim()) {
          dbg("Gemini response selector: model-response", last);
          return text.trim();
        }
      }
      // Newer Gemini UI uses data attribute without Shadow DOM
      const modelMsgs = document.querySelectorAll('[data-message-author="model"]');
      if (modelMsgs.length > 0) {
        el = modelMsgs[modelMsgs.length - 1];
        dbg("Gemini response selector: data-message-author=model", el);
        return el.innerText.trim();
      }
    }

    if (SITE === "Perplexity") {
      // data-testid="answer" is the most stable selector
      const answer = document.querySelector('[data-testid="answer"]');
      if (answer) {
        dbg("Perplexity response selector: data-testid=answer", answer);
        return answer.innerText.trim();
      }
      const msgs = document.querySelectorAll('.prose.break-words, [class*="AnswerBody"]');
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        dbg("Perplexity response selector: prose.break-words / AnswerBody", el);
        return el.innerText.trim();
      }
    }

    if (SITE === "Grok") {
      const msgs = document.querySelectorAll(
        '[data-message-author="assistant"], [class*="MessageBubble"], [class*="message-bubble"]'
      );
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        dbg("Grok response selector matched", el);
        return el.innerText.trim();
      }
    }

    if (SITE === "DeepSeek") {
      // ds-markdown contains the rendered response; r1-thinking contains reasoning
      const thinking = document.querySelectorAll('[class*="r1-thinking"]');
      const content = document.querySelectorAll('[class*="ds-markdown"]');
      if (content.length > 0) {
        const lastContent = content[content.length - 1].innerText.trim();
        const lastThinking = thinking.length > 0 ? thinking[thinking.length - 1].innerText.trim() : "";
        dbg("DeepSeek response selector: ds-markdown", content[content.length - 1]);
        if (lastThinking) return `<thinking>\n${lastThinking}\n</thinking>\n\n${lastContent}`;
        return lastContent;
      }
    }

    if (SITE === "HuggingChat") {
      const msgs = document.querySelectorAll('.message.bot [class*="prose"], [data-role="assistant"]');
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        dbg("HuggingChat response selector matched", el);
        return el.innerText.trim();
      }
    }

    if (SITE === "Le Chat") {
      const msgs = document.querySelectorAll(
        '[data-message-author="assistant"], [class*="assistant-message"]'
      );
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        dbg("Le Chat response selector matched", el);
        return el.innerText.trim();
      }
    }

    if (SITE === "Meta AI") {
      const msgs = document.querySelectorAll(
        '[aria-label*="AI said"], [class*="AssistantMessage"]'
      );
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        dbg("Meta AI response selector matched", el);
        return el.innerText.trim();
      }
    }

    if (SITE === "Copilot") {
      const msgs = document.querySelectorAll(
        '[data-content="ai-response"], .cib-message-group.response-message'
      );
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        dbg("Copilot response selector matched", el);
        return el.innerText.trim();
      }
    }

    if (SITE === "You.com") {
      const msgs = document.querySelectorAll(
        '[class*="youChatResponse"], [data-testid="you-chat-response"]'
      );
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        dbg("You.com response selector matched", el);
        return el.innerText.trim();
      }
    }

    if (SITE === "Phind") {
      const msgs = document.querySelectorAll('[class*="PhindReply"], .markdown');
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        dbg("Phind response selector matched", el);
        return el.innerText.trim();
      }
    }

    // Generic fallback for any unrecognized provider
    const selectors = [
      '[data-message-author="assistant"]',
      '[data-role="assistant"]',
      '[class*="assistant"]',
      '[class*="response"]',
      '[class*="answer"]',
      '[class*="message-content"]',
      '[class*="prose"]',
      '[class*="markdown"]',
    ];
    const msgs = document.querySelectorAll(selectors.join(", "));
    if (msgs.length > 0) {
      el = msgs[msgs.length - 1];
      dbg("Generic fallback response selector matched", el);
    }

    return el ? el.innerText.trim() : "";
  }

  // --- Send prompt to background ---
  // --- Send prompt to background ---
  function capturePrompt(text, attachments, interceptorConversationId, parentMessageId, messagesCount) {
    if ((!text || text.length < 2) && !attachments) return;
    const currentConvId = interceptorConversationId || extractConversationId();
    if (text === lastPrompt && !attachments && currentConvId === lastConversationId) return;
    lastPrompt = text;
    lastConversationId = currentConvId;

    console.log(`LLM Buddy: captured ${SITE} prompt (${(text || "").length} chars${attachments ? `, ${attachments.length} attachment(s)` : ""})`);

    try {
      chrome.runtime.sendMessage(
        {
          type: "PROMPT_CAPTURED",
          data: {
            llmName: SITE,
            promptText: text || "",
            url: location.href,
            pageTitle: document.title,
            modelName: SITE,
            conversationId: currentConvId,
            attachments: attachments || undefined,
            parentMessageId: parentMessageId || undefined,
            messagesCount: messagesCount || undefined,
          },
        },
        (response) => {
          if (chrome.runtime.lastError) {
             console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
             return;
          }
          if (response && response.result && response.result.prompt_id) {
            lastPromptId = response.result.prompt_id;
            watchForResponse(lastPromptId);
            // If the conversation_id was a fallback (no UUID in URL),
            // watch for URL changes to get the real one.
            if (currentConvId && !/[0-9a-f]{8,}-/.test(currentConvId)) {
              watchForConversationId(lastPromptId, currentConvId);
            }
          }
        }
      );
    } catch (e) {
      if (e.message.includes("Extension context invalidated")) {
        console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
      } else {
        console.error("LLM Buddy error:", e);
      }
    }
  }

  // --- Watch for URL change to get the real conversation_id ---
  // ChatGPT (and others) create the conversation_id only after the
  // first response.  The URL changes from e.g. chatgpt.com/ to
  // chatgpt.com/c/{uuid}.  When that happens, send an update so the
  // prompt is grouped correctly.
  function watchForConversationId(promptId, fallbackCid) {
    let checks = 0;
    const MAX = 30; // 30 seconds max
    const timer = setInterval(() => {
      checks++;
      const newCid = extractConversationId();
      if (newCid && newCid !== fallbackCid && /[0-9a-f]{8,}-/.test(newCid)) {
        clearInterval(timer);
        console.log(`LLM Buddy: updated conversation_id for prompt ${promptId}: ${fallbackCid} -> ${newCid}`);
        try {
          chrome.runtime.sendMessage({
            type: "CONVERSATION_ID_UPDATE",
            data: { promptId, conversationId: newCid },
          });
        } catch (e) {
          // Extension context may be invalidated
        }
      }
      if (checks >= MAX) clearInterval(timer);
    }, 1000);
  }

  // --- Send captured response to background ---
  function sendResponseCapture(promptId, responseText) {
    try {
      chrome.runtime.sendMessage({
        type: "RESPONSE_CAPTURED",
        data: { promptId, responseText },
      }, () => {
        if (chrome.runtime.lastError) {
          console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
        }
      });
    } catch (e) {
      if (e.message && e.message.includes("Extension context invalidated")) {
        console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
      } else {
        console.error("LLM Buddy error:", e);
      }
    }
  }

  // --- Watch for LLM response after prompt submission ---
  // Uses MutationObserver with a 1500ms debounce to detect when streaming stops.
  // Falls back to a 3-minute hard timeout to capture partial responses.
  function watchForResponse(promptId) {
    // Snapshot the pre-existing DOM content to avoid capturing the previous turn.
    const initialContent = getLastAssistantMessage();
    let latestContent = "";
    let debounceTimer = null;
    let captured = false;

    const MAX_MS = 3 * 60 * 1000; // 3 minutes hard timeout
    const DEBOUNCE_MS = 1500;      // settle time after last DOM mutation

    function fireCapture(content, reason) {
      if (captured) return;
      captured = true;
      observer.disconnect();
      clearTimeout(debounceTimer);
      clearTimeout(hardTimeout);
      console.log(`LLM Buddy: captured ${SITE} response (${content.length} chars, ${reason})`);
      dbg("Response content preview:", content.slice(0, 200));
      sendResponseCapture(promptId, content);
    }

    function onMutation() {
      const currentContent = getLastAssistantMessage();
      // Ignore until new content appears (different from pre-existing snapshot)
      if (!currentContent || currentContent === initialContent) return;
      latestContent = currentContent;

      // Reset debounce on every mutation
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        if (latestContent && latestContent !== initialContent) {
          fireCapture(latestContent, "debounce");
        }
      }, DEBOUNCE_MS);
    }

    const observer = new MutationObserver(onMutation);
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });
    dbg("MutationObserver started for prompt", promptId);

    // Hard timeout: disconnect observer and save whatever we have
    const hardTimeout = setTimeout(() => {
      observer.disconnect();
      clearTimeout(debounceTimer);
      if (!captured && latestContent && latestContent !== initialContent && latestContent.length > 10) {
        console.log(`LLM Buddy: response timeout, saving partial (${latestContent.length} chars)`);
        sendResponseCapture(promptId, latestContent);
      }
    }, MAX_MS);
  }

  // --- Detect submissions ---

  // Method 1: Watch for Enter key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      const text = getPromptText();
      if (text) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => capturePrompt(text), 100);
      }
    }
  }, true);

  // Method 2: Watch for send button clicks
  function setupButtonWatcher() {
    document.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;

      const isSend =
        btn.getAttribute("data-testid") === "send-button" ||
        btn.getAttribute("aria-label")?.toLowerCase().includes("send") ||
        btn.querySelector('svg path[d*="M2"]') ||
        btn.classList.toString().toLowerCase().includes("send");

      if (isSend) {
        const text = getPromptText();
        if (text) {
          clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => capturePrompt(text), 100);
        }
      }
    }, true);
  }

  // Method 3: Injected fetch interceptor using CustomEvent bridge
  // Inject the script as a file to comply with CSP restrictions
  const script = document.createElement("script");
  script.src = chrome.runtime.getURL("interceptor.js");
  (document.head || document.documentElement).appendChild(script);
  
  // Clean up the script tag after it executes
  script.onload = function() {
    this.remove();
  };

  // Listen for messages bridged from the injected script
  window.addEventListener("LLMBuddy_Capture", (e) => {
    const detail = e.detail;
    // Support both old format (string) and new format ({text, attachments})
    const text = typeof detail === "string" ? detail : detail?.text;
    const isObj = typeof detail === "object" && detail !== null;
    const attachments = isObj ? detail?.attachments : null;
    const conversationId = isObj ? detail?.conversationId : null;
    const parentMessageId = isObj ? detail?.parentMessageId : null;
    const messagesCount = isObj ? detail?.messagesCount : null;
    if (text || attachments) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => capturePrompt(text, attachments, conversationId, parentMessageId, messagesCount), 50);
    }
  });

  // Listen for conversation_id updates from the interceptor (fired when
  // the first SSE response chunk contains the real conversation_id).
  window.addEventListener("LLMBuddy_ConvIdUpdate", (e) => {
    const newCid = e.detail?.conversationId;
    if (newCid && lastPromptId) {
      console.log(`LLM Buddy: got conversation_id from response: ${newCid}`);
      try {
        chrome.runtime.sendMessage({
          type: "CONVERSATION_ID_UPDATE",
          data: { promptId: lastPromptId, conversationId: newCid },
        });
      } catch (err) {
        // Extension context may be invalidated
      }
    }
  });

  // Initialize
  setupButtonWatcher();

})();

@§A_4a26e87a@ C:/LLM Buddy\extension\interceptor.js

(function() {
  const originalFetch = window.fetch;

  function isLLMEndpoint(url) {
    const patterns = [
      /backend-api\/conversation/,           // ChatGPT web UI
      /backend-api\/f\/conversation/,        // ChatGPT (alternate)
      /openai\.com\/v1\/(?:chat\/)?completions/, // OpenAI API
      /api\.anthropic\.com\/v1\/messages/,   // Anthropic API
      /api\/append_message/,                 // Claude web UI
      /chat_conversations\/.*\/completion/,  // Claude web UI
      /GenerateContent/,                     // Gemini API
      /gemini\.google\.com.*\/f\//,          // Gemini web UI
      /generativelanguage\.googleapis\.com/, // Gemini API
      /rest\/app-chat\/conversations/,       // Grok web UI
      /api\.x\.ai\/v1\/(?:chat\/)?completions/, // Grok API
      /chat\.deepseek\.com\/api/,            // DeepSeek
      /api\.deepseek\.com\/v1/,              // DeepSeek API
      /chat\.mistral\.ai\/api/,              // Le Chat
      /api\.mistral\.ai/,                    // Mistral API
      /huggingface\.co\/chat\/conversation/, // HuggingChat
      /copilot\.microsoft\.com.*\/api/,      // Copilot
      /sydney\.bing\.com\/sydney/,           // Copilot (Bing backend)
      /you\.com\/api\/(?:streamingSearch|chat)/, // You.com
      /phind\.com\/api\/infer/,              // Phind
      /meta\.ai\/api/,                       // Meta AI
      /perplexity\.ai\/api/,                 // Perplexity
      /openrouter\.ai\/api\/v1/,             // OpenRouter
      /api\.groq\.com/,                      // Groq
      /api\.cohere\.ai/,                     // Cohere
    ];
    return patterns.some(p => p.test(url));
  }

  function extractPromptFromBody(body) {
    // Copilot throttled format: arguments[0].messages[-1].text
    if (body.arguments && Array.isArray(body.arguments) && body.arguments[0]?.messages) {
      const msgs = body.arguments[0].messages;
      const userMsgs = msgs.filter(m => m.author === "user" || m.role === "user");
      if (userMsgs.length > 0) {
        const last = userMsgs[userMsgs.length - 1];
        if (last.text) return last.text;
        if (typeof last.content === "string") return last.content;
      }
    }
    // Meta AI GraphQL format: variables.message or variables.query
    if (body.variables) {
      if (body.variables.message) return body.variables.message;
      if (body.variables.query) return body.variables.query;
    }
    // Standard OpenAI/Anthropic messages array
    if (body.messages) {
      const userMsgs = body.messages.filter(m => m.role === "user" || m.author?.role === "user");
      if (userMsgs.length > 0) {
        const last = userMsgs[userMsgs.length - 1];
        const content = last.content || last;
        if (typeof content === "string") return content;
        // ChatGPT Web UI: content.parts may contain mixed strings and objects
        if (content.parts) {
          const textParts = content.parts.filter(p => typeof p === "string");
          return textParts.join(" ");
        }
        if (content.text) return content.text;
      }
    }
    if (body.prompt) return body.prompt;
    if (body.text) return body.text;
    if (body.query) return body.query;
    if (body.message && typeof body.message === "string") return body.message;
    // Gemini API: contents[].parts[].text
    if (body.contents) {
      const parts = body.contents.flatMap(c => c.parts || []).filter(p => p.text).map(p => p.text);
      if (parts.length) return parts.join(" ");
    }
    return null;
  }

  function extractAttachmentsFromBody(body) {
    const attachments = [];

    if (body.messages) {
      const userMsgs = body.messages.filter(m => m.role === "user" || m.author?.role === "user");
      if (userMsgs.length > 0) {
        const last = userMsgs[userMsgs.length - 1];
        const content = last.content || last;

        // OpenAI/Claude-style content array
        if (Array.isArray(content)) {
          for (const item of content) {
            if (item.type === "image_url") {
              const url = item.image_url?.url || "";
              attachments.push({
                type: "image",
                source: url.startsWith("data:") ? "base64" : "url",
                mediaType: url.startsWith("data:") ? url.split(";")[0].replace("data:", "") : null,
              });
            } else if (item.type === "image") {
              attachments.push({
                type: "image",
                mediaType: item.source?.media_type || null,
                source: item.source?.type || "unknown",
              });
            } else if (item.type === "document") {
              attachments.push({
                type: "document",
                mediaType: item.source?.media_type || null,
                source: item.source?.type || "unknown",
                name: item.name || null,
              });
            }
          }
        }

        // ChatGPT Web UI multimodal parts
        if (content?.parts && Array.isArray(content.parts)) {
          for (const part of content.parts) {
            if (typeof part === "object" && part !== null) {
              const ct = part.content_type || "";
              if (ct === "image_asset_pointer") {
                attachments.push({ type: "image", source: "chatgpt_asset" });
              } else if (ct.includes("file") || ct.includes("document")) {
                attachments.push({ type: "document", source: "chatgpt_asset", name: part.name || null });
              }
            }
          }
        }
      }
    }

    // Gemini format
    if (body.contents) {
      for (const c of body.contents) {
        for (const part of (c.parts || [])) {
          if (part.inline_data) {
            attachments.push({
              type: part.inline_data.mime_type?.startsWith("image/") ? "image" : "document",
              mediaType: part.inline_data.mime_type,
              source: "inline_base64",
            });
          } else if (part.file_data) {
            attachments.push({
              type: "document",
              mediaType: part.file_data.mime_type,
              source: "file_uri",
            });
          }
        }
      }
    }

    // Claude web UI /completion endpoint: top-level attachments array
    // Format: [{file_name, file_type, file_size, extracted_content, id, ...}]
    if (body.attachments && Array.isArray(body.attachments)) {
      for (const att of body.attachments) {
        if (!att || typeof att !== "object") continue;
        const fileType = att.file_type || "";
        attachments.push({
          type: fileType.startsWith("image/") ? "image" : "document",
          mediaType: fileType || null,
          source: "claude_web",
          name: att.file_name || null,
        });
      }
    }
    // Claude web UI may also have a separate 'files' array
    if (body.files && Array.isArray(body.files)) {
      for (const f of body.files) {
        if (!f || typeof f !== "object") continue;
        const fileType = f.file_type || f.mime_type || "";
        const name = f.file_name || f.name || null;
        if (name || fileType) {
          attachments.push({
            type: fileType.startsWith("image/") ? "image" : "document",
            mediaType: fileType || null,
            source: "claude_web",
            name,
          });
        }
      }
    }

    return attachments.length > 0 ? attachments : null;
  }

  window.fetch = async function(...args) {
    const [resource, config] = args;
    const url = typeof resource === "string" ? resource : resource?.url || "";

    let needsConvIdFromResponse = false;

    if (config?.method === "POST" && config?.body && isLLMEndpoint(url)) {
      try {
        const body = typeof config.body === "string" ? JSON.parse(config.body) : config.body;
        const prompt = extractPromptFromBody(body);
        const attachments = extractAttachmentsFromBody(body);
        // Extract conversation metadata from request body if available
        const conversationId = body.conversation_id || body.conversationId || null;
        const parentMessageId = body.parent_message_id
          || body.parent_message_uuid  // Claude web UI
          || null;
        // Count messages from various API formats
        const messagesCount = body.messages ? body.messages.length
          : body.contents ? body.contents.length
          : null;
        if (prompt || attachments) {
          window.dispatchEvent(new CustomEvent("LLMBuddy_Capture", {
            detail: {
              text: prompt,
              attachments: attachments,
              conversationId: conversationId,
              parentMessageId: parentMessageId,
              messagesCount: messagesCount,
            }
          }));
          // If no conversation_id in request, try to extract from response
          if (!conversationId) {
            needsConvIdFromResponse = true;
          }
        }
      } catch (e) {
        // Ignore parse errors safely
      }
    }

    const response = originalFetch.apply(this, args);

    // For first messages (no conversation_id in request), read the first
    // chunk of the SSE response to extract the conversation_id.
    if (needsConvIdFromResponse) {
      response.then(function(resp) {
        try {
          const clone = resp.clone();
          const reader = clone.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          function readChunk() {
            reader.read().then(function(result) {
              if (result.done) return;
              buffer += decoder.decode(result.value, {stream: true});
              const match = buffer.match(/"conversation_id"\s*:\s*"([^"]+)"/);
              if (match) {
                reader.cancel().catch(function(){});
                window.dispatchEvent(new CustomEvent("LLMBuddy_ConvIdUpdate", {
                  detail: { conversationId: match[1] }
                }));
                return;
              }
              // Read up to 20KB to find the conversation_id
              if (buffer.length < 20000) readChunk();
              else reader.cancel().catch(function(){});
            }).catch(function(){});
          }
          readChunk();
        } catch (e) {
          // Ignore errors — this is a best-effort enhancement
        }
      }).catch(function(){});
    }

    return response;
  };
})();


@§A_4a26e87a@ C:/LLM Buddy\extension\manifest.json

{
  "manifest_version": 3,
  "name": "LLM Buddy - Prompt Recorder",
  "version": "1.0.0",
  "description": "Automatically records prompts from ChatGPT, Claude, Gemini, Perplexity, Grok, DeepSeek, and more to LLM Buddy.",
  "permissions": [
    "storage",
    "scripting"
  ],
  "host_permissions": [
    "http://localhost:5000/*",
    "*://chatgpt.com/*",
    "*://chat.openai.com/*",
    "*://claude.ai/*",
    "*://gemini.google.com/*",
    "*://perplexity.ai/*",
    "*://www.perplexity.ai/*",
    "*://grok.com/*",
    "*://www.grok.com/*",
    "*://chat.deepseek.com/*",
    "*://chat.mistral.ai/*",
    "*://huggingface.co/*",
    "*://meta.ai/*",
    "*://www.meta.ai/*",
    "*://copilot.microsoft.com/*",
    "*://you.com/*",
    "*://www.you.com/*",
    "*://phind.com/*",
    "*://www.phind.com/*"
  ],
  "content_scripts": [
    {
      "matches": [
        "*://chatgpt.com/*",
        "*://chat.openai.com/*",
        "*://claude.ai/*",
        "*://gemini.google.com/*",
        "*://perplexity.ai/*",
        "*://www.perplexity.ai/*",
        "*://grok.com/*",
        "*://www.grok.com/*",
        "*://chat.deepseek.com/*",
        "*://chat.mistral.ai/*",
        "*://huggingface.co/chat/*",
        "*://meta.ai/*",
        "*://www.meta.ai/*",
        "*://copilot.microsoft.com/*",
        "*://you.com/*",
        "*://www.you.com/*",
        "*://phind.com/*",
        "*://www.phind.com/*"
      ],
      "js": ["content.js"],
      "run_at": "document_idle"
    }
  ],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  },
  "web_accessible_resources": [
    {
      "resources": ["interceptor.js"],
      "matches": [
        "*://chatgpt.com/*",
        "*://chat.openai.com/*",
        "*://claude.ai/*",
        "*://gemini.google.com/*",
        "*://perplexity.ai/*",
        "*://www.perplexity.ai/*",
        "*://grok.com/*",
        "*://www.grok.com/*",
        "*://chat.deepseek.com/*",
        "*://chat.mistral.ai/*",
        "*://huggingface.co/*",
        "*://meta.ai/*",
        "*://www.meta.ai/*",
        "*://copilot.microsoft.com/*",
        "*://you.com/*",
        "*://www.you.com/*",
        "*://phind.com/*",
        "*://www.phind.com/*"
      ]
    }
  ]
}

@§A_4a26e87a@ C:/LLM Buddy\extension\popup.html

<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {
      width: 300px;
      padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 13px;
      color: #333;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 16px;
      color: #1a1a1a;
    }
    .status {
      padding: 8px 12px;
      border-radius: 6px;
      margin-bottom: 12px;
      font-weight: 500;
    }
    .connected { background: #e8f5e9; color: #2e7d32; }
    .disconnected { background: #ffebee; color: #c62828; }
    .stat { display: flex; justify-content: space-between; padding: 4px 0; }
    .stat-label { color: #666; }
    .stat-value { font-weight: 600; }
    hr { border: none; border-top: 1px solid #eee; margin: 12px 0; }
    .settings { margin-top: 8px; }
    .settings label { display: block; margin-bottom: 4px; color: #666; font-size: 12px; }
    .settings input {
      width: 100%; padding: 6px 8px; border: 1px solid #ddd;
      border-radius: 4px; font-size: 12px; box-sizing: border-box;
    }
    .btn {
      width: 100%; padding: 8px; margin-top: 8px; border: none;
      border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500;
    }
    .btn-primary { background: #1976d2; color: white; }
    .btn-secondary { background: #f5f5f5; color: #333; border: 1px solid #ddd; }
    .btn:hover { opacity: 0.9; }
    .sites { font-size: 11px; color: #888; margin-top: 8px; }
  </style>
</head>
<body>
  <h2>LLM Buddy</h2>

  <div id="status" class="status disconnected">Checking connection...</div>

  <div class="stat">
    <span class="stat-label">Prompts captured</span>
    <span class="stat-value" id="count">0</span>
  </div>
  <div class="stat">
    <span class="stat-label">Server prompts</span>
    <span class="stat-value" id="serverCount">-</span>
  </div>

  <hr>

  <div class="settings">
    <label>Server URL</label>
    <input type="text" id="serverUrl" value="http://localhost:5000">
    <button class="btn btn-primary" id="saveBtn">Save & Test Connection</button>
    <button class="btn btn-secondary" id="resetBtn">Reset Count</button>
  </div>

  <div class="sites">
    Monitoring: ChatGPT, Claude, Gemini, Perplexity, Grok, DeepSeek, Le Chat, HuggingChat, Meta AI, Copilot, You.com, Phind
  </div>

  <script src="popup.js"></script>
</body>
</html>


@§A_4a26e87a@ C:/LLM Buddy\extension\popup.js

/**
 * LLM Buddy - Popup Script
 */

const statusEl = document.getElementById("status");
const countEl = document.getElementById("count");
const serverCountEl = document.getElementById("serverCount");
const urlInput = document.getElementById("serverUrl");
const saveBtn = document.getElementById("saveBtn");
const resetBtn = document.getElementById("resetBtn");

// Load saved settings
chrome.storage.local.get(["serverUrl", "promptCount"], (result) => {
  if (result.serverUrl) urlInput.value = result.serverUrl;
  countEl.textContent = result.promptCount || 0;
  checkConnection();
});

// Check connection to server
async function checkConnection() {
  try {
    const resp = await chrome.runtime.sendMessage({ type: "CHECK_SERVER" });
    if (resp && resp.connected) {
      statusEl.className = "status connected";
      statusEl.textContent = "Connected to LLM Buddy";
      if (resp.data && resp.data.prompt_count !== undefined) {
        serverCountEl.textContent = resp.data.prompt_count;
      }
    } else {
      statusEl.className = "status disconnected";
      statusEl.textContent =
        "Not connected — start the server in LLM Buddy";
    }
  } catch {
    statusEl.className = "status disconnected";
    statusEl.textContent = "Not connected — start the server in LLM Buddy";
  }
}

// Save settings
saveBtn.addEventListener("click", () => {
  const url = urlInput.value.trim().replace(/\/$/, "");
  chrome.storage.local.set({ serverUrl: url }, () => {
    checkConnection();
  });
});

// Reset count
resetBtn.addEventListener("click", () => {
  chrome.storage.local.set({ promptCount: 0 }, () => {
    countEl.textContent = "0";
    chrome.action.setBadgeText({ text: "" });
  });
});


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\cli.py

"""
CLI entry point for LLM Buddy.

Usage:
    llm-buddy              Launch the GUI (default)
    llm-buddy gui          Launch the GUI explicitly
    llm-buddy proxy        Start the proxy recorder only
    llm-buddy server       Start the Flask API server only
    llm-buddy mcp          Start the MCP recorder only
    llm-buddy configure    Configure Claude Desktop MCP integration
    llm-buddy start-all    Start all background services + GUI
"""

import argparse
import sys


def _cmd_gui(args):
    """Launch the PySide6 GUI."""
    from llm_buddy.qt.app import main as qt_main
    qt_main()


def _cmd_proxy(args):
    """Start the mitmproxy-based recorder."""
    try:
        import subprocess
        addon = _find_module_path("llm_buddy.recorders.proxy_recorder")
        cmd = [
            sys.executable, "-m", "mitmproxy",
            "--mode", "regular",
            "--listen-port", str(args.port),
            "-s", addon,
        ]
        print(f"Starting proxy recorder on port {args.port} ...")
        subprocess.run(cmd)
    except ImportError:
        print("Error: mitmproxy is not installed.")
        print("Install it with:  pip install llm-buddy[proxy]")
        sys.exit(1)


def _cmd_server(args):
    """Start the Flask REST API server."""
    try:
        from llm_buddy.recorders.api_server import app
        print(f"Starting Flask API server on port {args.port} ...")
        app.run(host="127.0.0.1", port=args.port, debug=args.debug)
    except ImportError as e:
        print(f"Error: {e}")
        print("Install Flask with:  pip install llm-buddy[server]")
        sys.exit(1)


def _cmd_mcp(args):
    """Start the MCP recorder for Claude Desktop."""
    try:
        from llm_buddy.recorders.mcp_recorder import mcp
        print("Starting MCP recorder ...")
        mcp.run()
    except ImportError as e:
        print(f"Error: {e}")
        print("Install MCP with:  pip install llm-buddy[mcp]")
        sys.exit(1)


def _cmd_configure(args):
    """Configure Claude Desktop to use LLM Buddy's MCP server."""
    from llm_buddy.scripts.configure_claude import update_claude_config
    update_claude_config()


def _cmd_start_all(args):
    """Start background services and the GUI."""
    import threading
    import subprocess

    # Start Flask server in background
    try:
        from llm_buddy.recorders.api_server import app as flask_app
        server_thread = threading.Thread(
            target=lambda: flask_app.run(
                host="127.0.0.1", port=args.server_port, debug=False),
            daemon=True,
        )
        server_thread.start()
        print(f"Flask API server started on port {args.server_port}")
    except ImportError:
        print("Warning: Flask not installed, skipping API server.")

    # Launch GUI (blocks until window closed)
    from llm_buddy.qt.app import main as qt_main
    qt_main()


def _find_module_path(module_name):
    """Find the file path of a Python module."""
    import importlib
    mod = importlib.import_module(module_name)
    return mod.__file__


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="llm-buddy",
        description="LLM Buddy - Universal prompt recording & management",
    )
    subparsers = parser.add_subparsers(dest="command")

    # gui
    sub_gui = subparsers.add_parser("gui", help="Launch the GUI")
    sub_gui.set_defaults(func=_cmd_gui)

    # proxy
    sub_proxy = subparsers.add_parser(
        "proxy", help="Start the proxy recorder")
    sub_proxy.add_argument(
        "--port", type=int, default=8080,
        help="Port for the proxy (default: 8080)")
    sub_proxy.set_defaults(func=_cmd_proxy)

    # server
    sub_server = subparsers.add_parser(
        "server", help="Start the Flask API server")
    sub_server.add_argument(
        "--port", type=int, default=5000,
        help="Port for the server (default: 5000)")
    sub_server.add_argument(
        "--debug", action="store_true",
        help="Run in debug mode")
    sub_server.set_defaults(func=_cmd_server)

    # mcp
    sub_mcp = subparsers.add_parser(
        "mcp", help="Start the MCP recorder for Claude Desktop")
    sub_mcp.set_defaults(func=_cmd_mcp)

    # configure
    sub_configure = subparsers.add_parser(
        "configure", help="Configure Claude Desktop MCP integration")
    sub_configure.set_defaults(func=_cmd_configure)

    # start-all
    sub_all = subparsers.add_parser(
        "start-all", help="Start background services + GUI")
    sub_all.add_argument(
        "--server-port", type=int, default=5000,
        help="Port for the Flask server (default: 5000)")
    sub_all.set_defaults(func=_cmd_start_all)

    args = parser.parse_args()

    if args.command is None:
        # Default: launch GUI
        _cmd_gui(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\paths.py

"""Centralized path resolution for LLM Buddy.

Handles both development (editable install) and frozen (PyInstaller) modes.
All modules should use these functions instead of os.getcwd() for data paths.
"""

import os
import sys


def get_app_dir() -> str:
    """Return the application root directory.

    - Frozen (PyInstaller --onedir): directory containing the .exe
    - Development: current working directory
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


def get_data_dir() -> str:
    """Return the data directory, creating it if needed."""
    data_dir = os.path.join(get_app_dir(), "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_logs_dir() -> str:
    """Return the logs directory, creating it if needed."""
    logs_dir = os.path.join(get_app_dir(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def get_backup_dir() -> str:
    """Return the backup output directory, creating it if needed."""
    backup_dir = os.path.join(get_app_dir(), "backup")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def get_extension_dir() -> str:
    """Return the path to the browser extension folder."""
    return os.path.join(get_app_dir(), "extension")


def get_bundle_dir() -> str:
    """Return the directory where bundled resources are located.

    - Frozen: sys._MEIPASS (PyInstaller extraction dir)
    - Development: current working directory
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.getcwd()


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\__init__.py

"""
LLM Buddy - Universal prompt recording and management system for LLM services.

Captures, organizes, and analyzes prompts from ChatGPT, Claude, Gemini,
Perplexity, and other LLM services.
"""

__version__ = "3.1.0"
__author__ = "Anthony Vigil"


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\__main__.py

"""Allow running as `python -m llm_buddy`."""

from llm_buddy.cli import main

if __name__ == "__main__":
    main()


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\core\backup.py

"""
Auto-backup configuration and file change monitoring for LLM Buddy.
"""

import fnmatch
import hashlib
import logging
import os
from datetime import datetime, timedelta

from watchdog.events import FileSystemEventHandler

from llm_buddy.core.tokens import count_tokens_in_file

logger = logging.getLogger(__name__)


class AutoBackupConfig:
    """Configuration class for auto-backup settings."""

    def __init__(self):
        self.enabled = False
        self.monitor_folders = []
        self.monitor_files = []
        self.ignored_patterns = ["*.tmp", "*.bak", "*~"]
        self.min_token_change = 50
        self.cooldown_minutes = 5
        self.max_backups = 10
        self.notification_enabled = True
        self.last_backup_time = None
        self.file_hashes = {}  # {path: (hash, token_count)}

    def to_dict(self):
        """Convert configuration to dictionary for saving."""
        return {
            "enabled": self.enabled,
            "monitor_folders": self.monitor_folders,
            "monitor_files": self.monitor_files,
            "ignored_patterns": self.ignored_patterns,
            "min_token_change": self.min_token_change,
            "cooldown_minutes": self.cooldown_minutes,
            "max_backups": self.max_backups,
            "notification_enabled": self.notification_enabled,
        }

    def from_dict(self, config_dict):
        """Load configuration from dictionary."""
        self.enabled = config_dict.get("enabled", False)
        self.monitor_folders = config_dict.get("monitor_folders", [])
        self.monitor_files = config_dict.get("monitor_files", [])
        self.ignored_patterns = config_dict.get(
            "ignored_patterns", ["*.tmp", "*.bak", "*~"])
        self.min_token_change = config_dict.get("min_token_change", 50)
        self.cooldown_minutes = config_dict.get("cooldown_minutes", 5)
        self.max_backups = config_dict.get("max_backups", 10)
        self.notification_enabled = config_dict.get(
            "notification_enabled", True)


class EnhancedFileChangeHandler(FileSystemEventHandler):
    """Enhanced handler for file system events with prompt awareness.

    Uses callback functions instead of direct GUI references so that
    this class works with any GUI framework (or no GUI at all).

    Parameters
    ----------
    config : AutoBackupConfig
        Backup configuration (ignored patterns, cooldown, etc.).
    log_callback : callable(str), optional
        Called with log messages.
    schedule_callback : callable(int, callable), optional
        Schedules *callable* to run after *int* milliseconds on the
        main/GUI thread.  For tkinter pass ``master.after``; for
        PySide6 pass a ``QTimer.singleShot`` wrapper.
    trigger_backup_callback : callable(list[tuple[str, int]]), optional
        Called with ``(file_path, token_change)`` pairs when a backup
        should be triggered.
    prompt_database : optional
        If provided, changed files are associated with the active prompt.
    """

    def __init__(
        self,
        config,
        *,
        log_callback=None,
        schedule_callback=None,
        trigger_backup_callback=None,
        prompt_database=None,
    ):
        self.config = config
        self._log = log_callback or (lambda msg: None)
        self._schedule = schedule_callback or (lambda ms, fn: fn())
        self._trigger_backup = trigger_backup_callback or (lambda changes: None)
        self._prompt_database = prompt_database
        self.pending_changes = set()
        super().__init__()

    def on_modified(self, event):
        """Called when a file is modified."""
        if event.is_directory:
            return

        if not self._should_monitor_file(event.src_path):
            return

        self.pending_changes.add(event.src_path)
        self._log(f"Change detected in file: {event.src_path}")

        if not getattr(self, '_processing_scheduled', False):
            self._processing_scheduled = True
            self._schedule(1000, self._process_changes)

    def _should_monitor_file(self, file_path):
        """Check if the file should be monitored based on config."""
        if file_path in self.config.monitor_files:
            return True
        for folder in self.config.monitor_folders:
            if file_path.startswith(folder):
                for pattern in self.config.ignored_patterns:
                    if fnmatch.fnmatch(os.path.basename(file_path), pattern):
                        return False
                return True
        return False

    def _process_changes(self):
        """Process all pending file changes with prompt awareness."""
        self._processing_scheduled = False

        if not self.pending_changes:
            return

        # Check cooldown period
        if self.config.last_backup_time:
            elapsed = datetime.now() - self.config.last_backup_time
            if elapsed < timedelta(minutes=self.config.cooldown_minutes):
                remaining = (self.config.cooldown_minutes
                             - elapsed.total_seconds() / 60)
                self._log(
                    f"Cooldown period active. Next auto-backup available "
                    f"in {remaining:.1f} minutes")
                return

        # Associate changed files with active prompt
        if (self._prompt_database
                and self._prompt_database.active_prompt):
            for file_path in self.pending_changes:
                try:
                    current_tokens = count_tokens_in_file(file_path)
                    self._prompt_database.associate_file_with_active_prompt(
                        file_path, current_tokens)
                except Exception as e:
                    self._log(
                        f"Error processing prompt association "
                        f"for {file_path}: {e}")

        significant_changes = self._check_for_significant_changes()

        if significant_changes:
            self._trigger_backup(significant_changes)

        self.pending_changes.clear()

    def _check_for_significant_changes(self):
        """Check if changes are significant enough to trigger a backup."""
        significant_changes = []

        for file_path in self.pending_changes:
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                current_hash = hashlib.md5(content).hexdigest()
                current_tokens = count_tokens_in_file(file_path)

                if file_path in self.config.file_hashes:
                    prev_hash, prev_tokens = self.config.file_hashes[file_path]
                    if current_hash != prev_hash:
                        token_change = abs(current_tokens - prev_tokens)
                        if token_change >= self.config.min_token_change:
                            self._log(
                                f"Significant change detected in "
                                f"{file_path}: {token_change} tokens changed")
                            significant_changes.append(
                                (file_path, token_change))
                            # ONLY update the baseline if a backup is triggered
                            self.config.file_hashes[file_path] = (current_hash, current_tokens)
                else:
                    significant_changes.append((file_path, current_tokens))
                    self.config.file_hashes[file_path] = (current_hash, current_tokens)

                self.config.file_hashes[file_path] = (
                    current_hash, current_tokens)
            except Exception as e:
                self._log(
                    f"Error processing change for {file_path}: {e}")

        return significant_changes


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\core\database.py

"""
Unified SQLite Database for LLM Buddy.

All persistent research data lives in one file (llm_buddy.db):
  prompts, file_associations, eadr_notes, sessions,
  conversation_trees, branches, fork_points, schema_version

On first launch a one-shot migration reads any pre-existing
prompts.db / JSON files and imports their data, then renames them
to *.migrated so they are never re-processed.

JSON is no longer written on every mutation.  Use export_json(path)
for an on-demand snapshot.
"""

import json
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from llm_buddy.paths import get_data_dir

_SCHEMA_VERSION = 2


def _default_db_path() -> str:
    return os.path.join(get_data_dir(), "llm_buddy.db")



class PromptRecord:
    """Represents a single prompt used with an LLM."""

    def __init__(self, prompt_text: str = "", llm_used: str = "Unknown",
                 description: str = ""):
        self.id: str = str(uuid.uuid4())
        self.timestamp: datetime = datetime.now()
        self.prompt_text: str = prompt_text
        self.llm_used: str = llm_used
        self.description: str = description
        self.associated_files: List[str] = []
        self.file_changes: Dict[str, int] = {}
        self.retroactive_notes: Dict[str, str] = {}
        self.response_text: str = ""
        self.source: str = "Unknown"
        self.model_name: Optional[str] = None
        self.url: Optional[str] = None
        self.conversation_id: Optional[str] = None
        self.metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "prompt_text": self.prompt_text,
            "llm_used": self.llm_used,
            "model": self.llm_used,  # backward compat alias
            "description": self.description,
            "associated_files": self.associated_files,
            "files": self.associated_files,  # backward compat alias
            "file_changes": self.file_changes,
            "retroactive_notes": self.retroactive_notes,
            "source": self.source,
            "response_text": self.response_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptRecord":
        """Create PromptRecord from dictionary (JSON or SQLite row)."""
        record = cls()
        record.id = data.get("id", str(uuid.uuid4()))
        record.timestamp = _parse_timestamp(data.get("timestamp", ""))
        record.prompt_text = data.get("prompt_text") or ""
        record.llm_used = (data.get("llm_used") or data.get("model")
                           or data.get("llm_name", "Unknown"))
        record.description = data.get("description") or ""
        record.associated_files = (data.get("associated_files")
                                   or data.get("files") or [])
        record.file_changes = data.get("file_changes") or {}
        record.retroactive_notes = data.get("retroactive_notes") or {}
        record.response_text = data.get("response_text") or ""
        record.source = data.get("source") or "Unknown"
        record.model_name = data.get("model_name")
        record.url = data.get("url")
        record.conversation_id = data.get("conversation_id")
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            try:
                record.metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                record.metadata = None
        else:
            record.metadata = metadata
        return record


@dataclass
class EadrNote:
    id: int
    timestamp: str
    project: str
    note: str


def _parse_timestamp(timestamp_str: str) -> datetime:
    """Parse a timestamp string with multiple format fallbacks."""
    if not timestamp_str:
        return datetime.now()
    try:
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    logger.warning("Could not parse timestamp: %s", timestamp_str)
    return datetime.now()



def _create_tables(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist."""
    conn.executescript("""
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;

        CREATE TABLE IF NOT EXISTS prompts (
            id              TEXT PRIMARY KEY,
            timestamp       TEXT NOT NULL,
            source          TEXT NOT NULL DEFAULT 'Unknown',
            llm_name        TEXT NOT NULL DEFAULT 'Unknown',
            model_name      TEXT,
            prompt_text     TEXT NOT NULL DEFAULT '',
            response_text   TEXT DEFAULT '',
            description     TEXT DEFAULT '',
            url             TEXT,
            conversation_id TEXT,
            metadata        TEXT
        );

        CREATE TABLE IF NOT EXISTS file_associations (
            prompt_id    TEXT,
            file_path    TEXT,
            token_change INTEGER DEFAULT 0,
            PRIMARY KEY (prompt_id, file_path),
            FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS eadr_notes (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT    NOT NULL,
            project   TEXT    NOT NULL DEFAULT 'Origin',
            note      TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id             TEXT PRIMARY KEY,
            name           TEXT NOT NULL,
            project        TEXT,
            status         TEXT NOT NULL DEFAULT 'active',
            start_time     TEXT,
            end_time       TEXT,
            start_snapshot TEXT,
            end_snapshot   TEXT,
            summary        TEXT,
            notes          TEXT,
            paused_elapsed REAL DEFAULT 0,
            paused_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS conversation_trees (
            id                     TEXT PRIMARY KEY,
            name                   TEXT,
            description            TEXT,
            status                 TEXT DEFAULT 'active',
            created_at             TEXT,
            updated_at             TEXT,
            tags                   TEXT,
            source_conversation_id TEXT,
            checked_out_branch_id  TEXT,
            layout_positions       TEXT
        );

        CREATE TABLE IF NOT EXISTS branches (
            id               TEXT PRIMARY KEY,
            tree_id          TEXT NOT NULL
                             REFERENCES conversation_trees(id) ON DELETE CASCADE,
            name             TEXT,
            strategy         TEXT,
            status           TEXT DEFAULT 'active',
            prompt_ids       TEXT,
            parent_branch_id TEXT,
            fork_point_id    TEXT,
            notes            TEXT,
            outcome          TEXT,
            merge_insights   TEXT,
            session_id       TEXT,
            created_at       TEXT,
            updated_at       TEXT,
            hidden           INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS fork_points (
            id               TEXT PRIMARY KEY,
            tree_id          TEXT NOT NULL
                             REFERENCES conversation_trees(id) ON DELETE CASCADE,
            parent_branch_id TEXT,
            child_branch_id  TEXT,
            prompt_id        TEXT,
            fork_index       INTEGER,
            trigger          TEXT,
            reason           TEXT,
            context_summary  TEXT,
            key_artifacts    TEXT,
            timestamp        TEXT
        );

        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );
    """)
    # Seed schema version if empty
    cur = conn.execute("SELECT COUNT(*) FROM schema_version")
    if cur.fetchone()[0] == 0:
        conn.execute("INSERT INTO schema_version VALUES (?)",
                     (_SCHEMA_VERSION,))

    # Add response_text column to existing databases that predate it
    try:
        conn.execute(
            "ALTER TABLE prompts ADD COLUMN response_text TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.commit()



def _run_migration(db_path: str) -> None:
    """Import old file-based data into the unified database.

    Runs only once: skipped if ``llm_buddy.db`` already exists or if
    no old files are present.  On success old files are renamed to
    ``*.migrated`` so they are never re-processed.  If the migration
    fails the partially-created db is deleted and old files remain
    intact.
    """
    data_dir = os.path.dirname(db_path) or "."
    old_sqlite = os.path.join(data_dir, "prompts.db")
    old_json = os.path.join(data_dir, "prompts.json")
    eadr_json = os.path.join(data_dir, "eadr_notes.json")
    sessions_json = os.path.join(data_dir, "sessions.json")
    trees_json = os.path.join(data_dir, "conversation_trees.json")

    old_files = [f for f in [old_sqlite, old_json, eadr_json,
                              sessions_json, trees_json]
                 if os.path.exists(f)]
    if not old_files:
        return
    if os.path.exists(db_path):
        return  # already migrated

    logger.info("One-shot migration → %s", db_path)
    try:
        _do_migrate(db_path, old_sqlite, old_json, eadr_json,
                    sessions_json, trees_json)
        for fp in old_files:
            try:
                os.rename(fp, fp + ".migrated")
            except Exception as e:
                logger.warning("Could not rename %s: %s", fp, e)
        logger.info("Migration complete.")
    except Exception as e:
        logger.error("Migration failed: %s", e, exc_info=True)
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


def _do_migrate(db_path: str, old_sqlite: str, old_json: str,
                eadr_json: str, sessions_json: str,
                trees_json: str) -> None:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    _create_tables(conn)
    c = conn.cursor()

    try:
        if os.path.exists(old_sqlite):
            try:
                src = sqlite3.connect(old_sqlite)
                src.row_factory = sqlite3.Row
                rows = src.execute("SELECT * FROM prompts").fetchall()
                assoc = src.execute(
                    "SELECT * FROM file_associations").fetchall()
                src.close()
                for row in rows:
                    d = dict(row)
                    c.execute("""
                        INSERT OR IGNORE INTO prompts
                        (id, timestamp, source, llm_name, model_name,
                         prompt_text, response_text, description, url,
                         conversation_id, metadata)
                        VALUES (:id, :timestamp, :source, :llm_name,
                                :model_name, :prompt_text, :response_text,
                                :description, :url, :conversation_id,
                                :metadata)
                    """, {k: d.get(k) for k in (
                        "id", "timestamp", "source", "llm_name",
                        "model_name", "prompt_text", "response_text",
                        "description", "url", "conversation_id", "metadata")})
                for row in assoc:
                    d = dict(row)
                    c.execute("""
                        INSERT OR IGNORE INTO file_associations
                        (prompt_id, file_path, token_change)
                        VALUES (?, ?, ?)
                    """, (d["prompt_id"], d["file_path"],
                          d.get("token_change", 0)))
                logger.info("Migrated %d prompts from prompts.db",
                            len(rows))
            except Exception as e:
                logger.warning("prompts.db migration error: %s", e)

        if os.path.exists(old_json):
            try:
                with open(old_json, "r", encoding="utf-8") as f:
                    items = json.load(f)
                count = 0
                for item in items:
                    pid = item.get("id")
                    if not pid:
                        continue
                    c.execute("SELECT 1 FROM prompts WHERE id = ?", (pid,))
                    if c.fetchone():
                        continue
                    c.execute("""
                        INSERT OR IGNORE INTO prompts
                        (id, timestamp, source, llm_name, model_name,
                         prompt_text, response_text, description, url,
                         conversation_id, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (pid,
                          item.get("timestamp", datetime.now().isoformat()),
                          item.get("source", "Unknown"),
                          item.get("llm_used") or item.get("model",
                                                            "Unknown"),
                          item.get("model_name"),
                          item.get("prompt_text", ""),
                          item.get("response_text", ""),
                          item.get("description", ""),
                          item.get("url"),
                          item.get("conversation_id"),
                          json.dumps(item["metadata"])
                          if item.get("metadata") else None))
                    count += 1
                logger.info("Migrated %d unique prompts from prompts.json",
                            count)
            except Exception as e:
                logger.warning("prompts.json migration error: %s", e)

        if os.path.exists(eadr_json):
            try:
                with open(eadr_json, "r", encoding="utf-8") as f:
                    notes = json.load(f)
                for n in notes:
                    c.execute("""
                        INSERT INTO eadr_notes (timestamp, project, note)
                        VALUES (?, ?, ?)
                    """, (n.get("timestamp",
                                datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S")),
                          n.get("project", "Origin"),
                          n.get("note", "")))
                logger.info("Migrated %d eADR notes", len(notes))
            except Exception as e:
                logger.warning("eadr_notes.json migration error: %s", e)

        if os.path.exists(sessions_json):
            try:
                with open(sessions_json, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
                for s in sessions:
                    c.execute("""
                        INSERT OR IGNORE INTO sessions
                        (id, name, project, status, start_time, end_time,
                         start_snapshot, end_snapshot, summary, notes,
                         paused_elapsed, paused_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (s.get("id", str(uuid.uuid4())),
                          s.get("name", ""),
                          s.get("project", ""),
                          s.get("status", "completed"),
                          s.get("start_time"),
                          s.get("end_time"),
                          json.dumps(s["start_snapshot"])
                          if s.get("start_snapshot") else None,
                          json.dumps(s["end_snapshot"])
                          if s.get("end_snapshot") else None,
                          json.dumps(s["summary"])
                          if s.get("summary") else None,
                          s.get("notes", ""),
                          s.get("paused_elapsed", 0.0),
                          s.get("paused_at")))
                logger.info("Migrated %d sessions", len(sessions))
            except Exception as e:
                logger.warning("sessions.json migration error: %s", e)

        if os.path.exists(trees_json):
            try:
                with open(trees_json, "r", encoding="utf-8") as f:
                    trees = json.load(f)
                for t in trees:
                    tid = t.get("id", str(uuid.uuid4()))
                    c.execute("""
                        INSERT OR IGNORE INTO conversation_trees
                        (id, name, description, status, created_at,
                         updated_at, tags, source_conversation_id,
                         checked_out_branch_id, layout_positions)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (tid,
                          t.get("name", ""),
                          t.get("description", ""),
                          t.get("status", "active"),
                          t.get("created_at"),
                          t.get("updated_at"),
                          json.dumps(t.get("tags", [])),
                          t.get("source_conversation_id"),
                          t.get("checked_out_branch_id"),
                          json.dumps(t.get("layout_positions", {}))))
                    for b in t.get("branches", []):
                        c.execute("""
                            INSERT OR IGNORE INTO branches
                            (id, tree_id, name, strategy, status,
                             prompt_ids, parent_branch_id, fork_point_id,
                             notes, outcome, merge_insights, session_id,
                             created_at, updated_at, hidden)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                    ?, ?, ?, ?)
                        """, (b.get("id", str(uuid.uuid4())),
                              tid,
                              b.get("name", "main"),
                              b.get("strategy", ""),
                              b.get("status", "active"),
                              json.dumps(b.get("prompt_ids", [])),
                              b.get("parent_branch_id"),
                              b.get("fork_point_id"),
                              b.get("notes", ""),
                              b.get("outcome", ""),
                              b.get("merge_insights", ""),
                              b.get("session_id"),
                              b.get("created_at"),
                              b.get("updated_at"),
                              1 if b.get("hidden") else 0))
                    for fp in t.get("fork_points", []):
                        c.execute("""
                            INSERT OR IGNORE INTO fork_points
                            (id, tree_id, parent_branch_id,
                             child_branch_id, prompt_id, fork_index,
                             trigger, reason, context_summary,
                             key_artifacts, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (fp.get("id", str(uuid.uuid4())),
                              tid,
                              fp.get("parent_branch_id"),
                              fp.get("child_branch_id"),
                              fp.get("prompt_id"),
                              fp.get("fork_index", 0),
                              fp.get("trigger", "other"),
                              fp.get("reason", ""),
                              fp.get("context_summary", ""),
                              fp.get("key_artifacts", ""),
                              fp.get("timestamp")))
                logger.info("Migrated %d conversation trees", len(trees))
            except Exception as e:
                logger.warning(
                    "conversation_trees.json migration error: %s", e)

        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.close()



class PromptDatabase:
    """
    Unified database for storing all LLM Buddy research data.

    Supports two usage modes:
    - **Recorder mode** (proxy, MCP, API): call add_prompt() directly.
    - **GUI mode**: call load() to populate self.prompts, then use the
      in-memory list for display.  Mutations sync back to SQLite.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.sqlite_path = db_path or _default_db_path()
        self.prompts: List[PromptRecord] = []
        self.active_prompt: Optional[PromptRecord] = None
        _run_migration(self.sqlite_path)
        self._initialize_db()

    def _initialize_db(self) -> None:
        db_dir = os.path.dirname(self.sqlite_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path)
        _create_tables(conn)
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def add_prompt(self, prompt_text: str = "",
                   llm_name: str = "Unknown",
                   source: str = "Unknown",
                   model_name: Optional[str] = None,
                   description: Optional[str] = None,
                   url: Optional[str] = None,
                   conversation_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   associated_files: Optional[List[str]] = None,
                   prompt_record: Optional[PromptRecord] = None,
                   ) -> str:
        """Add a new prompt; returns the prompt ID."""
        if prompt_record is not None:
            rec = prompt_record
        else:
            rec = PromptRecord(prompt_text, llm_name, description or "")
            rec.source = source
            rec.model_name = model_name
            rec.url = url
            rec.conversation_id = conversation_id
            rec.metadata = metadata
            if associated_files:
                rec.associated_files = list(associated_files)

        self._insert_sqlite(rec)
        self.prompts.append(rec)
        self.active_prompt = rec
        return rec.id

    def get_prompt(self, prompt_id: str) -> Optional[PromptRecord]:
        for p in self.prompts:
            if p.id == prompt_id:
                return p
        return self._get_from_sqlite(prompt_id)

    def get_recent_prompts(self, hours: int = 24) -> List[PromptRecord]:
        cutoff = datetime.now() - timedelta(hours=hours)
        return [p for p in self.prompts if p.timestamp > cutoff]

    def get_prompts_for_file(self, file_path: str) -> List[PromptRecord]:
        return [p for p in self.prompts
                if file_path in p.associated_files]

    def associate_file_with_active_prompt(self, file_path: str,
                                          token_change: int = 0) -> bool:
        if (self.active_prompt
                and file_path not in self.active_prompt.associated_files):
            self.active_prompt.associated_files.append(file_path)
            self.active_prompt.file_changes[file_path] = token_change
            self.save()
            return True
        return False

    def associate_files_with_prompt(self, prompt_id: str,
                                    file_paths: List[str],
                                    token_change: int = 0) -> bool:
        try:
            conn = self._connect()
            for fp in file_paths:
                conn.execute("""
                    INSERT OR REPLACE INTO file_associations
                    (prompt_id, file_path, token_change) VALUES (?, ?, ?)
                """, (prompt_id, fp, token_change))
            conn.commit()
            conn.close()
            rec = self.get_prompt(prompt_id)
            if rec:
                for fp in file_paths:
                    if fp not in rec.associated_files:
                        rec.associated_files.append(fp)
                        rec.file_changes[fp] = token_change
            return True
        except Exception as e:
            logger.error("Error associating files: %s", e)
            return False

    def update_response(self, prompt_id: str,
                        response_text: str) -> bool:
        try:
            conn = self._connect()
            conn.execute(
                "UPDATE prompts SET response_text = ? WHERE id = ?",
                (response_text, prompt_id))
            conn.commit()
            conn.close()
            for p in self.prompts:
                if p.id == prompt_id:
                    p.response_text = response_text
                    break
            return True
        except Exception as e:
            logger.error("Error updating response: %s", e)
            return False

    def update_conversation_id(self, prompt_id: str,
                               conversation_id: str) -> bool:
        """Update the conversation_id for a previously recorded prompt."""
        try:
            conn = self._connect()
            conn.execute(
                "UPDATE prompts SET conversation_id = ? WHERE id = ?",
                (conversation_id, prompt_id))
            conn.commit()
            conn.close()
            for p in self.prompts:
                if p.id == prompt_id:
                    p.conversation_id = conversation_id
                    break
            return True
        except Exception as e:
            logger.error("Error updating conversation_id: %s", e)
            return False

    def delete_prompt(self, prompt_id: str) -> bool:
        try:
            conn = self._connect()
            conn.execute("DELETE FROM file_associations WHERE prompt_id = ?",
                         (prompt_id,))
            conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
            conn.commit()
            conn.close()
            self.prompts = [p for p in self.prompts if p.id != prompt_id]
            return True
        except Exception as e:
            logger.error("Error deleting prompt: %s", e)
            return False

    def clear_active_prompt(self) -> None:
        self.active_prompt = None

    def search_prompts(self, search_text: Optional[str] = None,
                       llm_name: Optional[str] = None,
                       source: Optional[str] = None,
                       file_path: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        try:
            conn = self._connect()
            query = "SELECT DISTINCT p.* FROM prompts p"
            params: List[Any] = []
            where: List[str] = []

            if file_path:
                query += " LEFT JOIN file_associations fa ON p.id = fa.prompt_id"
                where.append("fa.file_path LIKE ?")
                params.append(f"%{file_path}%")
            if search_text:
                where.append(
                    "(p.prompt_text LIKE ? OR p.description LIKE ?)")
                params.extend([f"%{search_text}%", f"%{search_text}%"])
            if llm_name:
                where.append("p.llm_name = ?")
                params.append(llm_name)
            if source:
                where.append("p.source = ?")
                params.append(source)
            if start_date:
                where.append("p.timestamp >= ?")
                params.append(start_date)
            if end_date:
                where.append("p.timestamp <= ?")
                params.append(end_date)

            if where:
                query += " WHERE " + " AND ".join(where)
            query += " ORDER BY p.timestamp DESC LIMIT ?"
            params.append(limit)

            results = []
            for row in conn.execute(query, params).fetchall():
                d = dict(row)
                if d.get("metadata"):
                    try:
                        d["metadata"] = json.loads(d["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                file_rows = conn.execute(
                    "SELECT file_path, token_change FROM file_associations "
                    "WHERE prompt_id = ?", (d["id"],)).fetchall()
                d["associated_files"] = [r["file_path"] for r in file_rows]
                d["file_changes"] = {r["file_path"]: r["token_change"]
                                     for r in file_rows}
                results.append(d)
            conn.close()
            return results
        except Exception as e:
            logger.error("Error searching prompts: %s", e)
            return []

    def get_prompts_count(self) -> int:
        try:
            conn = self._connect()
            count = conn.execute(
                "SELECT COUNT(*) FROM prompts").fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error("Error getting prompts count: %s", e)
            return len(self.prompts)

    def load(self) -> bool:
        """Load prompts into memory from SQLite."""
        loaded: List[PromptRecord] = []
        try:
            conn = self._connect()
            for row in conn.execute(
                    "SELECT * FROM prompts ORDER BY timestamp").fetchall():
                d = dict(row)
                d["llm_used"] = d.pop("llm_name", "Unknown")
                file_rows = conn.execute(
                    "SELECT file_path, token_change FROM file_associations "
                    "WHERE prompt_id = ?", (d["id"],)).fetchall()
                d["associated_files"] = [r["file_path"] for r in file_rows]
                d["file_changes"] = {r["file_path"]: r["token_change"]
                                     for r in file_rows}
                loaded.append(PromptRecord.from_dict(d))
            conn.close()
        except Exception as e:
            logger.error("Error loading from SQLite: %s", e)

        self.prompts = loaded
        logger.info("Loaded %d prompts", len(self.prompts))
        return len(self.prompts) > 0

    def save(self) -> bool:
        """Persist all in-memory prompts to SQLite."""
        try:
            conn = self._connect()
            for rec in self.prompts:
                conn.execute("""
                    INSERT OR REPLACE INTO prompts
                    (id, timestamp, source, llm_name, model_name,
                     prompt_text, response_text, description, url,
                     conversation_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (rec.id, rec.timestamp.isoformat(), rec.source,
                      rec.llm_used, rec.model_name, rec.prompt_text,
                      rec.response_text, rec.description, rec.url,
                      rec.conversation_id,
                      json.dumps(rec.metadata) if rec.metadata else None))
                for fp in rec.associated_files:
                    conn.execute("""
                        INSERT OR REPLACE INTO file_associations
                        (prompt_id, file_path, token_change) VALUES (?, ?, ?)
                    """, (rec.id, fp, rec.file_changes.get(fp, 0)))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error saving prompt database: %s", e)
            return False

    def export_json(self, path: str) -> bool:
        """Export all prompts to a JSON file (on-demand snapshot)."""
        try:
            data = [rec.to_dict() for rec in self.prompts]
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logger.error("Error exporting JSON: %s", e)
            return False

    def import_from_json(self, json_path: Optional[str] = None) -> int:
        """Import prompts from a JSON file into SQLite."""
        if not json_path or not os.path.exists(json_path):
            return 0
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = 0
            for item in data:
                pid = item.get("id")
                if pid and not any(p.id == pid for p in self.prompts):
                    rec = PromptRecord.from_dict(item)
                    self._insert_sqlite(rec)
                    self.prompts.append(rec)
                    count += 1
            return count
        except Exception as e:
            logger.error("Error importing from JSON: %s", e)
            return 0

    def _insert_sqlite(self, rec: PromptRecord) -> None:
        try:
            conn = self._connect()
            conn.execute("""
                INSERT OR REPLACE INTO prompts
                (id, timestamp, source, llm_name, model_name,
                 prompt_text, response_text, description, url,
                 conversation_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rec.id, rec.timestamp.isoformat(), rec.source,
                  rec.llm_used, rec.model_name, rec.prompt_text,
                  rec.response_text, rec.description, rec.url,
                  rec.conversation_id,
                  json.dumps(rec.metadata) if rec.metadata else None))
            for fp in rec.associated_files:
                conn.execute("""
                    INSERT OR REPLACE INTO file_associations
                    (prompt_id, file_path, token_change) VALUES (?, ?, ?)
                """, (rec.id, fp, rec.file_changes.get(fp, 0)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Error inserting to SQLite: %s", e)

    def _get_from_sqlite(self, prompt_id: str) -> Optional[PromptRecord]:
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT * FROM prompts WHERE id = ?",
                (prompt_id,)).fetchone()
            if not row:
                conn.close()
                return None
            d = dict(row)
            d["llm_used"] = d.pop("llm_name", "Unknown")
            file_rows = conn.execute(
                "SELECT file_path, token_change FROM file_associations "
                "WHERE prompt_id = ?", (prompt_id,)).fetchall()
            d["associated_files"] = [r["file_path"] for r in file_rows]
            d["file_changes"] = {r["file_path"]: r["token_change"]
                                 for r in file_rows}
            conn.close()
            return PromptRecord.from_dict(d)
        except Exception as e:
            logger.error("Error getting prompt from SQLite: %s", e)
            return None

    def add_eadr_note(self, note: str,
                      project: str = "Origin") -> int:
        """Insert a new eADR note; returns the new row id."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            conn = self._connect()
            cur = conn.execute(
                "INSERT INTO eadr_notes (timestamp, project, note) "
                "VALUES (?, ?, ?)",
                (ts, project, note))
            note_id = cur.lastrowid
            conn.commit()
            conn.close()
            return note_id
        except Exception as e:
            logger.error("Error adding eADR note: %s", e)
            return -1

    def get_eadr_notes(self,
                       project: Optional[str] = None) -> List[EadrNote]:
        """Return all eADR notes, newest first."""
        try:
            conn = self._connect()
            if project:
                rows = conn.execute(
                    "SELECT id, timestamp, project, note FROM eadr_notes "
                    "WHERE project = ? ORDER BY id DESC",
                    (project,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, timestamp, project, note FROM eadr_notes "
                    "ORDER BY id DESC").fetchall()
            conn.close()
            return [EadrNote(id=r["id"], timestamp=r["timestamp"],
                             project=r["project"], note=r["note"])
                    for r in rows]
        except Exception as e:
            logger.error("Error loading eADR notes: %s", e)
            return []

    def delete_eadr_note(self, note_id: int) -> bool:
        """Delete an eADR note by its database ID."""
        try:
            conn = self._connect()
            conn.execute("DELETE FROM eadr_notes WHERE id = ?", (note_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error deleting eADR note: %s", e)
            return False

    def add_session(self, session) -> str:
        """Insert a new ResearchSession; returns its ID."""
        try:
            conn = self._connect()
            d = session.to_dict()
            conn.execute("""
                INSERT OR REPLACE INTO sessions
                (id, name, project, status, start_time, end_time,
                 start_snapshot, end_snapshot, summary, notes,
                 paused_elapsed, paused_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (d["id"], d["name"], d["project"], d["status"],
                  d["start_time"], d["end_time"],
                  json.dumps(d["start_snapshot"])
                  if d.get("start_snapshot") else None,
                  json.dumps(d["end_snapshot"])
                  if d.get("end_snapshot") else None,
                  json.dumps(d["summary"])
                  if d.get("summary") else None,
                  d["notes"], d["paused_elapsed"], d["paused_at"]))
            conn.commit()
            conn.close()
            return d["id"]
        except Exception as e:
            logger.error("Error adding session: %s", e)
            return ""

    def update_session(self, session) -> bool:
        """Upsert a ResearchSession (used for pause/resume/end)."""
        return bool(self.add_session(session))

    def get_sessions(self) -> list:
        """Return all sessions as ResearchSession objects."""
        from llm_buddy.core.sessions import ResearchSession
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY start_time").fetchall()
            conn.close()
            sessions = []
            for row in rows:
                d = dict(row)
                for key in ("start_snapshot", "end_snapshot", "summary"):
                    if d.get(key):
                        try:
                            d[key] = json.loads(d[key])
                        except (json.JSONDecodeError, TypeError):
                            d[key] = None
                sessions.append(ResearchSession.from_dict(d))
            return sessions
        except Exception as e:
            logger.error("Error loading sessions: %s", e)
            return []

    def get_active_session(self):
        """Return the currently active or paused session, or None."""
        for s in self.get_sessions():
            if s.status in ("active", "paused"):
                return s
        return None

    def delete_session(self, session_id: str) -> bool:
        try:
            conn = self._connect()
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error deleting session: %s", e)
            return False

    def save_tree(self, tree) -> bool:
        """Upsert a ConversationTree and all its branches/fork_points."""
        try:
            conn = self._connect()
            d = tree.to_dict()
            tid = d["id"]

            # Upsert tree row
            conn.execute("""
                INSERT OR REPLACE INTO conversation_trees
                (id, name, description, status, created_at, updated_at,
                 tags, source_conversation_id, checked_out_branch_id,
                 layout_positions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (tid, d["name"], d["description"], d["status"],
                  d["created_at"], d["updated_at"],
                  json.dumps(d.get("tags", [])),
                  d.get("source_conversation_id"),
                  d.get("checked_out_branch_id"),
                  json.dumps(d.get("layout_positions", {}))))

            # Replace branches: delete all then re-insert
            conn.execute("DELETE FROM branches WHERE tree_id = ?", (tid,))
            for b in d.get("branches", []):
                conn.execute("""
                    INSERT INTO branches
                    (id, tree_id, name, strategy, status, prompt_ids,
                     parent_branch_id, fork_point_id, notes, outcome,
                     merge_insights, session_id, created_at, updated_at,
                     hidden)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (b["id"], tid, b.get("name", "main"),
                      b.get("strategy", ""), b.get("status", "active"),
                      json.dumps(b.get("prompt_ids", [])),
                      b.get("parent_branch_id"), b.get("fork_point_id"),
                      b.get("notes", ""), b.get("outcome", ""),
                      b.get("merge_insights", ""), b.get("session_id"),
                      b.get("created_at"), b.get("updated_at"),
                      1 if b.get("hidden") else 0))

            # Replace fork_points
            conn.execute("DELETE FROM fork_points WHERE tree_id = ?", (tid,))
            for fp in d.get("fork_points", []):
                conn.execute("""
                    INSERT INTO fork_points
                    (id, tree_id, parent_branch_id, child_branch_id,
                     prompt_id, fork_index, trigger, reason,
                     context_summary, key_artifacts, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (fp["id"], tid, fp.get("parent_branch_id"),
                      fp.get("child_branch_id"), fp.get("prompt_id"),
                      fp.get("fork_index", 0), fp.get("trigger", "other"),
                      fp.get("reason", ""), fp.get("context_summary", ""),
                      fp.get("key_artifacts", ""), fp.get("timestamp")))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error saving tree: %s", e)
            return False

    def load_trees(self) -> list:
        """Return all ConversationTree objects."""
        from llm_buddy.core.forking import ConversationTree
        try:
            conn = self._connect()
            tree_rows = conn.execute(
                "SELECT * FROM conversation_trees").fetchall()
            trees = []
            for trow in tree_rows:
                td = dict(trow)
                for key in ("tags", "layout_positions"):
                    if td.get(key):
                        try:
                            td[key] = json.loads(td[key])
                        except (json.JSONDecodeError, TypeError):
                            td[key] = [] if key == "tags" else {}

                branch_rows = conn.execute(
                    "SELECT * FROM branches WHERE tree_id = ?",
                    (td["id"],)).fetchall()
                td["branches"] = []
                for brow in branch_rows:
                    bd = dict(brow)
                    if bd.get("prompt_ids"):
                        try:
                            bd["prompt_ids"] = json.loads(bd["prompt_ids"])
                        except (json.JSONDecodeError, TypeError):
                            bd["prompt_ids"] = []
                    bd["hidden"] = bool(bd.get("hidden", 0))
                    td["branches"].append(bd)

                fp_rows = conn.execute(
                    "SELECT * FROM fork_points WHERE tree_id = ?",
                    (td["id"],)).fetchall()
                td["fork_points"] = [dict(r) for r in fp_rows]

                trees.append(ConversationTree.from_dict(td))
            conn.close()
            return trees
        except Exception as e:
            logger.error("Error loading trees: %s", e)
            return []

    def delete_tree(self, tree_id: str) -> bool:
        try:
            conn = self._connect()
            conn.execute(
                "DELETE FROM conversation_trees WHERE id = ?", (tree_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error deleting tree: %s", e)
            return False


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\core\eadr.py

"""
eADR (Elaborated Action Design Research) note management.

File I/O has been moved to PromptDatabase.add_eadr_note(),
get_eadr_notes(), and delete_eadr_note() in core/database.py.
This module is kept as a stub so that any remaining imports resolve.
"""


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\core\forking.py

"""
Conversational Forking data model and persistence for LLM Buddy.

Implements the Conversational Forking (CF) method — a non-linear
context engineering approach that treats LLM conversations as
version-controlled, branchable structures rather than immutable
linear sequences.

Improvements over v3.0:
  - Merge workflow support (merge_branch method)
  - Explicit branch checkout tracking (checked_out_branch_id)
  - Soft-delete support (hidden flag on Branch)
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


FORK_TRIGGERS = [
    ("error_cascade", "Error Cascade"),
    ("context_overflow", "Context Overflow"),
    ("exploratory", "Exploratory Branching"),
    ("optimization", "Optimization Opportunity"),
    ("other", "Other"),
]

BRANCH_STRATEGIES = [
    ("", "(none)"),
    ("divergent", "Divergent Exploration"),
    ("convergent", "Convergent Refinement"),
    ("parallel", "Parallel Processing"),
]

BRANCH_STATUSES = [
    ("active", "Active"),
    ("completed", "Completed"),
    ("abandoned", "Abandoned"),
    ("merged", "Merged"),
]

TREE_STATUSES = [
    ("active", "Active"),
    ("completed", "Completed"),
    ("archived", "Archived"),
]


def _parse_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None

def _now_iso() -> str:
    return datetime.now().isoformat()

def _norm_pos(v):
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return (float(v[0]), float(v[1]))
    if isinstance(v, dict) and "x" in v and "y" in v:
        return (float(v["x"]), float(v["y"]))
    return None


@dataclass
class ForkPoint:
    id: str = ""
    parent_branch_id: str = ""
    child_branch_id: str = ""
    prompt_id: str = ""
    fork_index: int = 0
    trigger: str = "other"
    reason: str = ""
    context_summary: str = ""
    key_artifacts: str = ""
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_branch_id": self.parent_branch_id,
            "child_branch_id": self.child_branch_id,
            "prompt_id": self.prompt_id,
            "fork_index": self.fork_index,
            "trigger": self.trigger,
            "reason": self.reason,
            "context_summary": self.context_summary,
            "key_artifacts": self.key_artifacts,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ForkPoint":
        fp = cls()
        fp.id = d.get("id", str(uuid.uuid4()))
        fp.parent_branch_id = d.get("parent_branch_id", "")
        fp.child_branch_id = d.get("child_branch_id", "")
        fp.prompt_id = d.get("prompt_id", "")
        fp.fork_index = d.get("fork_index", 0)
        fp.trigger = d.get("trigger", "other")
        fp.reason = d.get("reason", "")
        fp.context_summary = d.get("context_summary", "")
        fp.key_artifacts = d.get("key_artifacts", "")
        ts = d.get("timestamp")
        fp.timestamp = _parse_dt(ts) if ts else datetime.now()
        return fp

@dataclass
class Branch:
    id: str = ""
    name: str = "main"
    strategy: str = ""
    status: str = "active"
    prompt_ids: List[str] = field(default_factory=list)
    parent_branch_id: Optional[str] = None
    fork_point_id: Optional[str] = None
    notes: str = ""
    outcome: str = ""
    merge_insights: str = ""
    session_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    hidden: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "strategy": self.strategy,
            "status": self.status,
            "prompt_ids": list(self.prompt_ids),
            "parent_branch_id": self.parent_branch_id,
            "fork_point_id": self.fork_point_id,
            "notes": self.notes,
            "outcome": self.outcome,
            "merge_insights": self.merge_insights,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "hidden": self.hidden,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Branch":
        b = cls()
        b.id = d.get("id", str(uuid.uuid4()))
        b.name = d.get("name", "main")
        b.strategy = d.get("strategy", "")
        b.status = d.get("status", "active")
        b.prompt_ids = list(d.get("prompt_ids", []))
        b.parent_branch_id = d.get("parent_branch_id")
        b.fork_point_id = d.get("fork_point_id")
        b.notes = d.get("notes", "")
        b.outcome = d.get("outcome", "")
        b.merge_insights = d.get("merge_insights", "")
        b.session_id = d.get("session_id")
        ca = d.get("created_at")
        b.created_at = _parse_dt(ca) if ca else datetime.now()
        ua = d.get("updated_at")
        b.updated_at = _parse_dt(ua) if ua else datetime.now()
        b.hidden = d.get("hidden", False)
        return b

@dataclass
class ConversationTree:
    id: str = ""
    name: str = ""
    description: str = ""
    status: str = "active"
    branches: List[Branch] = field(default_factory=list)
    fork_points: List[ForkPoint] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    source_conversation_id: Optional[str] = None
    layout_positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    checked_out_branch_id: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if not self.branches:
            root = Branch(name="main")
            self.branches.append(root)
            self.checked_out_branch_id = root.id

    def get_branch(self, branch_id: str) -> Optional[Branch]:
        for b in self.branches:
            if b.id == branch_id:
                return b
        return None

    def get_root_branch(self) -> Optional[Branch]:
        for b in self.branches:
            if b.parent_branch_id is None:
                return b
        return self.branches[0] if self.branches else None

    def get_child_branches(self, branch_id: str) -> List[Branch]:
        return [b for b in self.branches if b.parent_branch_id == branch_id]

    def get_visible_branches(self, show_hidden: bool = False) -> List[Branch]:
        """Return branches filtered by hidden state."""
        if show_hidden:
            return list(self.branches)
        return [b for b in self.branches if not b.hidden]

    def get_fork_point(self, fp_id: str) -> Optional[ForkPoint]:
        for fp in self.fork_points:
            if fp.id == fp_id:
                return fp
        return None

    def get_checked_out_branch(self) -> Optional[Branch]:
        """Return the currently checked-out branch, or fall back to root."""
        if self.checked_out_branch_id:
            b = self.get_branch(self.checked_out_branch_id)
            if b and not b.hidden:
                return b
        return self.get_root_branch()

    def checkout_branch(self, branch_id: str) -> bool:
        """Set the active/checked-out branch for receiving new prompts."""
        branch = self.get_branch(branch_id)
        if branch is None or branch.hidden:
            return False
        self.checked_out_branch_id = branch_id
        self.updated_at = datetime.now()
        return True

    def add_branch(
        self, name: str, parent_branch_id: str, fork_index: int, trigger: str = "other",
        reason: str = "", context_summary: str = "", key_artifacts: str = "",
        strategy: str = "", session_id: Optional[str] = None,
    ) -> Optional[Branch]:
        parent = self.get_branch(parent_branch_id)
        if parent is None:
            return None

        prompt_at_fork = ""
        inherited_prompts: List[str] = []
        if parent.prompt_ids and 0 <= fork_index < len(parent.prompt_ids):
            prompt_at_fork = parent.prompt_ids[fork_index]
            inherited_prompts = list(parent.prompt_ids[: fork_index + 1])
        elif parent.prompt_ids:
            fork_index = len(parent.prompt_ids) - 1
            prompt_at_fork = parent.prompt_ids[fork_index]
            inherited_prompts = list(parent.prompt_ids)

        new_branch = Branch(
            name=name, strategy=strategy, prompt_ids=inherited_prompts,
            parent_branch_id=parent_branch_id, session_id=session_id,
        )

        fork_point = ForkPoint(
            parent_branch_id=parent_branch_id, child_branch_id=new_branch.id,
            prompt_id=prompt_at_fork, fork_index=fork_index, trigger=trigger,
            reason=reason, context_summary=context_summary, key_artifacts=key_artifacts,
        )
        new_branch.fork_point_id = fork_point.id

        self.branches.append(new_branch)
        self.fork_points.append(fork_point)
        self.updated_at = datetime.now()
        return new_branch

    def merge_branch(
        self, source_branch_id: str, target_branch_id: str,
        merge_insights: str = "", include_unique_prompts: bool = True,
    ) -> bool:
        """Merge *source* into *target*.

        - Copies unique prompt IDs from source into target (if requested).
        - Sets source status to 'merged' and records insights.
        - Returns True on success.
        """
        source = self.get_branch(source_branch_id)
        target = self.get_branch(target_branch_id)
        if source is None or target is None:
            return False
        if source.id == target.id:
            return False

        if include_unique_prompts:
            existing = set(target.prompt_ids)
            for pid in source.prompt_ids:
                if pid not in existing:
                    target.prompt_ids.append(pid)
                    existing.add(pid)

        source.status = "merged"
        source.merge_insights = merge_insights
        source.updated_at = datetime.now()
        target.updated_at = datetime.now()
        self.updated_at = datetime.now()
        return True

    def remove_branch(self, branch_id: str) -> bool:
        branch = self.get_branch(branch_id)
        if branch is None or branch.parent_branch_id is None:
            return False

        children = self.get_child_branches(branch_id)
        for child in children:
            self.remove_branch(child.id)

        if branch.fork_point_id:
            self.fork_points = [fp for fp in self.fork_points if fp.id != branch.fork_point_id]

        self.branches = [b for b in self.branches if b.id != branch_id]

        # Fix checkout if we just removed the checked-out branch
        if self.checked_out_branch_id == branch_id:
            root = self.get_root_branch()
            self.checked_out_branch_id = root.id if root else None

        self.updated_at = datetime.now()
        return True

    def soft_delete_branch(self, branch_id: str) -> bool:
        """Hide a branch and its descendants without destroying data."""
        branch = self.get_branch(branch_id)
        if branch is None or branch.parent_branch_id is None:
            return False  # Cannot soft-delete root

        def _hide_recursive(bid: str):
            b = self.get_branch(bid)
            if b:
                b.hidden = True
                b.updated_at = datetime.now()
            for child in self.get_child_branches(bid):
                _hide_recursive(child.id)

        _hide_recursive(branch_id)

        if self.checked_out_branch_id == branch_id:
            root = self.get_root_branch()
            self.checked_out_branch_id = root.id if root else None

        self.updated_at = datetime.now()
        return True

    def restore_branch(self, branch_id: str) -> bool:
        """Un-hide a previously soft-deleted branch and its descendants."""
        branch = self.get_branch(branch_id)
        if branch is None:
            return False

        def _restore_recursive(bid: str):
            b = self.get_branch(bid)
            if b:
                b.hidden = False
                b.updated_at = datetime.now()
            for child in self.get_child_branches(bid):
                _restore_recursive(child.id)

        _restore_recursive(branch_id)
        self.updated_at = datetime.now()
        return True

    def move_prompt(self, prompt_id: str, from_branch_id: str, to_branch_id: str) -> bool:
        """Move a prompt from one branch to another."""
        src = self.get_branch(from_branch_id)
        dst = self.get_branch(to_branch_id)
        if not src or not dst:
            return False
        if prompt_id not in src.prompt_ids:
            return False
        src.prompt_ids.remove(prompt_id)
        if prompt_id not in dst.prompt_ids:
            dst.prompt_ids.append(prompt_id)
        src.updated_at = datetime.now()
        dst.updated_at = datetime.now()
        self.updated_at = datetime.now()
        return True

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "branches": [b.to_dict() for b in self.branches],
            "fork_points": [fp.to_dict() for fp in self.fork_points],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tags": list(self.tags),
            "source_conversation_id": self.source_conversation_id,
            "checked_out_branch_id": self.checked_out_branch_id,
        }
        d["layout_positions"] = {
            bid: [pos[0], pos[1]] for bid, pos in (self.layout_positions or {}).items()
        }
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConversationTree":
        tree = cls.__new__(cls)
        tree.id = d.get("id", str(uuid.uuid4()))
        tree.name = d.get("name", "")
        tree.description = d.get("description", "")
        tree.status = d.get("status", "active")
        tree.branches = [Branch.from_dict(b) for b in d.get("branches", [])]
        tree.fork_points = [ForkPoint.from_dict(fp) for fp in d.get("fork_points", [])]
        ca = d.get("created_at")
        tree.created_at = _parse_dt(ca) if ca else datetime.now()
        ua = d.get("updated_at")
        tree.updated_at = _parse_dt(ua) if ua else datetime.now()
        tree.tags = list(d.get("tags", []))
        tree.source_conversation_id = d.get("source_conversation_id")
        tree.checked_out_branch_id = d.get("checked_out_branch_id")
        
        if not tree.branches:
            tree.branches.append(Branch(name="main"))
            
        raw_positions = d.get("layout_positions") or {}
        normalized = {}
        if isinstance(raw_positions, dict):
            for k, v in raw_positions.items():
                p = _norm_pos(v)
                if p is not None:
                    normalized[str(k)] = p
        tree.layout_positions = normalized
        
        if not tree.source_conversation_id:
            for tag in getattr(tree, "tags", []) or []:
                if isinstance(tag, str) and tag.startswith("cid:"):
                    tree.source_conversation_id = tag[4:]
                    break

        # Ensure checkout is valid
        if tree.checked_out_branch_id:
            if not tree.get_branch(tree.checked_out_branch_id):
                tree.checked_out_branch_id = None
        if not tree.checked_out_branch_id and tree.branches:
            root = tree.get_root_branch()
            tree.checked_out_branch_id = root.id if root else tree.branches[0].id

        return tree


def auto_detect_trees(prompt_database) -> List[Dict[str, Any]]:
    groups: Dict[str, List] = {}
    
    # SAFEGUARD: Catch unintialized databases during startup
    if not prompt_database or not hasattr(prompt_database, "prompts"):
        return []
        
    for p in prompt_database.prompts:
        cid = getattr(p, "conversation_id", None) or ""
        if not cid:
            # Backward-compat: group old extension prompts recorded before the
            # conversationId fix by their URL path (stable within a conversation).
            if getattr(p, "source", "") == "Browser Extension" and getattr(p, "url", ""):
                from urllib.parse import urlparse
                parsed = urlparse(p.url)
                cid = parsed.netloc + parsed.path
            else:
                continue
        # Normalize Gemini fallback IDs so proxy ("gemini.google.com/")
        # and extension ("gemini.google.com/app") group together.
        if cid in ("gemini.google.com/", "gemini.google.com"):
            cid = "gemini.google.com/app"
        groups.setdefault(cid, []).append(p)

    suggestions = []
    for cid, prompts in groups.items():
        prompts.sort(key=lambda p: p.timestamp)
        llms = list({p.llm_used for p in prompts if p.llm_used})
        suggestions.append({
            "conversation_id": cid,
            "prompt_count": len(prompts),
            "llms_used": llms,
            "first_timestamp": prompts[0].timestamp,
            "last_timestamp": prompts[-1].timestamp,
            "sample_description": prompts[0].description or prompts[0].prompt_text[:80],
            "prompt_ids": [p.id for p in prompts],
        })

    suggestions.sort(key=lambda s: s["last_timestamp"], reverse=True)
    return suggestions


def build_tree_with_forks(tree: ConversationTree, prompts, db) -> bool:
    """Detect forks in a list of prompts and build branches accordingly.

    Each prompt is independently placed on the correct branch based on its
    metadata — the function never relies on "checked-out branch" state to
    decide placement.

    Strategies (tried in order for each prompt):
    1. ``parent_message_id`` — if another prompt already shares the same
       parent, fork.  Otherwise, find the branch whose tip was the most
       recently placed prompt (its response generated this parent_message_id)
       and append there.
    2. ``messages_count`` — find the branch whose tip messages_count equals
       ``this_prompt.messages_count - 2``.  If none match but a branch has
       a *higher* count, the user went back → fork.
    3. Fallback — append to the root branch.

    Returns True if the tree was modified.
    """
    if not prompts:
        return False

    existing_ids: set = set()
    for b in tree.branches:
        existing_ids.update(b.prompt_ids)

    new_prompts = [p for p in prompts if p.id not in existing_ids]
    if not new_prompts:
        return False

    root = tree.get_root_branch()
    if root is None:
        return False

    # --- Lookup: parent_message_id → [(branch, prompt_index)] ---
    # Tracks which prompts reply to which parent messages.
    pmid_locs: Dict[str, List[tuple]] = {}

    # --- Lookup: branch_id → messages_count of last prompt ---
    tip_mc: Dict[str, int] = {}

    # --- Lookup: branch_id → timestamp of the most recently placed prompt ---
    # Used to determine which branch a new prompt continues when its
    # parent_message_id is new (i.e. it's a linear continuation, not a fork).
    tip_ts: Dict[str, Any] = {}

    def _index_branch(branch):
        """Add all prompts in *branch* to the lookup maps."""
        for idx, pid in enumerate(branch.prompt_ids):
            p = db.get_prompt(pid)
            if not p:
                continue
            if p.metadata:
                pmid = p.metadata.get("parent_message_id")
                if pmid:
                    pmid_locs.setdefault(pmid, []).append((branch, idx))
                mc = p.metadata.get("messages_count")
                if mc is not None:
                    tip_mc[branch.id] = mc
            # Always track the latest timestamp per branch
            ts = p.timestamp
            if ts and (branch.id not in tip_ts or ts > tip_ts[branch.id]):
                tip_ts[branch.id] = ts

    for branch in tree.branches:
        _index_branch(branch)

    def _append_to_branch(branch, prompt, parent_msg_id, msg_count):
        """Helper: append *prompt* to *branch* and update lookup maps."""
        branch.prompt_ids.append(prompt.id)
        branch.updated_at = prompt.timestamp
        if parent_msg_id:
            pmid_locs.setdefault(parent_msg_id, []).append(
                (branch, len(branch.prompt_ids) - 1))
        if msg_count is not None:
            tip_mc[branch.id] = msg_count
        tip_ts[branch.id] = prompt.timestamp

    modified = False

    for prompt in new_prompts:
        meta = prompt.metadata or {}
        parent_msg_id = meta.get("parent_message_id")
        msg_count = meta.get("messages_count")
        placed = False

        # ----------------------------------------------------------
        # Strategy 1: parent_message_id
        # ----------------------------------------------------------
        if parent_msg_id:
            siblings = pmid_locs.get(parent_msg_id, [])
            if siblings:
                # Another prompt already replies to the same parent → fork.
                # The fork point is one index BEFORE the existing sibling
                # (i.e., the prompt whose *response* is the shared parent).
                sib_branch, sib_idx = siblings[0]
                fork_idx = max(0, sib_idx - 1)

                branch_num = len(tree.branches)
                new_branch = tree.add_branch(
                    name=f"branch-{branch_num}",
                    parent_branch_id=sib_branch.id,
                    fork_index=fork_idx,
                    trigger="auto_detected",
                    reason="Shared parent_message_id",
                )
                if new_branch:
                    new_branch.prompt_ids.append(prompt.id)
                    pmid_locs.setdefault(parent_msg_id, []).append(
                        (new_branch, len(new_branch.prompt_ids) - 1))
                    if msg_count is not None:
                        tip_mc[new_branch.id] = msg_count
                    tip_ts[new_branch.id] = prompt.timestamp
                    modified = True
                    placed = True
            else:
                # No sibling — this parent_message_id is new.  This prompt
                # is a linear continuation of whichever branch's tip prompt
                # generated the response.  Since we don't store response
                # message IDs, we use the heuristic: the branch whose tip
                # was placed most recently (chronologically) before this
                # prompt is the one the user is currently on.
                if tip_ts:
                    best_branch = None
                    best_ts = None
                    for branch in tree.branches:
                        ts = tip_ts.get(branch.id)
                        if ts is not None and ts < prompt.timestamp:
                            if best_ts is None or ts > best_ts:
                                best_ts = ts
                                best_branch = branch
                    if best_branch is not None:
                        _append_to_branch(best_branch, prompt,
                                          parent_msg_id, msg_count)
                        modified = True
                        placed = True

        # ----------------------------------------------------------
        # Strategy 2: messages_count
        # ----------------------------------------------------------
        if not placed and msg_count is not None:
            # Find a branch whose tip messages_count == msg_count - 2.
            # That branch is the natural linear continuation target.
            continuation_branch = None
            for branch in tree.branches:
                btmc = tip_mc.get(branch.id)
                if btmc is not None and btmc == msg_count - 2:
                    continuation_branch = branch
                    break

            if continuation_branch is not None:
                _append_to_branch(continuation_branch, prompt,
                                  parent_msg_id, msg_count)
                modified = True
                placed = True
            else:
                # No branch has the expected tip count.
                # If msg_count is LESS than the highest tip, user went back.
                max_mc = max(tip_mc.values()) if tip_mc else 0
                if max_mc > 0 and msg_count <= max_mc:
                    # Find the fork point: the branch and prompt whose
                    # messages_count is closest to (but <=) msg_count - 2.
                    best_branch = None
                    best_idx = 0
                    best_diff = float("inf")
                    target_mc = msg_count - 2  # the prompt we're replying to
                    for branch in tree.branches:
                        for idx, pid in enumerate(branch.prompt_ids):
                            p = db.get_prompt(pid)
                            if p and p.metadata:
                                p_mc = p.metadata.get("messages_count")
                                if p_mc is not None and p_mc <= target_mc:
                                    diff = target_mc - p_mc
                                    if diff < best_diff:
                                        best_diff = diff
                                        best_branch = branch
                                        best_idx = idx

                    if best_branch is not None:
                        # Check if best_idx is the tip — if so, just append
                        if best_idx == len(best_branch.prompt_ids) - 1:
                            _append_to_branch(best_branch, prompt,
                                              parent_msg_id, msg_count)
                            modified = True
                            placed = True
                        else:
                            # Fork from best_idx
                            branch_num = len(tree.branches)
                            new_branch = tree.add_branch(
                                name=f"branch-{branch_num}",
                                parent_branch_id=best_branch.id,
                                fork_index=best_idx,
                                trigger="auto_detected",
                                reason="messages_count regression",
                            )
                            if new_branch:
                                new_branch.prompt_ids.append(prompt.id)
                                tip_mc[new_branch.id] = msg_count
                                if parent_msg_id:
                                    pmid_locs.setdefault(
                                        parent_msg_id, []).append(
                                        (new_branch,
                                         len(new_branch.prompt_ids) - 1))
                                tip_ts[new_branch.id] = prompt.timestamp
                                modified = True
                                placed = True

        # ----------------------------------------------------------
        # Fallback: append to root
        # ----------------------------------------------------------
        if not placed:
            _append_to_branch(root, prompt, parent_msg_id, msg_count)
            modified = True

    if modified:
        tree.updated_at = new_prompts[-1].timestamp

    return modified



@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\core\profiles.py

"""
Profile persistence for LLM Buddy.

Profiles store user configurations (folders, extensions, header/footer, etc.)
as JSON on disk.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

from llm_buddy.paths import get_data_dir

DEFAULT_CONFIG_FILE = os.path.join(get_data_dir(), "profiles.json")


def load_profiles(config_file=None):
    """Load profiles from the JSON config file."""
    path = config_file or DEFAULT_CONFIG_FILE
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading profiles: %s", e)
    return {}


def save_profiles(profiles, config_file=None):
    """Save profiles to the JSON config file."""
    path = config_file or DEFAULT_CONFIG_FILE
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=4)
    except Exception as e:
        logger.error("Error saving profiles: %s", e)


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\core\rollback.py

"""
File rollback utilities for LLM Buddy.

Parse combined backup files and restore individual files from them.
"""

import difflib
import logging
import os
import re

logger = logging.getLogger(__name__)

def parse_combined_file(filepath):
    """
    Parse a combined backup file and extract individual files.
    Detects dynamic markers to prevent markdown collision, with a fallback
    to legacy ### markers for older backups.

    Returns:
        dict: Mapping of file paths to file contents.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Look for the dynamic marker declaration at the top of the file
        marker_match = re.search(r'^LLM_BUDDY_MARKER:\s*(.+)$', content, flags=re.MULTILINE)
        
        if not marker_match:
            # Legacy fallback: If no dynamic marker is found, assume it's an old backup using ###
            dynamic_marker = "###"
        else:
            dynamic_marker = marker_match.group(1).strip()

        # 2. Escape the dynamic marker just in case, and split the file blocks
        split_pattern = rf'^{re.escape(dynamic_marker)} (.+?)$'
        file_blocks = re.split(split_pattern, content, flags=re.MULTILINE)

        files_dict = {}
        for i in range(1, len(file_blocks), 2):
            if i + 1 < len(file_blocks):
                file_path = file_blocks[i].strip()
                file_content = file_blocks[i + 1]
                
                # 1. CLEAN THE TOP: Remove the 2 artificial newlines 
                # (1 from the marker line ending + 1 from the injected empty line)
                if file_content.startswith('\n\n'):
                    file_content = file_content[2:]
                elif file_content.startswith('\n'):
                    file_content = file_content[1:]
                    
                # 2. CLEAN THE BOTTOM: Remove the artificial trailing newlines
                is_last_block = (i + 1 == len(file_blocks) - 1)
                
                if not is_last_block:
                    # Middle blocks have '\n\n' injected between them
                    if file_content.endswith('\n\n'):
                        file_content = file_content[:-2]
                else:
                    # The very last block only has a single '\n' injected at EOF
                    if file_content.endswith('\n'):
                        file_content = file_content[:-1]

                files_dict[file_path] = file_content

        return files_dict
    except Exception as e:
        logger.error("Error parsing combined file: %s", e)
        return {}


def restore_file(file_path, content):
    """
    Restore a file to its original location with the provided content.

    Creates parent directories if they don't exist.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error("Error restoring file %s: %s", file_path, e)
        return False


def restore_file_to(original_path, content, target_root):
    """
    Restore a file under a different root directory.
    
    Preserves the relative structure by finding the common prefix
    of all files and re-rooting under target_root.
    """
    return restore_file(os.path.join(target_root, original_path), content)


def remap_path(original_path, all_paths, target_root):
    """Remap an original absolute path to a new root, preserving structure."""
    common = os.path.commonpath(all_paths)
    relative = os.path.relpath(original_path, common)
    return os.path.join(target_root, relative)


def get_file_diff(file_path, backup_content):
    """
    Get a unified diff between the current file and backup content.

    Returns a formatted diff string, or a status message if files
    are identical or the current file doesn't exist.
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                current_content = f.read()
        else:
            return "Current file does not exist - this would be a new file creation."

        current_lines = current_content.splitlines()
        backup_lines = backup_content.splitlines()

        diff = difflib.unified_diff(
            current_lines, backup_lines,
            fromfile=f"Current: {file_path}",
            tofile=f"Backup: {file_path}",
            lineterm='',
        )

        diff_text = '\n'.join(list(diff))
        if not diff_text:
            return "No differences found."
        return diff_text
    except Exception as e:
        return f"Error generating diff: {e}"


def diff_two_contents(content_a, content_b, label_a="File A", label_b="File B"):
    """
    Get a unified diff between two arbitrary text contents.

    Args:
        content_a: Text content of the first file.
        content_b: Text content of the second file.
        label_a: Display label for the first file (used in diff header).
        label_b: Display label for the second file (used in diff header).

    Returns:
        A formatted unified diff string, or a status message if identical.
    """
    try:
        lines_a = content_a.splitlines()
        lines_b = content_b.splitlines()

        diff = difflib.unified_diff(
            lines_a, lines_b,
            fromfile=label_a,
            tofile=label_b,
            lineterm='',
        )

        diff_text = '\n'.join(list(diff))
        if not diff_text:
            return "No differences found."
        return diff_text
    except Exception as e:
        return f"Error generating diff: {e}"


def read_file_content(file_path):
    """
    Read and return the text content of a file.

    Args:
        file_path: Path to the file to read.

    Returns:
        Tuple of (content_string, error_string). On success error is None;
        on failure content is None.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read(), None
    except Exception as e:
        return None, str(e)


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\core\sessions.py

"""
Research session model and persistence for LLM Buddy.

A *research session* is a named, bounded period of work (e.g.
"eADR Cycle 3: Agent Independence Testing") that groups prompts,
file changes, eADR notes, and backups into a coherent unit.

On session close the tool auto-generates a structured summary that
serves as an exportable "methods appendix" for each iteration cycle.
"""

import logging
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



@dataclass
class ResearchSession:
    """A single research session.

    Status lifecycle: ``active`` → ``paused`` ↔ ``active`` → ``completed``

    When paused, ``paused_elapsed`` accumulates the seconds of active
    work so far and ``paused_at`` records when the pause began.  On
    resume, those are folded back into the running total.
    """

    id: str = ""
    name: str = ""
    project: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "active"  # "active" | "paused" | "completed"
    start_snapshot: Dict[str, Any] = field(default_factory=dict)
    end_snapshot: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    notes: str = ""
    # Pause tracking: accumulated active seconds before the current
    # pause, and the timestamp of the most recent pause.
    paused_elapsed: float = 0.0
    paused_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.start_time is None:
            self.start_time = datetime.now()


    def pause(self) -> None:
        """Pause a running session, freezing the elapsed clock."""
        if self.status != "active":
            return
        now = datetime.now()
        # Add the time since start (or last resume) to the accumulator
        ref = self.paused_at or self.start_time or now
        # On first pause, ref == start_time, so this is total active so far.
        # After a resume, paused_at is cleared and start_time stays
        # the same, so we instead track via _active_seconds_since_resume.
        self.paused_elapsed = self.active_seconds
        self.paused_at = now
        self.status = "paused"

    def resume(self) -> None:
        """Resume a paused session."""
        if self.status != "paused":
            return
        self.paused_at = None
        # Shift start_time forward so that (now - start_time) matches
        # the real active duration stored in paused_elapsed.
        # On next tick: active_seconds = paused_elapsed + (now - start_time)
        # So we want (now - new_start_time) == 0 at this moment.
        self.start_time = datetime.now()
        self.status = "active"

    @property
    def active_seconds(self) -> float:
        """Total *active* (un-paused) seconds for this session."""
        if self.start_time is None:
            return self.paused_elapsed
        if self.status == "paused":
            # Frozen: return the value stored at pause time
            return self.paused_elapsed
        if self.status == "completed":
            end = self.end_time or datetime.now()
            return self.paused_elapsed + (end - self.start_time).total_seconds()
        # Running
        return self.paused_elapsed + (
            datetime.now() - self.start_time).total_seconds()


    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serialisable dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "project": self.project,
            "start_time": self.start_time.isoformat()
                          if self.start_time else None,
            "end_time": self.end_time.isoformat()
                        if self.end_time else None,
            "status": self.status,
            "start_snapshot": self.start_snapshot,
            "end_snapshot": self.end_snapshot,
            "summary": self.summary,
            "notes": self.notes,
            "paused_elapsed": self.paused_elapsed,
            "paused_at": self.paused_at.isoformat()
                         if self.paused_at else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResearchSession":
        """Create from dictionary."""
        session = cls()
        session.id = d.get("id", str(uuid.uuid4()))
        session.name = d.get("name", "")
        session.project = d.get("project", "")
        session.status = d.get("status", "completed")
        session.start_snapshot = d.get("start_snapshot", {})
        session.end_snapshot = d.get("end_snapshot")
        session.summary = d.get("summary")
        session.notes = d.get("notes", "")
        session.paused_elapsed = d.get("paused_elapsed", 0.0)

        st = d.get("start_time")
        session.start_time = _parse_dt(st) if st else datetime.now()
        et = d.get("end_time")
        session.end_time = _parse_dt(et) if et else None
        pa = d.get("paused_at")
        session.paused_at = _parse_dt(pa) if pa else None

        return session

    @property
    def duration_str(self) -> str:
        """Human-readable *active* duration (excludes paused time)."""
        total_secs = int(self.active_seconds)
        if total_secs < 0:
            return "\u2014"
        hours, rem = divmod(total_secs, 3600)
        mins, secs = divmod(rem, 60)
        if hours:
            return f"{hours}h {mins}m"
        if mins:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    @property
    def is_running(self) -> bool:
        """True if the session is active (not paused, not completed)."""
        return self.status == "active"



def capture_snapshot(prompt_db, db=None,
                     backup_config=None) -> Dict[str, Any]:
    """Capture the current state for later comparison.

    Parameters
    ----------
    prompt_db : PromptDatabase instance
    db : PromptDatabase instance (for eADR note count; same object as
         prompt_db when called from the GUI)
    backup_config : AutoBackupConfig instance (or None)
    """
    prompt_ids = [p.id for p in prompt_db.prompts]

    notes = []
    try:
        if db is not None:
            notes = db.get_eadr_notes()
    except Exception:
        pass

    note_timestamps = [n.timestamp for n in notes]

    file_hashes: Dict[str, Any] = {}
    if backup_config and hasattr(backup_config, "file_hashes"):
        file_hashes = dict(backup_config.file_hashes)

    return {
        "prompt_count": len(prompt_ids),
        "prompt_ids": prompt_ids,
        "note_count": len(notes),
        "note_timestamps": note_timestamps,
        "file_hashes": file_hashes,
        "timestamp": datetime.now().isoformat(),
    }


def compute_session_diff(start_snapshot: Dict[str, Any],
                         end_snapshot: Dict[str, Any],
                         prompt_db) -> Dict[str, Any]:
    """Compute what changed between start and end snapshots.

    Returns a dict with counts and lists suitable for summary
    generation.
    """
    start_ids = set(start_snapshot.get("prompt_ids", []))
    end_ids = set(end_snapshot.get("prompt_ids", []))
    new_ids = end_ids - start_ids

    # Gather details from the prompts that were added this session
    llm_counter: Counter = Counter()
    total_prompt_tokens = 0
    total_response_tokens = 0
    for p in prompt_db.prompts:
        if p.id in new_ids:
            llm_counter[p.llm_used] += 1
            total_prompt_tokens += len(p.prompt_text or "")
            total_response_tokens += len(
                getattr(p, "response_text", "") or "")

    start_hashes = start_snapshot.get("file_hashes", {})
    end_hashes = end_snapshot.get("file_hashes", {})
    files_changed = []
    for fp in end_hashes:
        if end_hashes.get(fp) != start_hashes.get(fp):
            files_changed.append(fp)
    # Also include files that existed in start but not end (deleted)
    for fp in start_hashes:
        if fp not in end_hashes and fp not in files_changed:
            files_changed.append(fp)

    new_note_count = (
        end_snapshot.get("note_count", 0)
        - start_snapshot.get("note_count", 0)
    )

    return {
        "new_prompt_count": len(new_ids),
        "new_prompt_ids": list(new_ids),
        "new_note_count": max(new_note_count, 0),
        "files_changed": files_changed,
        "llms_used": dict(llm_counter),
        "total_prompt_tokens": total_prompt_tokens,
        "total_response_tokens": total_response_tokens,
    }



def generate_session_summary_markdown(
        session: ResearchSession,
        diff: Dict[str, Any]) -> str:
    """Produce an exportable Markdown methods-appendix summary."""
    lines: List[str] = []

    lines.append(f"# Research Session: {session.name}")
    lines.append("")
    lines.append(f"**Project:** {session.project or '(not set)'}")

    start_str = (session.start_time.strftime("%Y-%m-%d %H:%M")
                 if session.start_time else "—")
    end_str = (session.end_time.strftime("%Y-%m-%d %H:%M")
               if session.end_time else "—")
    lines.append(
        f"**Period:** {start_str} \u2013 {end_str} ({session.duration_str})")
    lines.append(f"**Status:** {session.status.capitalize()}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"- **Prompts issued:** {diff.get('new_prompt_count', 0)}")
    llms = diff.get("llms_used", {})
    lines.append(
        f"- **LLMs used:** {', '.join(llms.keys()) if llms else 'None'}")
    lines.append(
        f"- **Files changed:** {len(diff.get('files_changed', []))}")
    lines.append(
        f"- **eADR notes created:** {diff.get('new_note_count', 0)}")
    lines.append(
        f"- **Total prompt characters:** "
        f"{diff.get('total_prompt_tokens', 0):,}")
    lines.append(
        f"- **Total response characters:** "
        f"{diff.get('total_response_tokens', 0):,}")
    lines.append("")

    if llms:
        lines.append("## LLM Usage Breakdown")
        lines.append("")
        lines.append("| LLM | Prompts |")
        lines.append("|-----|---------|")
        for llm, count in sorted(llms.items(),
                                  key=lambda x: x[1], reverse=True):
            lines.append(f"| {llm} | {count} |")
        lines.append("")

    changed = diff.get("files_changed", [])
    if changed:
        lines.append("## Files Changed")
        lines.append("")
        for fp in changed:
            lines.append(f"- `{fp}`")
        lines.append("")

    if session.notes:
        lines.append("## Session Notes")
        lines.append("")
        lines.append(session.notes)
        lines.append("")

    return "\n".join(lines)



def _parse_dt(s: str) -> Optional[datetime]:
    """Parse an ISO timestamp string into a datetime."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\core\tokens.py

"""
Token counting and text building utilities for LLM Buddy.
"""

import uuid
import logging

logger = logging.getLogger(__name__)

def build_combined_text(selected_files, header="", footer=""):
    """
    Build combined text from selected files with optional header/footer.

    Each file is preceded by a dynamically generated marker for identification
    to prevent markdown collision.
    """
    lines = []
    
    # Generate a unique 8-character ID for this specific backup
    session_id = uuid.uuid4().hex[:8]
    dynamic_marker = f"@§A_{session_id}@"
    
    # Declare the marker at the very top of the file so rollback can find it
    lines.append(f"LLM_BUDDY_MARKER: {dynamic_marker}")
    lines.append("")
    
    if header:
        lines.append(header)
        lines.append("")
        
    for file_path in selected_files:
        # Use the dynamic marker instead of ###
        lines.append(f"{dynamic_marker} {file_path}")
        lines.append("")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines.append(f.read())
        except Exception as e:
            lines.append(f"Error reading file: {e}")
        lines.append("")
        
    if footer:
        lines.append(footer)
        
    return "\n".join(lines)


def build_content_only_text(file_paths):
    """Build combined text from files without headers."""
    lines = []
    for file_path in file_paths:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines.append(f.read())
        except Exception as e:
            lines.append(f"Error reading file: {e}")
        lines.append("")
    return "\n".join(lines)


def count_tokens(text, encoding_name="cl100k_base"):
    """Count tokens in a text string using tiktoken."""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except ImportError:
        logger.warning("tiktoken not installed, falling back to word count")
        return len(text.split())
    except Exception as e:
        logger.error("Error counting tokens: %s", e)
        return len(text.split())


def count_tokens_in_file(filepath, encoding_name="cl100k_base"):
    """Count tokens in a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        return count_tokens(text, encoding_name)
    except Exception:
        return 0


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\core\__init__.py



@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\app.py

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


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\main_window.py

"""Main application window for LLM Buddy (PySide6).

Owns the shared application state (database, profiles, file lists)
and wires all panels together via Qt signals and slots.
"""

import os
import sys

from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QAction, QKeySequence, QFont, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QComboBox, QPushButton, QStatusBar,
    QInputDialog, QMessageBox, QFrame,
)

from llm_buddy.core.database import PromptDatabase
from llm_buddy.core.profiles import load_profiles, save_profiles
from llm_buddy.qt.theme import (
    THEMES, apply_theme, get_theme_colors, current_theme_name, STATUS_GREEN,
)
from llm_buddy.qt.widgets.toast import ToastManager
from llm_buddy.qt.panels.help_panel import HelpPanel, AboutPanel
from llm_buddy.qt.panels.log_panel import LogPanel
from llm_buddy.qt.panels.eadr_panel import EadrPanel
from llm_buddy.qt.panels.control_panel import ControlPanel
from llm_buddy.qt.panels.preview_panel import PreviewPanel
from llm_buddy.qt.panels.rollback_panel import RollbackPanel
from llm_buddy.qt.panels.compare_panel import ComparePanel
from llm_buddy.qt.panels.backup_panel import BackupPanel
from llm_buddy.qt.panels.capture_widgets import (
    ExtensionServerWidget, ProxyRecorderWidget,
)
from llm_buddy.qt.panels.prompts_panel import PromptsPanel
from llm_buddy.qt.panels.analytics_panel import AnalyticsPanel
from llm_buddy.qt.panels.sessions_panel import SessionsPanel
from llm_buddy.qt.panels.forking_panel import ForkingPanel


class LLMBuddyWindow(QMainWindow):
    """Top-level application window.

    Owns the shared application state (database, profiles) and
    wires panels together via Qt signals.
    """

    # Signals that panels can connect to
    log_message = Signal(str)
    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLM Buddy \u2013 Prompt Recording & Management")
        self.resize(1200, 800)

        self.profiles = load_profiles()
        self.current_profile = None
        self.folders: list[str] = []
        self.all_files: list[str] = []
        self.filtered_files: list[tuple[str, int]] = []
        self.backup_files: dict = {}

        self.allowed_extensions = (
            ".py,.kt,.xml,.html,.js,.txt,.md,.json,.css,"
            ".bat,.p12,.pem,.sh,.env,.R,.toml"
        )
        self.min_tokens = 0

        # Compute data paths at construction time (not module-import time)
        self.prompt_database = PromptDatabase()
        self.prompt_database.load()

        self._build_toolbar()

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.setCentralWidget(central)

        # Session status bar (hidden when no session is active)
        self._session_bar = self._build_session_bar()
        self._session_bar.setVisible(False)
        central_layout.addWidget(self._session_bar)

        self._splitter = QSplitter(Qt.Horizontal)
        central_layout.addWidget(self._splitter, stretch=1)

        self._control_panel = ControlPanel(self)
        self._splitter.addWidget(self._control_panel)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)  # cleaner tab rendering
        self._splitter.addWidget(self._tabs)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 2)

        self._log_panel = LogPanel()
        self._eadr_panel = EadrPanel(log_fn=self.log, toast_fn=self.show_toast,
                                     db=self.prompt_database)
        self._preview_panel = PreviewPanel(self)
        self._rollback_panel = RollbackPanel(self)
        self._compare_panel = ComparePanel(self)
        self._backup_panel = BackupPanel(self)
        self._help_panel = HelpPanel()
        self._about_panel = AboutPanel()

        # Capture widgets (shared between main window and prompts panel)
        self._ext_widget = ExtensionServerWidget(self)
        self._proxy_widget = ProxyRecorderWidget(self)

        self._prompts_panel = PromptsPanel(
            self, self._ext_widget, self._proxy_widget)
        self._analytics_panel = AnalyticsPanel(self)
        self._sessions_panel = SessionsPanel(self)
        self._forking_panel = ForkingPanel(self)

        # Log signal → Log panel
        self.log_message.connect(self._log_panel.append)

        # Control panel file changes → preview + status bar
        self._control_panel.files_changed.connect(
            self._preview_panel.update_preview)
        self._control_panel.files_changed.connect(self._update_file_status)

        # Tab change → lazy refresh for analytics/sessions
        self._tabs.currentChanged.connect(self._on_tab_changed)

        self._eadr_panel.note_saved.connect(
            lambda: self.log("eADR note saved."))

        # Forking signals → auto eADR notes
        self._forking_panel.branch_forked.connect(self._on_branch_forked)
        self._forking_panel.branch_merged.connect(self._on_branch_merged)

        # Theme changes → forking graph repaint
        self.theme_changed.connect(self._forking_panel._graph_view.update_theme)

        # Session state → toolbar bar
        self._sessions_panel.session_state_changed.connect(
            self._on_session_state_changed)

        self._tabs.addTab(self._eadr_panel,      "\U0001f4dd Research Notes")
        self._tabs.addTab(self._prompts_panel,    "\U0001f4ac Prompt Tracking")
        self._tabs.addTab(self._forking_panel,    "\U0001f333 Prompt Explorer")
        self._tabs.addTab(self._sessions_panel,   "\U0001f9ea Sessions")
        self._tabs.addTab(self._analytics_panel,  "\U0001f4ca Analytics")
        self._tabs.addTab(self._preview_panel,    "\U0001f441 Preview")
        self._tabs.addTab(self._compare_panel,    "\U0001f50d Compare Files")
        self._tabs.addTab(self._backup_panel,     "\U0001f4be Auto-Backup")
        self._tabs.addTab(self._rollback_panel,   "\u23ea Rollback")
        self._tabs.addTab(self._log_panel,        "\U0001f4cb Logs")
        self._tabs.addTab(self._help_panel,       "\u2753 Help")
        self._tabs.addTab(self._about_panel,      "\u2139 About")

        # Store tab indices for lazy-refresh logic
        self._tab_indices = {
            "analytics": self._tabs.indexOf(self._analytics_panel),
            "sessions": self._tabs.indexOf(self._sessions_panel),
            "prompts": self._tabs.indexOf(self._prompts_panel),
            "forking": self._tabs.indexOf(self._forking_panel),
        }

        # Prompt tab badge state
        self._last_prompt_count = 0
        self._prompt_tab_unread = False

        self._build_menus()

        self._setup_shortcuts()

        self._status = QStatusBar()
        self.setStatusBar(self._status)

        # Permanent status widgets
        self._file_count_label = QLabel("Files: 0")
        self._file_count_label.setStyleSheet("padding: 0 8px;")
        self._prompt_count_label = QLabel("Prompts: 0")
        self._prompt_count_label.setStyleSheet("padding: 0 8px;")
        self._profile_label = QLabel("No profile")
        self._profile_label.setStyleSheet(
            "padding: 0 8px; font-style: italic;")

        self._status.addPermanentWidget(self._profile_label)
        self._status.addPermanentWidget(self._file_count_label)
        self._status.addPermanentWidget(self._prompt_count_label)
        self._status.showMessage("Ready", 3000)

        # Periodic prompt count refresh (every 10s)
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status_counts)
        self._status_timer.start(10_000)

        self._toast_manager = ToastManager(self)

        self._handle_cli_args()
        if self.all_files or self.folders:
            self._control_panel.apply_filters()
        self._refresh_status_counts()
        self.log("LLM Buddy started.")

    def _build_toolbar(self):
        toolbar_widget = QWidget()
        layout = QHBoxLayout(toolbar_widget)
        layout.setContentsMargins(6, 4, 6, 4)

        lbl_profile = QLabel("Profile:")
        lbl_profile.setFont(QFont(lbl_profile.font().family(), -1, QFont.Bold))
        layout.addWidget(lbl_profile)
        self._profile_combo = QComboBox()
        self._profile_combo.setEditable(True)
        self._profile_combo.addItems(list(self.profiles.keys()))
        self._profile_combo.setMinimumWidth(160)
        self._profile_combo.setToolTip("Select or type a profile name")
        self._profile_combo.activated.connect(self._load_profile)
        layout.addWidget(self._profile_combo, stretch=1)

        btn_save = QPushButton("Save Profile")
        btn_save.setToolTip("Save current settings to the selected profile")
        btn_save.clicked.connect(self._save_profile)
        layout.addWidget(btn_save)

        btn_new = QPushButton("New Profile")
        btn_new.setToolTip("Create a new blank profile")
        btn_new.clicked.connect(self._new_profile)
        layout.addWidget(btn_new)

        layout.addSpacing(16)

        lbl_theme = QLabel("Theme:")
        lbl_theme.setFont(QFont(lbl_theme.font().family(), -1, QFont.Bold))
        layout.addWidget(lbl_theme)
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(list(THEMES.keys()))
        self._theme_combo.setToolTip("Switch application colour theme")
        self._theme_combo.currentTextChanged.connect(self._change_theme)
        layout.addWidget(self._theme_combo)

        # Install as toolbar widget (sits above splitter)
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addWidget(toolbar_widget)

    def _build_session_bar(self) -> QWidget:
        """Build the compact session status bar shown when a session is active."""
        bar = QFrame()
        bar.setFrameShape(QFrame.StyledPanel)
        bar.setStyleSheet(
            "QFrame { background: palette(window); "
            "border-bottom: 1px solid palette(mid); }"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self._sbar_dot = QLabel("\u25cf")
        self._sbar_dot.setStyleSheet(f"color: {STATUS_GREEN}; font-size: 14px;")
        layout.addWidget(self._sbar_dot)

        self._sbar_name = QLabel("")
        font = self._sbar_name.font()
        font.setBold(True)
        self._sbar_name.setFont(font)
        layout.addWidget(self._sbar_name)

        self._sbar_elapsed = QLabel("")
        timer_font = QFont("Consolas", 11)
        timer_font.setBold(True)
        self._sbar_elapsed.setFont(timer_font)
        self._sbar_elapsed.setStyleSheet(f"color: {STATUS_GREEN};")
        layout.addWidget(self._sbar_elapsed)

        layout.addStretch()

        self._sbar_btn_pause = QPushButton("\u23f8 Pause")
        self._sbar_btn_pause.setFixedWidth(90)
        self._sbar_btn_pause.clicked.connect(
            lambda: self._sessions_panel._toggle_pause())
        layout.addWidget(self._sbar_btn_pause)

        btn_end = QPushButton("\u25a0 End")
        btn_end.setFixedWidth(70)
        btn_end.setProperty("class", "danger")
        btn_end.clicked.connect(
            lambda: self._sessions_panel.end_current_session())
        layout.addWidget(btn_end)

        return bar

    @Slot(str, str, bool)
    def _on_session_state_changed(self, name: str, elapsed: str,
                                   is_paused: bool) -> None:
        """Update the session status bar from the sessions panel signal."""
        if not name:
            self._session_bar.setVisible(False)
            return

        self._session_bar.setVisible(True)
        self._sbar_name.setText(f"Session: \u201c{name}\u201d")
        self._sbar_elapsed.setText(elapsed)

        colors = get_theme_colors(current_theme_name())
        if is_paused:
            self._sbar_dot.setStyleSheet(
                f"color: {colors['warning']}; font-size: 14px;")
            self._sbar_elapsed.setStyleSheet("color: palette(mid);")
            self._sbar_btn_pause.setText("\u25b6 Resume")
        else:
            self._sbar_dot.setStyleSheet(
                f"color: {colors['success']}; font-size: 14px;")
            self._sbar_elapsed.setStyleSheet(f"color: {colors['success']};")
            self._sbar_btn_pause.setText("\u23f8 Pause")

    def _build_menus(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")

        act_combine = QAction("&Combine Scripts", self)
        act_combine.setShortcut(QKeySequence("Ctrl+Shift+C"))
        act_combine.triggered.connect(self._control_panel.combine_scripts)
        file_menu.addAction(act_combine)

        file_menu.addSeparator()

        act_clear_log = QAction("Clear &Log", self)
        act_clear_log.triggered.connect(self._log_panel.clear_log)
        file_menu.addAction(act_clear_log)

        file_menu.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        view_menu = menu_bar.addMenu("&View")
        for i in range(self._tabs.count()):
            tab_name = self._tabs.tabText(i)
            act = QAction(tab_name, self)
            # Ctrl+1 through Ctrl+0 for first 10 tabs
            if i < 10:
                key = str(i + 1) if i < 9 else "0"
                act.setShortcut(QKeySequence(f"Ctrl+{key}"))
            act.triggered.connect(
                lambda checked, idx=i: self._tabs.setCurrentIndex(idx))
            view_menu.addAction(act)

        theme_menu = menu_bar.addMenu("&Theme")
        for name in THEMES:
            act = QAction(name, self)
            act.triggered.connect(
                lambda checked, n=name: self._change_theme(n))
            theme_menu.addAction(act)

    def _setup_shortcuts(self):
        """Register global keyboard shortcuts."""
        sc_refresh = QShortcut(QKeySequence("F5"), self)
        sc_refresh.activated.connect(self._force_refresh)

    @Slot()
    def _force_refresh(self) -> None:
        """F5: reload database and refresh Prompts and Prompt Explorer panels."""
        self.prompt_database.load()
        if hasattr(self._prompts_panel, "refresh_prompt_history"):
            self._prompts_panel.refresh_prompt_history()
        if hasattr(self._forking_panel, "refresh"):
            self._forking_panel.refresh()
        if hasattr(self, "_status"):
            self._status.showMessage("Refreshed", 2000)

    @Slot(int)
    def _on_tab_changed(self, index: int) -> None:
        """Refresh data-heavy panels when their tab is activated."""
        tab_name = self._tabs.tabText(index)
        # Guard: may fire during init before all attrs exist
        if hasattr(self, "_status"):
            self._status.showMessage(f"Switched to {tab_name}", 2000)
        if not hasattr(self, "_tab_indices"):
            return

        if index == self._tab_indices.get("analytics"):
            if hasattr(self._analytics_panel, "refresh"):
                self._analytics_panel.refresh()
        elif index == self._tab_indices.get("sessions"):
            if hasattr(self._sessions_panel, "_refresh_session_tree"):
                self._sessions_panel._refresh_session_tree()
        elif index == self._tab_indices.get("prompts"):
            if hasattr(self._prompts_panel, "refresh_prompt_history"):
                # Reload from disk to pick up newly captured prompts
                self.prompt_database.load()
                self._prompts_panel.refresh_prompt_history()
            # Clear unread indicator when tab is visited
            self._prompt_tab_unread = False
            if hasattr(self, "_last_prompt_count"):
                self._update_prompt_tab_label(len(self.prompt_database.prompts))
        elif index == self._tab_indices.get("forking"):
            if hasattr(self._forking_panel, "refresh"):
                self._forking_panel.refresh()

    @Slot(object)
    def _update_file_status(self, files) -> None:
        """Update status bar when file list changes."""
        count = len(files) if files else 0
        total_tokens = sum(t for _, t in files) if files else 0
        self._file_count_label.setText(
            f"Files: {count}  |  Tokens: {total_tokens:,}")

    def _refresh_status_counts(self) -> None:
        """Periodically refresh prompt count in status bar and tab badge."""
        try:
            prompt_count = len(self.prompt_database.prompts)
            self._prompt_count_label.setText(f"Prompts: {prompt_count}")
            if hasattr(self, "_last_prompt_count"):
                self._update_prompt_tab_label(prompt_count)
        except Exception:
            pass

        if self.current_profile:
            self._profile_label.setText(f"Profile: {self.current_profile}")
        else:
            self._profile_label.setText("No profile")

    def _update_prompt_tab_label(self, count: int) -> None:
        """Update the Prompt Tracking tab label with current count and unread badge."""
        base = "\U0001f4ac Prompt Tracking"
        prompts_idx = self._tab_indices.get("prompts", -1)
        if prompts_idx < 0:
            return
        grew = count > self._last_prompt_count
        self._last_prompt_count = count
        is_active = self._tabs.currentIndex() == prompts_idx
        if grew and not is_active:
            self._prompt_tab_unread = True
        prefix = "\u2605 " if self._prompt_tab_unread else ""
        self._tabs.setTabText(prompts_idx, f"{prefix}{base} ({count})")

    def log(self, message: str) -> None:
        """Convenience method for logging from the main window."""
        self.log_message.emit(message)

    def show_toast(self, message: str, level: str = "info") -> None:
        """Show a non-blocking toast notification in the bottom-right corner."""
        self._toast_manager.show(message, level)

    @Slot(str, str, str, str)
    def _on_branch_forked(self, tree_name: str, parent_name: str,
                          child_name: str, trigger: str) -> None:
        """Auto-create an eADR note when a branch is forked."""
        project = self._eadr_panel.project
        note = (
            f"[CF Fork] Branch '{child_name}' forked from "
            f"'{parent_name}' in tree '{tree_name}'.\n"
            f"Trigger: {trigger}"
        )
        self.prompt_database.add_eadr_note(note, project)
        self._eadr_panel.refresh()
        self.log(f"eADR auto-note: fork '{child_name}' recorded.")

    @Slot(str, str, str)
    def _on_branch_merged(self, tree_name: str, branch_name: str,
                          insights: str) -> None:
        """Auto-create an eADR note when a branch is merged."""
        project = self._eadr_panel.project
        note = (
            f"[CF Merge] Branch '{branch_name}' merged "
            f"in tree '{tree_name}'.\n"
        )
        if insights:
            note += f"Insights: {insights}"
        self.prompt_database.add_eadr_note(note, project)
        self._eadr_panel.refresh()
        self.log(f"eADR auto-note: merge '{branch_name}' recorded.")

    @Slot(str)
    def _change_theme(self, name: str) -> None:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            apply_theme(app, name)
            self.theme_changed.emit(name)
            # Keep theme combo in sync if changed from menu
            if self._theme_combo.currentText() != name:
                self._theme_combo.blockSignals(True)
                self._theme_combo.setCurrentText(name)
                self._theme_combo.blockSignals(False)
            self.log(f"Theme changed to: {name}")

    @Slot(int)
    def _load_profile(self, _index: int = 0) -> None:
        prof_name = self._profile_combo.currentText().strip()
        if prof_name not in self.profiles:
            return
        prof = self.profiles[prof_name]
        self.folders = prof.get("folders", [])
        self.all_files = prof.get("files", [])
        self.allowed_extensions = prof.get(
            "allowed_extensions", self.allowed_extensions)
        self.min_tokens = prof.get("min_tokens", self.min_tokens)
        self.current_profile = prof_name

        # Sync control panel fields with profile data
        self._control_panel.set_extensions(self.allowed_extensions)
        self._control_panel.set_min_tokens(self.min_tokens)
        if hasattr(self._control_panel, "set_header"):
            self._control_panel.set_header(prof.get("header", ""))
        if hasattr(self._control_panel, "set_footer"):
            self._control_panel.set_footer(prof.get("footer", ""))

        self.log(f"Loaded profile '{prof_name}'.")
        self._refresh_status_counts()
        # Re-apply filters to reflect new data
        self._control_panel.apply_filters()

    @Slot()
    def _save_profile(self) -> None:
        prof_name = self._profile_combo.currentText().strip()
        if not prof_name:
            QMessageBox.warning(self, "Error", "Enter a valid profile name.")
            return
        self.profiles[prof_name] = {
            "folders": self.folders,
            "files": self.all_files,
            "allowed_extensions": self.allowed_extensions,
            "min_tokens": self.min_tokens,
            "header": getattr(self._control_panel, "header_text", ""),
            "footer": getattr(self._control_panel, "footer_text", ""),
        }
        save_profiles(self.profiles)
        # Refresh combo items
        self._profile_combo.clear()
        self._profile_combo.addItems(list(self.profiles.keys()))
        self._profile_combo.setCurrentText(prof_name)
        self.current_profile = prof_name
        self._refresh_status_counts()
        self.log(f"Profile '{prof_name}' saved.")

    @Slot()
    def _new_profile(self) -> None:
        name, ok = QInputDialog.getText(
            self, "New Profile", "Enter new profile name:")
        if ok and name.strip():
            name = name.strip()
            self._profile_combo.setCurrentText(name)
            self.folders = []
            self.all_files = []
            self.filtered_files = []
            self.current_profile = name
            self._refresh_status_counts()
            self.log(f"New profile '{name}' created.")
            self._control_panel.apply_filters()

    def _handle_cli_args(self) -> None:
        for path in sys.argv[1:]:
            if os.path.isfile(path):
                self.all_files.append(path)
                self.log(f"Added via command-line: {path}")
            elif os.path.isdir(path):
                self.folders.append(path)
                self.log(f"Added folder via command-line: {path}")

    def closeEvent(self, event):
        """Clean up resources on window close."""
        self.log("Shutting down...")

        # Stop periodic status refresh
        self._status_timer.stop()

        # Stop extension server
        self._ext_widget.stop_server()

        # Stop proxy and ensure system proxy is disabled
        self._proxy_widget.stop_proxy()

        # Stop auto-backup observer
        self._backup_panel.stop()

        event.accept()



@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\theme.py

"""Theming and colour palette for the LLM Buddy Qt GUI.

Provides Light, Dark, and Blue accent themes with comprehensive QSS
styling for all standard widgets plus QPalette overrides for proper
dark-mode rendering of native controls.

Also exports reusable helper widgets:
- ``StatusBadge`` – a rounded-pill status indicator label
- ``get_theme_colors()`` – returns a color dict for the named theme
"""

from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtWidgets import QApplication, QLabel, QFrame, QVBoxLayout

CHART_PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
    "#59a14f", "#edc948", "#b07aa1", "#ff9da7",
    "#9c755f", "#bab0ac",
]

# Timeline event colours
EVENT_COLOURS = {
    "prompt": "#4e79a7",
    "note": "#59a14f",
    "backup": "#f28e2b",
    "file_change": "#e15759",
}

# Status colours (accessible from any module)
STATUS_GREEN = "#2e7d32"
STATUS_RED = "#c62828"
STATUS_ORANGE = "#ef6c00"
STATUS_GRAY = "#757575"


_SHARED_WIDGET_RADIUS = "4px"

_SCROLLBAR_LIGHT = """
QScrollBar:vertical {
    background: #f0f0f0;
    width: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #c0c0c0;
    min-height: 30px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #a0a0a0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #f0f0f0;
    height: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background: #c0c0c0;
    min-width: 30px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background: #a0a0a0;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
"""

_SCROLLBAR_DARK = """
QScrollBar:vertical {
    background: #2a2a2a;
    width: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #555;
    min-height: 30px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #777;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #2a2a2a;
    height: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background: #555;
    min-width: 30px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background: #777;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
"""

_TOOLTIP_LIGHT = """
QToolTip {
    background-color: #424242;
    color: #fff;
    border: 1px solid #616161;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""

_TOOLTIP_DARK = """
QToolTip {
    background-color: #f5f5f5;
    color: #212121;
    border: 1px solid #bdbdbd;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""


# ══════════════════════════════════════════════════════════════════════
# Light theme
# ══════════════════════════════════════════════════════════════════════

LIGHT_QSS = (
    _TOOLTIP_LIGHT
    + _SCROLLBAR_LIGHT
    + """
/* ── Window & containers ─────────────────────────────────────────── */
QMainWindow {
    background-color: #fafafa;
    color: #333;
}
QSplitter::handle {
    background: #e0e0e0;
    width: 3px;
}
QSplitter::handle:hover {
    background: #1976d2;
}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {
    color: #333;
}

/* ── Tab widget ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    background: white;
}
QTabBar::tab {
    padding: 7px 18px;
    margin-right: 2px;
    border: 1px solid #d0d0d0;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background: #f0f0f0;
    color: #555;
    font-size: 13px;
}
QTabBar::tab:hover {
    background: #e8e8e8;
    color: #333;
}
QTabBar::tab:selected {
    background: white;
    color: #1976d2;
    font-weight: bold;
    border-bottom: 2px solid #1976d2;
}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 18px;
    color: #333;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #1976d2;
}

/* ── Trees ───────────────────────────────────────────────────────── */
QTreeView {
    alternate-background-color: #f5f8ff;
    background-color: #ffffff;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    font-size: 13px;
}
QTreeView::item {
    padding: 3px 0;
}
QTreeView::item:selected {
    background-color: #bbdefb;
    color: black;
}
QTreeView::item:hover {
    background-color: #e3f2fd;
}
QHeaderView::section {
    background-color: #f5f5f5;
    border: 1px solid #d0d0d0;
    border-left: none;
    padding: 5px 8px;
    font-weight: bold;
    font-size: 12px;
    color: #555;
}

/* ── Text areas ──────────────────────────────────────────────────── */
QPlainTextEdit, QTextBrowser {
    background-color: #ffffff;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    font-size: 13px;
    selection-background-color: #bbdefb;
}
QPlainTextEdit:focus, QTextBrowser:focus {
    border: 1px solid #1976d2;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    padding: 6px 16px;
    border: 1px solid #bdbdbd;
    border-radius: 4px;
    background-color: #f5f5f5;
    color: #333;
    font-size: 13px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #e3f2fd;
    border-color: #90caf9;
}
QPushButton:pressed {
    background-color: #bbdefb;
}
QPushButton:disabled {
    color: #aaa;
    background-color: #f0f0f0;
    border-color: #e0e0e0;
}
/* Primary action buttons (use setProperty("class", "primary") in code) */
QPushButton[class="primary"] {
    background-color: #1976d2;
    color: white;
    border: 1px solid #1565c0;
    font-weight: bold;
}
QPushButton[class="primary"]:hover {
    background-color: #1e88e5;
}
QPushButton[class="primary"]:pressed {
    background-color: #1565c0;
}
/* Danger buttons */
QPushButton[class="danger"] {
    background-color: #e53935;
    color: white;
    border: 1px solid #c62828;
}
QPushButton[class="danger"]:hover {
    background-color: #ef5350;
}

/* Capture source Start/Stop buttons (outline variants) */
QPushButton[class="start_action"] {
    background-color: transparent;
    color: #1976d2;
    border: 1px solid #1976d2;
    font-weight: bold;
}
QPushButton[class="start_action"]:hover {
    background-color: rgba(25, 118, 210, 0.10);
}
QPushButton[class="start_action"]:pressed {
    background-color: rgba(25, 118, 210, 0.20);
}
QPushButton[class="start_action"]:disabled {
    background-color: #f0f0f0;
    color: #aaa;
    border-color: #e0e0e0;
    font-weight: normal;
}

QPushButton[class="stop_action"] {
    background-color: transparent;
    color: #e53935;
    border: 1px solid #e53935;
    font-weight: bold;
}
QPushButton[class="stop_action"]:hover {
    background-color: rgba(229, 57, 53, 0.10);
}
QPushButton[class="stop_action"]:pressed {
    background-color: rgba(229, 57, 53, 0.20);
}
QPushButton[class="stop_action"]:disabled {
    background-color: #f0f0f0;
    color: #aaa;
    border-color: #e0e0e0;
    font-weight: normal;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox {
    padding: 5px 8px;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    background: white;
    color: #333;
    font-size: 13px;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #1976d2;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    selection-background-color: #bbdefb;
    selection-color: black;
}
QCheckBox {
    spacing: 6px;
    font-size: 13px;
    color: #333;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #bdbdbd;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #1976d2;
    border-color: #1565c0;
}

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {
    background: #f5f5f5;
    border-top: 1px solid #e0e0e0;
    font-size: 12px;
    color: #666;
}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {
    background-color: #f0f0f0;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    text-align: center;
    font-size: 12px;
    min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1976d2, stop:1 #42a5f5);
    border-radius: 3px;
}

/* ── Menu bar ────────────────────────────────────────────────────── */
QMenuBar {
    background: #f5f5f5;
    color: #333;
    border-bottom: 1px solid #e0e0e0;
    font-size: 13px;
}
QMenuBar::item:selected {
    background: #e3f2fd;
    border-radius: 4px;
}
QMenu {
    background: white;
    color: #333;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #e3f2fd;
}

/* ── Toolbar ─────────────────────────────────────────────────────── */
QToolBar {
    background: #f5f5f5;
    border-bottom: 1px solid #e0e0e0;
    spacing: 4px;
    padding: 2px;
}

/* ── Dialogs ─────────────────────────────────────────────────────── */
QDialog {
    background-color: #fafafa;
    color: #333;
}
QMessageBox {
    background-color: #fafafa;
    color: #333;
}
QMessageBox QLabel {
    color: #333;
}
"""
)


# ══════════════════════════════════════════════════════════════════════
# Dark theme
# ══════════════════════════════════════════════════════════════════════

DARK_QSS = (
    _TOOLTIP_DARK
    + _SCROLLBAR_DARK
    + """
/* ── Window & containers ─────────────────────────────────────────── */
QMainWindow {
    background-color: #1e1e1e;
    color: #ddd;
}
QSplitter::handle {
    background: #3a3a3a;
    width: 3px;
}
QSplitter::handle:hover {
    background: #64b5f6;
}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {
    color: #ddd;
}

/* ── Tab widget ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #444;
    border-radius: 4px;
    background: #1e1e1e;
}
QTabBar::tab {
    padding: 7px 18px;
    margin-right: 2px;
    border: 1px solid #444;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background: #2d2d2d;
    color: #999;
    font-size: 13px;
}
QTabBar::tab:hover {
    background: #383838;
    color: #ccc;
}
QTabBar::tab:selected {
    background: #1e1e1e;
    color: #64b5f6;
    font-weight: bold;
    border-bottom: 2px solid #64b5f6;
}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #444;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 18px;
    color: #ddd;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #64b5f6;
}

/* ── Trees ───────────────────────────────────────────────────────── */
QTreeView {
    alternate-background-color: #262626;
    background-color: #1e1e1e;
    border: 1px solid #444;
    border-radius: 4px;
    color: #ddd;
    font-size: 13px;
}
QTreeView::item {
    padding: 3px 0;
}
QTreeView::item:selected {
    background-color: #1565c0;
    color: white;
}
QTreeView::item:hover {
    background-color: #2a3a4a;
}
QHeaderView::section {
    background-color: #2d2d2d;
    border: 1px solid #444;
    border-left: none;
    padding: 5px 8px;
    font-weight: bold;
    font-size: 12px;
    color: #aaa;
}

/* ── Text areas ──────────────────────────────────────────────────── */
QPlainTextEdit, QTextBrowser {
    background-color: #1e1e1e;
    color: #ddd;
    border: 1px solid #444;
    border-radius: 4px;
    font-size: 13px;
    selection-background-color: #1565c0;
    selection-color: white;
}
QPlainTextEdit:focus, QTextBrowser:focus {
    border: 1px solid #64b5f6;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    padding: 6px 16px;
    border: 1px solid #555;
    border-radius: 4px;
    background-color: #333;
    color: #ddd;
    font-size: 13px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #2a3a4a;
    border-color: #5a8abf;
}
QPushButton:pressed {
    background-color: #1565c0;
    color: white;
}
QPushButton:disabled {
    color: #666;
    background-color: #2a2a2a;
    border-color: #3a3a3a;
}
QPushButton[class="primary"] {
    background-color: #1565c0;
    color: white;
    border: 1px solid #0d47a1;
    font-weight: bold;
}
QPushButton[class="primary"]:hover {
    background-color: #1976d2;
}
QPushButton[class="primary"]:pressed {
    background-color: #0d47a1;
}
QPushButton[class="danger"] {
    background-color: #c62828;
    color: white;
    border: 1px solid #b71c1c;
}
QPushButton[class="danger"]:hover {
    background-color: #e53935;
}

/* Capture source Start/Stop buttons (outline variants) */
QPushButton[class="start_action"] {
    background-color: transparent;
    color: #64b5f6;
    border: 1px solid #64b5f6;
    font-weight: bold;
}
QPushButton[class="start_action"]:hover {
    background-color: rgba(100, 181, 246, 0.15);
}
QPushButton[class="start_action"]:pressed {
    background-color: rgba(100, 181, 246, 0.25);
}
QPushButton[class="start_action"]:disabled {
    background-color: #2a2a2a;
    color: #666;
    border-color: #3a3a3a;
    font-weight: normal;
}

QPushButton[class="stop_action"] {
    background-color: transparent;
    color: #ef5350;
    border: 1px solid #ef5350;
    font-weight: bold;
}
QPushButton[class="stop_action"]:hover {
    background-color: rgba(239, 83, 80, 0.15);
}
QPushButton[class="stop_action"]:pressed {
    background-color: rgba(239, 83, 80, 0.25);
}
QPushButton[class="stop_action"]:disabled {
    background-color: #2a2a2a;
    color: #666;
    border-color: #3a3a3a;
    font-weight: normal;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox {
    background-color: #2d2d2d;
    color: #ddd;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 13px;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #64b5f6;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    border: 1px solid #555;
    border-radius: 4px;
    color: #ddd;
    selection-background-color: #1565c0;
    selection-color: white;
}
QCheckBox {
    spacing: 6px;
    color: #ddd;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #666;
    background-color: #333;
}
QCheckBox::indicator:checked {
    background-color: #1565c0;
    border-color: #0d47a1;
}

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {
    background: #2d2d2d;
    border-top: 1px solid #444;
    color: #aaa;
    font-size: 12px;
}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {
    border: 1px solid #444;
    border-radius: 4px;
    text-align: center;
    color: #ddd;
    font-size: 12px;
    background: #2a2a2a;
    min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1565c0, stop:1 #42a5f5);
    border-radius: 3px;
}

/* ── Menu bar ────────────────────────────────────────────────────── */
QMenuBar {
    background: #2d2d2d;
    border-bottom: 1px solid #444;
    color: #ddd;
    font-size: 13px;
}
QMenuBar::item:selected {
    background: #3a3a3a;
    border-radius: 4px;
}
QMenu {
    background: #2d2d2d;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px;
    color: #ddd;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #1565c0;
}

/* ── Toolbar ─────────────────────────────────────────────────────── */
QToolBar {
    background: #2d2d2d;
    border-bottom: 1px solid #444;
    spacing: 4px;
    padding: 2px;
}

/* ── Dialog ──────────────────────────────────────────────────────── */
QDialog {
    background-color: #1e1e1e;
    color: #ddd;
}
QMessageBox {
    background-color: #1e1e1e;
    color: #ddd;
}
QMessageBox QLabel {
    color: #ddd;
}
"""
)


# ══════════════════════════════════════════════════════════════════════
# Blue Accent theme (light base with blue accent colour)
# ══════════════════════════════════════════════════════════════════════

BLUE_ACCENT_QSS = (
    _TOOLTIP_LIGHT
    + _SCROLLBAR_LIGHT
    + """
/* ── Window & containers ─────────────────────────────────────────── */
QMainWindow {
    background-color: #e8eef7;
    color: #333;
}
QSplitter::handle {
    background: #c5cfe0;
    width: 3px;
}
QSplitter::handle:hover {
    background: #1565c0;
}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {
    color: #333;
}

/* ── Tab widget ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #b0c4de;
    border-radius: 4px;
    background: #f0f4fa;
}
QTabBar::tab {
    padding: 7px 18px;
    margin-right: 2px;
    border: 1px solid #b0c4de;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background: #dce6f5;
    color: #555;
    font-size: 13px;
}
QTabBar::tab:hover {
    background: #c8d8f0;
    color: #333;
}
QTabBar::tab:selected {
    background: #f0f4fa;
    color: #0d47a1;
    font-weight: bold;
    border-bottom: 2px solid #1565c0;
}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #b0c4de;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 18px;
    background: #f0f4fa;
    color: #333;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #0d47a1;
}

/* ── Trees ───────────────────────────────────────────────────────── */
QTreeView {
    alternate-background-color: #e8eef7;
    background: #f5f8fc;
    border: 1px solid #b0c4de;
    border-radius: 4px;
    font-size: 13px;
    color: #333;
}
QTreeView::item { padding: 3px 0; }
QTreeView::item:selected { background-color: #90caf9; color: black; }
QTreeView::item:hover { background-color: #bbdefb; }
QHeaderView::section {
    background-color: #dce6f5;
    border: 1px solid #b0c4de;
    border-left: none;
    padding: 5px 8px;
    font-weight: bold;
    font-size: 12px;
    color: #3a5a8a;
}

/* ── Text areas ──────────────────────────────────────────────────── */
QPlainTextEdit, QTextBrowser {
    background: #fafcff;
    color: #333;
    border: 1px solid #b0c4de;
    border-radius: 4px;
    font-size: 13px;
    selection-background-color: #90caf9;
}
QPlainTextEdit:focus, QTextBrowser:focus {
    border: 1px solid #1565c0;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    padding: 6px 16px;
    border: 1px solid #90a4c4;
    border-radius: 4px;
    background: #dce6f5;
    color: #333;
    font-size: 13px;
    min-height: 20px;
}
QPushButton:hover { background: #c8d8f0; border-color: #6a8ab8; color: #333; }
QPushButton:pressed { background: #90caf9; color: #333; }
QPushButton:disabled { color: #aaa; background: #e8eef7; border-color: #c5cfe0; }
QPushButton[class="primary"] {
    background: #1565c0; color: white;
    border: 1px solid #0d47a1; font-weight: bold;
}
QPushButton[class="primary"]:hover { background: #1976d2; color: white; }
QPushButton[class="danger"] {
    background: #e53935; color: white; border: 1px solid #c62828;
}

/* Capture source Start/Stop buttons (outline variants) */
QPushButton[class="start_action"] {
    background-color: transparent;
    color: #1565c0;
    border: 1px solid #1565c0;
    font-weight: bold;
}
QPushButton[class="start_action"]:hover {
    background-color: rgba(21, 101, 192, 0.12);
}
QPushButton[class="start_action"]:pressed {
    background-color: rgba(21, 101, 192, 0.22);
}
QPushButton[class="start_action"]:disabled {
    background-color: #e8eef7;
    color: #aaa;
    border-color: #c5cfe0;
    font-weight: normal;
}

QPushButton[class="stop_action"] {
    background-color: transparent;
    color: #e53935;
    border: 1px solid #e53935;
    font-weight: bold;
}
QPushButton[class="stop_action"]:hover {
    background-color: rgba(229, 57, 53, 0.12);
}
QPushButton[class="stop_action"]:pressed {
    background-color: rgba(229, 57, 53, 0.22);
}
QPushButton[class="stop_action"]:disabled {
    background-color: #e8eef7;
    color: #aaa;
    border-color: #c5cfe0;
    font-weight: normal;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox {
    padding: 5px 8px;
    border: 1px solid #b0c4de;
    border-radius: 4px;
    background: #fafcff;
    color: #333;
    font-size: 13px;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus { border: 1px solid #1565c0; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #fafcff;
    color: #333;
    border: 1px solid #b0c4de; border-radius: 4px;
    selection-background-color: #90caf9; selection-color: black;
}
QCheckBox { spacing: 6px; font-size: 13px; color: #333; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 3px;
    border: 1px solid #90a4c4;
}
QCheckBox::indicator:checked { background: #1565c0; border-color: #0d47a1; }

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {
    background: #dce6f5;
    border-top: 1px solid #b0c4de;
    font-size: 12px; color: #555;
}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {
    background: #fafcff;
    color: #333;
    border: 1px solid #b0c4de; border-radius: 4px;
    text-align: center; font-size: 12px; min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0d47a1, stop:1 #42a5f5);
    border-radius: 3px;
}

/* ── Menus & Toolbars ────────────────────────────────────────────── */
QMenuBar { background: #dce6f5; color: #333; border-bottom: 1px solid #b0c4de; font-size: 13px; }
QMenuBar::item:selected { background: #c8d8f0; border-radius: 4px; }
QMenu {
    background: #f0f4fa; color: #333; border: 1px solid #b0c4de;
    border-radius: 4px; padding: 4px;
}
QMenu::item { padding: 6px 24px; border-radius: 3px; }
QMenu::item:selected { background-color: #bbdefb; }
QToolBar {
    background: #dce6f5; border-bottom: 1px solid #b0c4de;
    spacing: 4px; padding: 2px;
}

/* ── Dialogs ─────────────────────────────────────────────────────── */
QDialog {
    background-color: #e8eef7;
    color: #333;
}
QMessageBox {
    background-color: #e8eef7;
    color: #333;
}
QMessageBox QLabel {
    color: #333;
}
"""
)


# ══════════════════════════════════════════════════════════════════════
# Theme registry and application
# ══════════════════════════════════════════════════════════════════════

THEMES: dict[str, str] = {
    "Light": LIGHT_QSS,
    "Dark": DARK_QSS,
    "Blue Accent": BLUE_ACCENT_QSS,
}


def _build_dark_palette() -> QPalette:
    """Build a QPalette for dark mode that covers native dialogs and
    widgets that don't respect QSS alone."""
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#1e1e1e"))
    p.setColor(QPalette.WindowText, QColor("#ddd"))
    p.setColor(QPalette.Base, QColor("#1e1e1e"))
    p.setColor(QPalette.AlternateBase, QColor("#262626"))
    p.setColor(QPalette.ToolTipBase, QColor("#f5f5f5"))
    p.setColor(QPalette.ToolTipText, QColor("#212121"))
    p.setColor(QPalette.Text, QColor("#ddd"))
    p.setColor(QPalette.Button, QColor("#333"))
    p.setColor(QPalette.ButtonText, QColor("#ddd"))
    p.setColor(QPalette.BrightText, QColor("#fff"))
    p.setColor(QPalette.Link, QColor("#64b5f6"))
    p.setColor(QPalette.Highlight, QColor("#1565c0"))
    p.setColor(QPalette.HighlightedText, QColor("#fff"))
    p.setColor(QPalette.PlaceholderText, QColor("#888"))
    # Disabled colours
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#666"))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#666"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#666"))
    return p

def _build_light_palette() -> QPalette:
    """Explicit light palette to override any stuck dark palette caching."""
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#fafafa"))
    p.setColor(QPalette.WindowText, QColor("#333333"))
    p.setColor(QPalette.Base, QColor("#ffffff"))
    p.setColor(QPalette.AlternateBase, QColor("#f5f5f5"))
    p.setColor(QPalette.ToolTipBase, QColor("#333333"))
    p.setColor(QPalette.ToolTipText, QColor("#eeeeee"))
    p.setColor(QPalette.Text, QColor("#333333"))
    p.setColor(QPalette.Button, QColor("#f5f5f5"))
    p.setColor(QPalette.ButtonText, QColor("#333333"))
    p.setColor(QPalette.BrightText, QColor("#ffffff"))
    p.setColor(QPalette.Link, QColor("#1976d2"))
    p.setColor(QPalette.Highlight, QColor("#1976d2"))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.PlaceholderText, QColor("#888888"))
    # Disabled colours
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#aaaaaa"))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#aaaaaa"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#aaaaaa"))
    return p

def _build_blue_palette() -> QPalette:
    """Explicit blue accent palette to override any stuck dark palette caching."""
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#e8eef7"))
    p.setColor(QPalette.WindowText, QColor("#333333"))
    p.setColor(QPalette.Base, QColor("#fafcff"))
    p.setColor(QPalette.AlternateBase, QColor("#dce6f5"))
    p.setColor(QPalette.ToolTipBase, QColor("#333333"))
    p.setColor(QPalette.ToolTipText, QColor("#eeeeee"))
    p.setColor(QPalette.Text, QColor("#333333"))
    p.setColor(QPalette.Button, QColor("#dce6f5"))
    p.setColor(QPalette.ButtonText, QColor("#333333"))
    p.setColor(QPalette.BrightText, QColor("#ffffff"))
    p.setColor(QPalette.Link, QColor("#1565c0"))
    p.setColor(QPalette.Highlight, QColor("#1565c0"))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.PlaceholderText, QColor("#888888"))
    # Disabled colours
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#aaaaaa"))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#aaaaaa"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#aaaaaa"))
    return p

_active_theme: str = "Light"


def apply_theme(app: QApplication, name: str) -> None:
    """Apply a named theme to the application.

    Sets the QSS stylesheet and explicitly overwrites the QPalette
    for every theme so that native dialogs don't cache stale colors.
    """
    global _active_theme
    _active_theme = name
    qss = THEMES.get(name, LIGHT_QSS)
    app.setStyleSheet(qss)

    if name == "Dark":
        app.setPalette(_build_dark_palette())
    elif name == "Blue Accent":
        app.setPalette(_build_blue_palette())
    else:
        app.setPalette(_build_light_palette())


# ══════════════════════════════════════════════════════════════════════
# Theme color dictionaries (for theme-aware HTML/widgets)
# ══════════════════════════════════════════════════════════════════════

_THEME_COLORS: dict[str, dict[str, str]] = {
    "Light": {
        "bg": "#fafafa", "fg": "#333333", "accent": "#1976d2",
        "border": "#d0d0d0", "card_bg": "#ffffff", "muted": "#888888",
        "card_border": "#e0e0e0", "success": "#2e7d32", "error": "#c62828",
        "warning": "#ef6c00", "hover": "#e3f2fd", "surface": "#f5f5f5",
    },
    "Dark": {
        "bg": "#1e1e1e", "fg": "#dddddd", "accent": "#64b5f6",
        "border": "#444444", "card_bg": "#2d2d2d", "muted": "#999999",
        "card_border": "#3a3a3a", "success": "#66bb6a", "error": "#ef5350",
        "warning": "#ffa726", "hover": "#2a3a4a", "surface": "#262626",
    },
    "Blue Accent": {
        "bg": "#e8eef7", "fg": "#333333", "accent": "#1565c0",
        "border": "#b0c4de", "card_bg": "#f0f4fa", "muted": "#888888",
        "card_border": "#c5cfe0", "success": "#2e7d32", "error": "#c62828",
        "warning": "#ef6c00", "hover": "#bbdefb", "surface": "#dce6f5",
    },
}


def get_theme_colors(name: str = "Light") -> dict[str, str]:
    """Return a color dict for the given theme name.

    Keys: bg, fg, accent, border, card_bg, muted, card_border,
    success, error, warning, hover, surface.
    """
    return _THEME_COLORS.get(name, _THEME_COLORS["Light"])


def current_theme_name() -> str:
    """Return the currently-active theme name."""
    return _active_theme


# ══════════════════════════════════════════════════════════════════════
# StatusBadge – reusable rounded-pill status indicator
# ══════════════════════════════════════════════════════════════════════

class StatusBadge(QLabel):
    """Small rounded-pill label for status indicators.

    Usage::

        badge = StatusBadge()
        badge.set_status("running")          # green pill
        badge.set_status("stopped")          # red pill
        badge.set_status("paused")           # orange pill
        badge.set_status("connected")        # green pill
        badge.set_status("disconnected")     # red pill
        badge.set_status("idle", "#757575")  # custom color
    """

    _PRESETS: dict[str, tuple[str, str]] = {
        "running":      ("\u25cf Running",       STATUS_GREEN),
        "connected":    ("\u25cf Connected",      STATUS_GREEN),
        "active":       ("\u25cf Active",         STATUS_GREEN),
        "started":      ("\u25cf Started",        STATUS_GREEN),
        "paused":       ("\u23f8 Paused",         STATUS_ORANGE),
        "starting":     ("\u25cb Starting\u2026", STATUS_ORANGE),
        "stopped":      ("\u25cf Stopped",        STATUS_RED),
        "disconnected": ("\u25cf Disconnected",   STATUS_RED),
        "error":        ("\u25cf Error",          STATUS_RED),
        "idle":         ("\u25cb Idle",           STATUS_GRAY),
        "completed":    ("\u2713 Completed",      STATUS_GREEN),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self._apply_style(STATUS_GRAY)
        self.setText("\u25cb Idle")

    def set_status(self, status: str, color: str | None = None) -> None:
        """Set the badge to a preset or custom status."""
        status_lower = status.lower()
        if status_lower in self._PRESETS:
            label, preset_color = self._PRESETS[status_lower]
            self.setText(label)
            self._apply_style(color or preset_color)
        else:
            self.setText(status)
            self._apply_style(color or STATUS_GRAY)

    def _apply_style(self, bg_color: str) -> None:
        self.setStyleSheet(
            f"background-color: {bg_color};"
            f"color: white;"
            f"border-radius: 10px;"
            f"padding: 3px 12px;"
            f"font-size: 11px;"
            f"font-weight: bold;"
        )


# ══════════════════════════════════════════════════════════════════════
# StatCard – animated stat display for dashboards
# ══════════════════════════════════════════════════════════════════════

class StatCard(QFrame):
    """Stylish stat card with a large number and small label.

    Usage::

        card = StatCard("Total Prompts", accent_color="#1976d2")
        card.set_value(142)       # animates count-up
        card.set_value("1.2M")    # sets text directly
    """

    def __init__(self, label: str, accent_color: str = "#1976d2",
                 parent=None):
        super().__init__(parent)
        self._accent = accent_color
        self._display_value = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)

        self._value_label = QLabel("0")
        value_font = QFont()
        value_font.setPointSize(22)
        value_font.setBold(True)
        self._value_label.setFont(value_font)
        self._value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._value_label)

        self._desc_label = QLabel(label)
        desc_font = QFont()
        desc_font.setPointSize(10)
        self._desc_label.setFont(desc_font)
        self._desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._desc_label)

        self._refresh_style()

    def _refresh_style(self) -> None:
        colors = get_theme_colors(current_theme_name())
        self.setStyleSheet(
            f"StatCard {{"
            f"  background-color: {colors['card_bg']};"
            f"  border: 1px solid {colors['card_border']};"
            f"  border-left: 4px solid {self._accent};"
            f"  border-radius: 8px;"
            f"}}"
        )
        self._desc_label.setStyleSheet(f"color: {colors['muted']};")

    # -- Animated count-up via QPropertyAnimation --

    def _get_display_value(self) -> int:
        return self._display_value

    def _set_display_value(self, val: int) -> None:
        self._display_value = val
        self._value_label.setText(f"{val:,}")

    displayValue = Property(int, _get_display_value, _set_display_value)

    def set_value(self, value, animate: bool = True) -> None:
        """Set the card's displayed value.

        If *value* is an ``int`` and *animate* is True, a smooth
        count-up animation plays.  Otherwise the text is set directly.
        """
        self._refresh_style()
        if isinstance(value, int) and animate:
            anim = QPropertyAnimation(self, b"displayValue", self)
            anim.setDuration(600)
            anim.setStartValue(self._display_value)
            anim.setEndValue(value)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
        elif isinstance(value, int):
            self._display_value = value
            self._value_label.setText(f"{value:,}")
        else:
            self._value_label.setText(str(value))


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\__init__.py

"""PySide6 GUI for LLM Buddy."""


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\analytics_panel.py

"""Analytics dashboard panel for the LLM Buddy Qt GUI.

PySide6 port of the tkinter ``AnalyticsMixin``.  Provides date-range
filtering, summary statistics, and a 2x2 chart grid (bar, pie, line,
timeline) powered by QtCharts.
"""

import logging
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Slot, QDateTime
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QDateEdit,
)

from llm_buddy.qt.theme import (
    CHART_PALETTE, EVENT_COLOURS,
    StatCard, current_theme_name,
)

# Analytics data service --------------------------------------------------
try:
    from llm_buddy.services.analytics_service import (
        compute_analytics_data,
        parse_date,
        fmt_tokens,
    )
except ImportError:  # pragma: no cover – inline fallback
    from collections import Counter
    from typing import Any, Dict, List, Optional

    def _count_tokens_fb(text: str) -> int:
        return len(text) // 4 if text else 0

    def compute_analytics_data(
        prompts, start_date=None, end_date=None,
    ) -> Dict[str, Any]:
        filtered = list(prompts)
        if start_date:
            filtered = [p for p in filtered if p.timestamp >= start_date]
        if end_date:
            filtered = [p for p in filtered if p.timestamp <= end_date]
        date_ctr: Counter = Counter()
        for p in filtered:
            date_ctr[p.timestamp.strftime("%Y-%m-%d")] += 1
        sorted_dates = sorted(date_ctr.keys())
        prompts_by_date = [(d, date_ctr[d]) for d in sorted_dates]
        llm_ctr: Counter = Counter()
        for p in filtered:
            llm_ctr[p.llm_used] += 1
        llm_distribution = list(llm_ctr.most_common())
        token_day: Counter = Counter()
        total_tokens = 0
        for p in filtered:
            tok = _count_tokens_fb(p.prompt_text)
            tok += _count_tokens_fb(getattr(p, "response_text", "") or "")
            total_tokens += tok
            token_day[p.timestamp.strftime("%Y-%m-%d")] += tok
        sorted_tok = sorted(token_day.keys())
        tokens_by_date = [(d, token_day[d]) for d in sorted_tok]
        timeline_events: List[Dict[str, Any]] = []
        for p in filtered:
            label = p.description or p.llm_used or "Prompt"
            if len(label) > 50:
                label = label[:47] + "\u2026"
            timeline_events.append(
                {"time": p.timestamp, "type": "prompt", "label": label}
            )
        timeline_events.sort(key=lambda e: e["time"])
        unique_dates = set(p.timestamp.date() for p in filtered)
        unique_llms = len(set(p.llm_used for p in filtered))
        return {
            "prompts_by_date": prompts_by_date,
            "llm_distribution": llm_distribution,
            "tokens_by_date": tokens_by_date,
            "timeline_events": timeline_events,
            "total_prompts": len(filtered),
            "total_tokens": total_tokens,
            "unique_llms": unique_llms,
            "active_days": len(unique_dates),
            "start_date": start_date,
            "end_date": end_date,
        }

    def parse_date(s: str):
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return None

    def fmt_tokens(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n:,.0f}"
        return str(n)

# QtCharts – optional dependency -----------------------------------------
_CHARTS_AVAILABLE = False
try:
    from PySide6.QtCharts import (
        QChart,
        QChartView,
        QBarSeries,
        QBarSet,
        QBarCategoryAxis,
        QValueAxis,
        QPieSeries,
        QLineSeries,
        QDateTimeAxis,
        QScatterSeries,
    )

    _CHARTS_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)



class AnalyticsPanel(QWidget):
    """Analytics dashboard with date filters, summary stats, and charts.

    Parameters
    ----------
    main_window : MainWindow
        Back-reference used to access ``prompt_database`` and ``log()``.
    parent : QWidget | None
        Parent widget.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._cache = None
        self._use_all_time = True

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        filter_group = QGroupBox("Date Range")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("From:"))
        self._from_edit = QDateEdit()
        self._from_edit.setCalendarPopup(True)
        self._from_edit.setDisplayFormat("yyyy-MM-dd")
        self._from_edit.setDate(QDateTime.currentDateTime().addDays(-30).date())
        self._from_edit.setMaximumWidth(140)
        filter_layout.addWidget(self._from_edit)

        filter_layout.addWidget(QLabel("To:"))
        self._to_edit = QDateEdit()
        self._to_edit.setCalendarPopup(True)
        self._to_edit.setDisplayFormat("yyyy-MM-dd")
        self._to_edit.setDate(QDateTime.currentDateTime().date())
        self._to_edit.setMaximumWidth(140)
        filter_layout.addWidget(self._to_edit)

        btn_all = QPushButton("All Time")
        btn_all.clicked.connect(self._all_time)
        filter_layout.addWidget(btn_all)

        btn_7 = QPushButton("Last 7 Days")
        btn_7.clicked.connect(self._last_7)
        filter_layout.addWidget(btn_7)

        btn_30 = QPushButton("Last 30 Days")
        btn_30.clicked.connect(self._last_30)
        filter_layout.addWidget(btn_30)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setProperty("class", "primary")
        btn_refresh.clicked.connect(self.refresh)
        filter_layout.addWidget(btn_refresh)

        filter_layout.addStretch()
        root.addWidget(filter_group)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        self._card_total = StatCard("Total Prompts", "#1976d2")
        stats_layout.addWidget(self._card_total)

        self._card_tokens = StatCard("Total Tokens", "#e15759")
        stats_layout.addWidget(self._card_tokens)

        self._card_llms = StatCard("Unique LLMs", "#59a14f")
        stats_layout.addWidget(self._card_llms)

        self._card_days = StatCard("Active Days", "#f28e2b")
        stats_layout.addWidget(self._card_days)

        root.addLayout(stats_layout)

        if _CHARTS_AVAILABLE:
            chart_grid = QGridLayout()
            chart_grid.setContentsMargins(0, 0, 0, 0)

            self._cv_bar = self._make_chart_view("Prompts per Day")
            chart_grid.addWidget(self._cv_bar, 0, 0)

            self._cv_pie = self._make_chart_view("LLM Distribution")
            chart_grid.addWidget(self._cv_pie, 0, 1)

            self._cv_line = self._make_chart_view("Token Usage Over Time")
            chart_grid.addWidget(self._cv_line, 1, 0)

            self._cv_timeline = self._make_chart_view("Activity Timeline")
            chart_grid.addWidget(self._cv_timeline, 1, 1)

            root.addLayout(chart_grid, stretch=1)
        else:
            fallback = QLabel(
                "Charts unavailable \u2014 install PySide6-QtCharts to "
                "enable the analytics charts."
            )
            fallback.setAlignment(Qt.AlignCenter)
            root.addWidget(fallback, stretch=1)

    @staticmethod
    def _make_chart_view(title: str) -> "QChartView":
        """Create a QChartView with an empty titled chart."""
        chart = QChart()
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        return view

    @staticmethod
    def _style_chart(chart: "QChart") -> None:
        """Apply current-theme styling to a chart."""
        theme_name = current_theme_name()
        if theme_name == "Dark":
            chart.setTheme(QChart.ChartThemeDark)
            chart.setBackgroundBrush(QColor("#1e1e1e"))
            chart.setTitleBrush(QColor("#ddd"))
        elif theme_name == "Blue Accent":
            chart.setTheme(QChart.ChartThemeBlueIcy)
            chart.setBackgroundBrush(QColor("#f0f4fa"))
            chart.setTitleBrush(QColor("#333"))
        else:
            chart.setTheme(QChart.ChartThemeLight)
            chart.setBackgroundBrush(QColor("#ffffff"))
            chart.setTitleBrush(QColor("#333"))
        chart.setBackgroundRoundness(8)

    def _log(self, msg: str) -> None:
        if hasattr(self._mw, "log"):
            self._mw.log(msg)

    @Slot()
    def _all_time(self) -> None:
        self._use_all_time = True
        self.refresh()

    @Slot()
    def _last_7(self) -> None:
        self._use_all_time = False
        self._set_range(7)

    @Slot()
    def _last_30(self) -> None:
        self._use_all_time = False
        self._set_range(30)

    def _set_range(self, days: int) -> None:
        from PySide6.QtCore import QDate
        end = QDate.currentDate()
        start = end.addDays(-days)
        self._from_edit.setDate(start)
        self._to_edit.setDate(end)
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        """Recompute analytics data and repaint all charts."""
        if getattr(self, "_use_all_time", False):
            start_date = None
            end_date = None
        else:
            start_date = parse_date(
                self._from_edit.date().toString("yyyy-MM-dd"))
            end_date = parse_date(
                self._to_edit.date().toString("yyyy-MM-dd"))

        prompts = []
        try:
            prompts = list(self._mw.prompt_database.prompts)
        except Exception:
            self._log("Analytics: could not read prompt database.")

        self._cache = compute_analytics_data(
            prompts, start_date, end_date,
            db=getattr(self._mw, "prompt_database", None))
        self._update_stats()
        if _CHARTS_AVAILABLE:
            self._draw_bar_chart()
            self._draw_pie_chart()
            self._draw_line_chart()
            self._draw_timeline()

    def _update_stats(self) -> None:
        d = self._cache
        if d is None:
            return
        self._card_total.set_value(d["total_prompts"])
        self._card_tokens.set_value(fmt_tokens(d["total_tokens"]))
        self._card_llms.set_value(d["unique_llms"])
        self._card_days.set_value(d["active_days"])

    def _draw_bar_chart(self) -> None:
        data = self._cache["prompts_by_date"]  # [(date_str, count), ...]
        chart = QChart()
        chart.setTitle("Prompts per Day")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        bar_set = QBarSet("Prompts")
        bar_set.setColor(QColor(CHART_PALETTE[0]))
        categories = []
        for date_str, count in data:
            bar_set.append(count)
            categories.append(date_str)

        series = QBarSeries()
        series.append(bar_set)
        chart.addSeries(series)

        # Category axis (X)
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        if len(categories) > 15:
            axis_x.setLabelsAngle(-45)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Value axis (Y)
        axis_y = QValueAxis()
        axis_y.setTitleText("Count")
        axis_y.setLabelFormat("%d")
        max_val = max((c for _, c in data), default=1)
        axis_y.setRange(0, max_val + 1)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(False)
        self._style_chart(chart)
        self._cv_bar.setChart(chart)

    def _draw_pie_chart(self) -> None:
        data = self._cache["llm_distribution"]  # [(name, count), ...]
        chart = QChart()
        chart.setTitle("LLM Distribution")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        series = QPieSeries()
        for i, (name, count) in enumerate(data):
            sl = series.append(name, count)
            colour = QColor(CHART_PALETTE[i % len(CHART_PALETTE)])
            sl.setColor(colour)
            sl.setBorderColor(colour.darker(120))
            # Explode the largest slice slightly
            if i == 0 and len(data) > 1:
                sl.setExploded(True)
                sl.setExplodeDistanceFactor(0.04)
            sl.setLabelVisible(True)
            pct = count / max(sum(c for _, c in data), 1) * 100
            sl.setLabel(f"{name} ({pct:.0f}%)")

        chart.addSeries(series)
        chart.legend().setAlignment(Qt.AlignRight)
        self._style_chart(chart)
        self._cv_pie.setChart(chart)

    def _draw_line_chart(self) -> None:
        data = self._cache["tokens_by_date"]  # [(date_str, tokens), ...]
        chart = QChart()
        chart.setTitle("Token Usage Over Time")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        series = QLineSeries()
        series.setName("Tokens")
        series.setColor(QColor(CHART_PALETTE[2]))

        min_ms = None
        max_ms = None
        max_tokens = 0
        for date_str, tokens in data:
            dt = QDateTime.fromString(date_str, "yyyy-MM-dd")
            ms = dt.toMSecsSinceEpoch()
            series.append(ms, tokens)
            if min_ms is None or ms < min_ms:
                min_ms = ms
            if max_ms is None or ms > max_ms:
                max_ms = ms
            if tokens > max_tokens:
                max_tokens = tokens

        chart.addSeries(series)

        # Date axis (X)
        axis_x = QDateTimeAxis()
        axis_x.setFormat("yyyy-MM-dd")
        axis_x.setTitleText("Date")
        if min_ms is not None and max_ms is not None:
            axis_x.setRange(
                QDateTime.fromMSecsSinceEpoch(min_ms),
                QDateTime.fromMSecsSinceEpoch(max_ms),
            )
        if len(data) > 15:
            axis_x.setLabelsAngle(-45)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Value axis (Y)
        axis_y = QValueAxis()
        axis_y.setTitleText("Tokens")
        axis_y.setLabelFormat("%d")
        axis_y.setRange(0, max_tokens * 1.1 if max_tokens else 1)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(False)
        self._style_chart(chart)
        self._cv_line.setChart(chart)

    def _draw_timeline(self) -> None:
        events = self._cache["timeline_events"]
        chart = QChart()
        chart.setTitle("Activity Timeline")
        chart.setAnimationOptions(QChart.NoAnimation)

        # Group events by type so each gets its own coloured series
        type_events: dict[str, list] = {}
        for ev in events:
            t = ev["type"]
            type_events.setdefault(t, []).append(ev)

        min_ms = None
        max_ms = None

        # Y position: stack events per type for visual separation
        type_y = {t: idx + 1 for idx, t in enumerate(sorted(type_events))}
        max_y = len(type_y) + 1

        for event_type, evts in type_events.items():
            colour_hex = EVENT_COLOURS.get(
                event_type, CHART_PALETTE[0]
            )
            colour = QColor(colour_hex)
            y = type_y[event_type]

            scatter = QScatterSeries()
            scatter.setName(event_type.replace("_", " ").title())
            scatter.setColor(colour)
            scatter.setMarkerSize(10)
            scatter.setBorderColor(colour.darker(120))

            for ev in evts:
                dt = QDateTime(
                    ev["time"].year,
                    ev["time"].month,
                    ev["time"].day,
                    ev["time"].hour,
                    ev["time"].minute,
                    ev["time"].second,
                )
                ms = dt.toMSecsSinceEpoch()
                scatter.append(ms, y)
                if min_ms is None or ms < min_ms:
                    min_ms = ms
                if max_ms is None or ms > max_ms:
                    max_ms = ms

            chart.addSeries(scatter)

        # Date axis (X)
        axis_x = QDateTimeAxis()
        axis_x.setFormat("yyyy-MM-dd")
        axis_x.setTitleText("Date")
        if min_ms is not None and max_ms is not None:
            # Add a small padding so edge points aren't clipped
            pad = max((max_ms - min_ms) * 0.02, 3_600_000)
            axis_x.setRange(
                QDateTime.fromMSecsSinceEpoch(int(min_ms - pad)),
                QDateTime.fromMSecsSinceEpoch(int(max_ms + pad)),
            )
        if len(events) > 30:
            axis_x.setLabelsAngle(-45)
        chart.addAxis(axis_x, Qt.AlignBottom)

        # Value axis (Y) – one tick per event type
        axis_y = QValueAxis()
        axis_y.setTitleText("Event Type")
        axis_y.setRange(0, max_y)
        axis_y.setTickCount(max_y + 1)
        axis_y.setLabelFormat("%d")
        chart.addAxis(axis_y, Qt.AlignLeft)

        # Attach axes to all series
        for s in chart.series():
            s.attachAxis(axis_x)
            s.attachAxis(axis_y)

        chart.legend().setAlignment(Qt.AlignBottom)
        self._style_chart(chart)
        self._cv_timeline.setChart(chart)


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\backup_panel.py

"""Auto-Backup panel – monitor files and trigger automatic backups."""

import json
import os
import fnmatch
from datetime import datetime

from PySide6.QtCore import Qt, Slot, QTimer, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QSpinBox, QPushButton, QCheckBox,
    QTreeView, QGroupBox, QMessageBox, QFileDialog,
    QHeaderView, QSplitter,
)

from llm_buddy.core.backup import AutoBackupConfig, EnhancedFileChangeHandler
from llm_buddy.core.tokens import build_combined_text, count_tokens, count_tokens_in_file
from llm_buddy.paths import get_data_dir, get_backup_dir

try:
    from watchdog.observers import Observer
except ImportError:
    Observer = None


class BackupPanel(QWidget):
    """Auto-Backup management panel.

    Sub-tabs: Files & Folders | Settings | History.
    """

    # Emitted from watchdog background thread; Qt queues delivery
    # to the main thread automatically (queued connection).
    _backup_requested = Signal(int, object)  # (delay_ms, callback)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._config = AutoBackupConfig()
        self._observer = None

        # Debounced backup scheduling via Qt Signal (thread-safe)
        self._debounce_timer = None
        self._backup_requested.connect(self._on_backup_requested)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        top_row = QHBoxLayout()
        self._chk_enabled = QCheckBox("Enable Auto-Backup")
        self._chk_enabled.toggled.connect(self._toggle)
        top_row.addWidget(self._chk_enabled)
        top_row.addSpacing(20)
        top_row.addWidget(QLabel("Status:"))
        self._status_label = QLabel("Inactive")
        self._status_label.setStyleSheet("color: red; font-weight: bold;")
        top_row.addWidget(self._status_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)

        tabs.addTab(self._build_files_tab(), "Files && Folders")
        tabs.addTab(self._build_settings_tab(), "Settings")
        tabs.addTab(self._build_history_tab(), "History")

        bot = QHBoxLayout()
        bot.addStretch()
        btn_refresh = QPushButton("Refresh Status")
        btn_refresh.clicked.connect(self._refresh_status)
        bot.addWidget(btn_refresh)
        btn_force = QPushButton("Force Backup Now")
        btn_force.clicked.connect(self._force_backup)
        bot.addWidget(btn_force)
        layout.addLayout(bot)

        self._load_settings()

    def _build_files_tab(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)

        # Monitored files
        file_group = QGroupBox("Monitored Files")
        fl = QVBoxLayout(file_group)
        self._files_model = QStandardItemModel()
        self._files_model.setHorizontalHeaderLabels(["File Path"])
        self._files_tree = QTreeView()
        self._files_tree.setModel(self._files_model)
        self._files_tree.setRootIsDecorated(False)
        self._files_tree.setSelectionMode(QTreeView.ExtendedSelection)
        self._files_tree.header().setSectionResizeMode(
            QHeaderView.Interactive)
        self._files_tree.header().setStretchLastSection(True)
        fl.addWidget(self._files_tree)
        fbtn = QHBoxLayout()
        b1 = QPushButton("Add Files")
        b1.clicked.connect(self._add_files)
        fbtn.addWidget(b1)
        b2 = QPushButton("Remove Selected")
        b2.clicked.connect(self._remove_files)
        fbtn.addWidget(b2)
        b3 = QPushButton("Add Current Selection")
        b3.clicked.connect(self._add_current_selection)
        fbtn.addWidget(b3)
        fl.addLayout(fbtn)
        lay.addWidget(file_group)

        # Monitored folders
        folder_group = QGroupBox("Monitored Folders")
        dl = QVBoxLayout(folder_group)
        self._folders_model = QStandardItemModel()
        self._folders_model.setHorizontalHeaderLabels(["Folder Path"])
        self._folders_tree = QTreeView()
        self._folders_tree.setModel(self._folders_model)
        self._folders_tree.setRootIsDecorated(False)
        self._folders_tree.setSelectionMode(QTreeView.ExtendedSelection)
        self._folders_tree.header().setSectionResizeMode(
            QHeaderView.Interactive)
        self._folders_tree.header().setStretchLastSection(True)
        dl.addWidget(self._folders_tree)
        dbtn = QHBoxLayout()
        d1 = QPushButton("Add Folder")
        d1.clicked.connect(self._add_folder)
        dbtn.addWidget(d1)
        d2 = QPushButton("Remove Selected")
        d2.clicked.connect(self._remove_folders)
        dbtn.addWidget(d2)
        dl.addLayout(dbtn)
        lay.addWidget(folder_group)
        return w

    def _build_settings_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)

        def _row(label_text, widget):
            r = QHBoxLayout()
            r.addWidget(QLabel(label_text))
            r.addWidget(widget)
            r.addStretch()
            lay.addLayout(r)

        self._ignored_edit = QLineEdit()
        _row("Ignored File Patterns:", self._ignored_edit)

        self._min_change_spin = QSpinBox()
        self._min_change_spin.setRange(1, 10000)
        self._min_change_spin.setValue(self._config.min_token_change)
        _row("Min Token Change to Trigger Backup:", self._min_change_spin)

        self._cooldown_spin = QSpinBox()
        self._cooldown_spin.setRange(1, 60)
        self._cooldown_spin.setValue(self._config.cooldown_minutes)
        _row("Cooldown Between Backups (minutes):", self._cooldown_spin)

        self._max_backups_spin = QSpinBox()
        self._max_backups_spin.setRange(1, 500)
        self._max_backups_spin.setValue(self._config.max_backups)
        _row("Maximum Auto-Backups to Keep:", self._max_backups_spin)

        self._chk_notify = QCheckBox("Show Notifications When Backup Occurs")
        self._chk_notify.setChecked(self._config.notification_enabled)
        lay.addWidget(self._chk_notify)

        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self._save_settings)
        lay.addWidget(btn_save)
        lay.addStretch()
        return w

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._hist_model = QStandardItemModel()
        self._hist_model.setHorizontalHeaderLabels(
            ["Date & Time", "Files Changed", "Token Changes", "Has Prompt"])
        self._hist_tree = QTreeView()
        self._hist_tree.setModel(self._hist_model)
        self._hist_tree.setRootIsDecorated(False)
        self._hist_tree.setAlternatingRowColors(True)
        hist_header = self._hist_tree.header()
        hist_header.setSectionResizeMode(QHeaderView.Interactive)
        hist_header.setStretchLastSection(True)
        hist_header.resizeSection(0, 160)
        lay.addWidget(self._hist_tree)
        return w

    @Slot(bool)
    def _toggle(self, enabled: bool) -> None:
        if enabled:
            self._start_monitoring()
        else:
            self._stop_monitoring()
        self._config.enabled = enabled
        self._save_settings()
        self._refresh_status()

    def _start_monitoring(self) -> None:
        if self._observer is not None:
            return
        if Observer is None:
            self._mw.log("watchdog not installed – cannot monitor files")
            QMessageBox.critical(
                self, "Error",
                "The 'watchdog' package is required for auto-backup.\n"
                "Install with: pip install watchdog")
            self._chk_enabled.setChecked(False)
            return
        try:
            handler = EnhancedFileChangeHandler(
                self._config,
                log_callback=self._mw.log,
                schedule_callback=self._schedule_on_main,
                trigger_backup_callback=self._trigger_backup,
                prompt_database=self._mw.prompt_database,
            )
            self._observer = Observer()
            for folder in self._config.monitor_folders:
                if os.path.isdir(folder):
                    self._observer.schedule(handler, folder, recursive=True)
                    self._mw.log(f"Monitoring folder: {folder}")
            for fp in self._config.monitor_files:
                if os.path.isfile(fp):
                    parent = os.path.dirname(fp)
                    if parent:
                        self._observer.schedule(
                            handler, parent, recursive=False)
                        self._mw.log(f"Monitoring file: {fp}")
            self._observer.start()
            self._mw.log("Auto-backup monitoring started")
        except Exception as e:
            self._mw.log(f"Error starting monitoring: {e}")
            QMessageBox.critical(self, "Error",
                                 f"Failed to start monitoring:\n{e}")
            self._chk_enabled.setChecked(False)

    def _stop_monitoring(self) -> None:
        if self._observer is None:
            return
        try:
            self._observer.stop()
            self._observer.join(timeout=5)
        except Exception as e:
            self._mw.log(f"Error stopping monitoring: {e}")
        self._observer = None
        self._mw.log("Auto-backup monitoring stopped")

    def _schedule_on_main(self, ms, fn, *args):
        """Called by watchdog from a background thread.

        Emits a Qt Signal which is delivered on the main thread,
        where debouncing is handled with a cancellable QTimer.
        """
        self._backup_requested.emit(ms, lambda: fn(*args))

    @Slot(int, object)
    def _on_backup_requested(self, delay_ms, fn):
        """Debounce backup requests on the main thread.

        Each new call cancels any pending timer, resetting the debounce
        window.  This coalesces rapid file changes into a single backup.
        """
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
            self._debounce_timer.deleteLater()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(fn)
        timer.start(delay_ms)
        self._debounce_timer = timer

    def _restart_if_active(self) -> None:
        if self._observer:
            self._stop_monitoring()
            self._start_monitoring()

    @Slot()
    def _refresh_status(self) -> None:
        if self._observer and self._observer.is_alive():
            self._status_label.setText("Active")
            self._status_label.setStyleSheet(
                "color: green; font-weight: bold;")
        else:
            self._status_label.setText("Inactive")
            self._status_label.setStyleSheet(
                "color: red; font-weight: bold;")

    @Slot()
    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select File(s) to Monitor", "",
            "All files (*.*)")
        for fp in paths:
            if fp not in self._config.monitor_files:
                self._config.monitor_files.append(fp)
                item = QStandardItem(fp)
                item.setEditable(False)
                item.setToolTip(fp)
                self._files_model.appendRow([item])
                self._mw.log(f"Added {fp} to monitored files")
        self._restart_if_active()

    @Slot()
    def _remove_files(self) -> None:
        indexes = self._files_tree.selectionModel().selectedRows()
        for idx in sorted(indexes, reverse=True):
            fp = self._files_model.item(idx.row(), 0).text()
            if fp in self._config.monitor_files:
                self._config.monitor_files.remove(fp)
            self._files_model.removeRow(idx.row())
            self._mw.log(f"Removed {fp} from monitored files")
        self._restart_if_active()

    @Slot()
    def _add_current_selection(self) -> None:
        for fp, _tok in self._mw.filtered_files:
            if fp not in self._config.monitor_files:
                self._config.monitor_files.append(fp)
                item = QStandardItem(fp)
                item.setEditable(False)
                item.setToolTip(fp)
                self._files_model.appendRow([item])
        for folder in self._mw.folders:
            if folder not in self._config.monitor_folders:
                self._config.monitor_folders.append(folder)
                item = QStandardItem(folder)
                item.setEditable(False)
                item.setToolTip(folder)
                self._folders_model.appendRow([item])
        self._mw.log("Added current selection to monitoring")
        self._restart_if_active()

    @Slot()
    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder to Monitor")
        if folder and folder not in self._config.monitor_folders:
            self._config.monitor_folders.append(folder)
            item = QStandardItem(folder)
            item.setEditable(False)
            item.setToolTip(folder)
            self._folders_model.appendRow([item])
            self._mw.log(f"Added {folder} to monitored folders")
        self._restart_if_active()

    @Slot()
    def _remove_folders(self) -> None:
        indexes = self._folders_tree.selectionModel().selectedRows()
        for idx in sorted(indexes, reverse=True):
            fp = self._folders_model.item(idx.row(), 0).text()
            if fp in self._config.monitor_folders:
                self._config.monitor_folders.remove(fp)
            self._folders_model.removeRow(idx.row())
            self._mw.log(f"Removed {fp} from monitored folders")
        self._restart_if_active()

    @Slot()
    def _save_settings(self) -> None:
        self._config.ignored_patterns = [
            p.strip() for p in self._ignored_edit.text().split(",")
            if p.strip()]
        self._config.min_token_change = self._min_change_spin.value()
        self._config.cooldown_minutes = self._cooldown_spin.value()
        self._config.max_backups = self._max_backups_spin.value()
        self._config.notification_enabled = self._chk_notify.isChecked()
        try:
            with open(os.path.join(get_data_dir(), "auto_backup_settings.json"), "w",
                       encoding="utf-8") as f:
                json.dump(self._config.to_dict(), f, indent=4)
            self._mw.log("Auto-backup settings saved")
            self._restart_if_active()
        except Exception as e:
            self._mw.log(f"Error saving settings: {e}")

    def _load_settings(self) -> None:
        settings_path = os.path.join(get_data_dir(), "auto_backup_settings.json")
        if not os.path.exists(settings_path):
            self._ignored_edit.setText(
                ",".join(self._config.ignored_patterns))
            return
        try:
            with open(settings_path, "r",
                       encoding="utf-8") as f:
                settings = json.load(f)
            self._config.from_dict(settings)

            self._chk_enabled.setChecked(self._config.enabled)
            self._ignored_edit.setText(
                ",".join(self._config.ignored_patterns))
            self._min_change_spin.setValue(self._config.min_token_change)
            self._cooldown_spin.setValue(self._config.cooldown_minutes)
            self._max_backups_spin.setValue(self._config.max_backups)
            self._chk_notify.setChecked(
                self._config.notification_enabled)

            # Populate file/folder trees
            self._files_model.removeRows(
                0, self._files_model.rowCount())
            for fp in self._config.monitor_files:
                item = QStandardItem(fp)
                item.setEditable(False)
                item.setToolTip(fp)
                self._files_model.appendRow([item])
            self._folders_model.removeRows(
                0, self._folders_model.rowCount())
            for fp in self._config.monitor_folders:
                item = QStandardItem(fp)
                item.setEditable(False)
                item.setToolTip(fp)
                self._folders_model.appendRow([item])

            self._mw.log("Auto-backup settings loaded")
            if self._config.enabled:
                self._start_monitoring()
        except Exception as e:
            self._mw.log(f"Error loading settings: {e}")

    def _trigger_backup(self, changed_files) -> bool:
        """Create an auto-backup (called from file watcher)."""
        self._config.last_backup_time = datetime.now()

        active_prompt_info = ""
        if self._mw.prompt_database.active_prompt:
            prompt = self._mw.prompt_database.active_prompt
            for fp, tc in changed_files:
                if fp not in prompt.associated_files:
                    prompt.associated_files.append(fp)
                    prompt.file_changes[fp] = tc
            self._mw.prompt_database.save()
            active_prompt_info = (
                f"\nActive Prompt: "
                f"{prompt.description or 'Untitled'} ({prompt.llm_used})")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_changes = sum(c for _, c in changed_files)
        backup_name = (
            f"auto_backup_{ts}_{len(changed_files)}files_"
            f"{total_changes}tokens.md")

        files_to_backup = [fp for fp, _ in changed_files]
        for fp in self._config.monitor_files:
            if fp not in files_to_backup and os.path.isfile(fp):
                files_to_backup.append(fp)

        header = (
            f"Auto-Backup generated on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Changed files: {len(changed_files)}, "
            f"Total token changes: {total_changes}"
            f"{active_prompt_info}")
        if self._mw.prompt_database.active_prompt:
            header += ("\n\nPrompt Text:\n"
                       + self._mw.prompt_database.active_prompt.prompt_text)

        combined = build_combined_text(
            files_to_backup, header, "End of Auto-Backup")
        total_tokens = count_tokens(combined)

        output_dir = get_backup_dir()
        output_file = os.path.join(output_dir, backup_name)

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(combined)
            self._mw.log(f"Auto-backup created: {output_file}")

            prompt_info = ("Yes" if self._mw.prompt_database.active_prompt
                           else "No")
            # Add to history tree
            row = [
                QStandardItem(ts),
                QStandardItem(str(len(changed_files))),
                QStandardItem(str(total_changes)),
                QStandardItem(prompt_info),
            ]
            for item in row:
                item.setEditable(False)
            self._hist_model.insertRow(0, row)

            self._create_backup_eadr_note(
                backup_name, changed_files, total_tokens)
            self._prune_old()

            if self._config.notification_enabled:
                QMessageBox.information(
                    self, "Auto-Backup Complete",
                    f"Created backup with {len(changed_files)} "
                    f"changed files.\nTotal tokens: {total_tokens:,}")
            return True
        except Exception as e:
            self._mw.log(f"Error creating auto-backup: {e}")
            return False

    @Slot()
    def _force_backup(self) -> None:
        files_to_backup = []
        for fp in self._config.monitor_files:
            if os.path.isfile(fp):
                files_to_backup.append(fp)
        for folder in self._config.monitor_folders:
            if os.path.isdir(folder):
                for root, _, files in os.walk(folder):
                    for fn in files:
                        skip = any(
                            fnmatch.fnmatch(fn, pat)
                            for pat in self._config.ignored_patterns)
                        if not skip:
                            files_to_backup.append(os.path.join(root, fn))
        if not files_to_backup:
            QMessageBox.information(
                self, "No Files",
                "No files to backup. Add files or folders first.")
            return
        changed = [(fp, count_tokens_in_file(fp)) for fp in files_to_backup]
        if self._trigger_backup(changed):
            QMessageBox.information(
                self, "Success", "Manual backup completed successfully.")
        else:
            QMessageBox.critical(
                self, "Error", "Failed to create backup. See log.")

    def _create_backup_eadr_note(self, backup_name, changed_files,
                                  total_tokens):
        project = "Origin"
        if hasattr(self._mw, '_eadr_panel'):
            project = self._mw._eadr_panel.project
        note = (
            f"Auto-Backup Created: {backup_name}\n\n"
            f"Total files: {len(changed_files)}\n"
            f"Total tokens: {total_tokens:,}\n\n")
        if self._mw.prompt_database.active_prompt:
            p = self._mw.prompt_database.active_prompt
            note += (f"Active Prompt: {p.description or 'Untitled'}\n"
                     f"LLM Used: {p.llm_used}\n\n")
        note += "Changed files:\n"
        for fp, tc in changed_files:
            note += f"- {fp} ({tc:+,} tokens)\n"
        note_id = self._mw.prompt_database.add_eadr_note(note, project)
        if note_id >= 0:
            self._mw.log(f"eADR note created for auto-backup")
            if hasattr(self._mw, '_eadr_panel'):
                self._mw._eadr_panel.refresh()

    def _prune_old(self) -> None:
        backup_dir = get_backup_dir()
        if not os.path.exists(backup_dir):
            return
        auto_backups = []
        for fn in os.listdir(backup_dir):
            if fn.startswith("auto_backup_") and fn.endswith(".md"):
                fp = os.path.join(backup_dir, fn)
                auto_backups.append((fp, os.path.getmtime(fp)))
        auto_backups.sort(key=lambda x: x[1], reverse=True)
        for fp, _ in auto_backups[self._config.max_backups:]:
            try:
                os.remove(fp)
                self._mw.log(
                    f"Pruned old backup: {os.path.basename(fp)}")
            except Exception as e:
                self._mw.log(f"Error pruning {fp}: {e}")

    def stop(self) -> None:
        """Stop the observer (call on app close)."""
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
        self._stop_monitoring()


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\capture_widgets.py

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

from llm_buddy.qt.theme import get_theme_colors, current_theme_name

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None


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
        self._status.setStyleSheet(
            f"color: {get_theme_colors(current_theme_name())['error']};")
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

        if getattr(sys, "frozen", False):
            # Frozen mode: run Flask in a daemon thread (QProcess
            # with sys.executable -m ... doesn't work in .exe)
            from llm_buddy.recorders.api_server import app as flask_app
            self._server_thread = threading.Thread(
                target=lambda: flask_app.run(
                    host="127.0.0.1", port=5000, debug=False,
                    use_reloader=False),
                daemon=True,
            )
            self._server_thread.start()
            # Use a sentinel so _stop / _on_finished still work
            self._process = "thread"
            QTimer.singleShot(2000, self._verify_started)
            self._mw.log("Starting extension server on port 5000 (in-process)...")
        else:
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
        self._status.setStyleSheet(
            f"color: {get_theme_colors(current_theme_name())['success']};")
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
        self._status.setStyleSheet(
            f"color: {get_theme_colors(current_theme_name())['error']};")
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
        from llm_buddy.paths import get_extension_dir
        ext_dir = get_extension_dir()
        
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
        self._status.setStyleSheet(
            f"color: {get_theme_colors(current_theme_name())['error']};")
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
            if getattr(sys, "frozen", False):
                # Frozen mode: use the bundled llm-buddy-proxy.exe
                proxy_exe = os.path.join(
                    os.path.dirname(sys.executable),
                    "llm-buddy-proxy.exe")
                if not os.path.exists(proxy_exe):
                    QMessageBox.critical(
                        self, "Proxy Not Found",
                        f"Could not find {proxy_exe}")
                    return
                self._mw.log(f"Using bundled proxy: {proxy_exe}")
                self._mw.log("Launching proxy on port 8080...")
                self._process = QProcess(self)
                self._process.setProgram(proxy_exe)
                self._process.setArguments(["--port", "8080"])
            else:
                addon_path = os.path.join(
                    os.path.dirname(os.path.dirname(
                        os.path.dirname(__file__))),
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
            self._status.setStyleSheet(
                f"color: {get_theme_colors(current_theme_name())['warning']};")
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
            self._status.setStyleSheet(
                f"color: {get_theme_colors(current_theme_name())['success']};")
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
        self._status.setStyleSheet(
            f"color: {get_theme_colors(current_theme_name())['error']};")
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
            self._mw.show_toast("System proxy enabled (127.0.0.1:8080).", "success")
            
        except Exception as e:
            self._mw.log(f"Failed to set system proxy: {e}")

    def _disable_system_proxy(self, silent: bool = False):
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            for entry in ("ProxyServer", "ProxyOverride"):
                try:
                    winreg.DeleteValue(key, entry)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            self._proxy_was_configured = False
            self._mw.log("System proxy disabled")

            if not silent:
                self._mw.show_toast("System proxy disabled.", "info")

        except Exception as e:
            self._mw.log(f"Failed to disable proxy: {e}")

    def ensure_proxy_disabled(self):
        """Safety: disable proxy if we configured it (call on close)."""
        if os.name != "nt" or not self._proxy_was_configured:
            return
        try:
            # silent=True suppresses the QMessageBox during app shutdown.
            self._disable_system_proxy(silent=True)
        except Exception:
            pass

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
        colors = get_theme_colors(current_theme_name())
        if cert_path.exists():
            status_lbl.setText("Certificate found!")
            status_lbl.setStyleSheet(
                f"color: {colors['success']}; font-weight: bold;")
        else:
            status_lbl.setText("Certificate not found yet. Start the proxy once.")
            status_lbl.setStyleSheet(
                f"color: {colors['warning']}; font-weight: bold;")
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

            existing_ids = {p.id for p in self._mw.prompt_database.prompts}
            added = 0
            for row in rows:
                if row["id"] not in existing_ids:
                    cur.execute(
                        "SELECT file_path FROM file_associations "
                        "WHERE prompt_id = ?", (row["id"],))
                    files = [r["file_path"] for r in cur.fetchall()]
                    from llm_buddy.core.database import PromptRecord
                    rec = PromptRecord.from_dict({
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "prompt_text": row["prompt_text"],
                        "response_text": row["response_text"] or "",
                        "description": (row["description"]
                                        or f"Prompt from {row['llm_name']}"),
                        "llm_used": row["llm_name"],
                        "associated_files": files,
                        "source": "Proxy Import",
                    })
                    self._mw.prompt_database.add_prompt(prompt_record=rec)
                    existing_ids.add(rec.id)
                    added += 1

            conn.close()
            if added:
                self._mw.log(f"Imported {added} prompts from SQLite")
                QMessageBox.information(
                    self, "Import", f"Imported {added} prompts.")
            else:
                QMessageBox.information(
                    self, "Import", "No new prompts to import.")
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

@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\compare_panel.py

"""Compare panel – diff any two text-based files or backup entries.

VSCode-style split view: File A on the left, File B on the right,
with inline background-colour diff highlighting and synchronised scrolling.
"""

import difflib
import os

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QTextCharFormat, QTextBlockFormat, QTextCursor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QGroupBox, QFileDialog, QMessageBox, QComboBox, QFrame,
)

from llm_buddy.core.rollback import (
    parse_combined_file, read_file_content,
)
from llm_buddy.qt.theme import get_theme_colors, current_theme_name

_SOURCE_STANDALONE = "Standalone File"
_SOURCE_BACKUP = "File Inside Backup"

# Diff line classification tags
_TAG_EQUAL    = "equal"
_TAG_REPLACE  = "replace"   # changed line (present on both sides)
_TAG_DELETE   = "delete"    # only in A
_TAG_INSERT   = "insert"    # only in B
_TAG_EMPTY    = "empty"     # padding line inserted for alignment


def _build_aligned_diff(
    lines_a: list[str],
    lines_b: list[str],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return *(aligned_a, aligned_b)*.

    Each element is a ``(line_text, tag)`` tuple where *tag* is one of the
    ``_TAG_*`` constants above.  Empty-string padding lines (``_TAG_EMPTY``)
    are inserted so that corresponding changed blocks align vertically.
    """
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
    aligned_a: list[tuple[str, str]] = []
    aligned_b: list[tuple[str, str]] = []

    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == "equal":
            for line in lines_a[i1:i2]:
                aligned_a.append((line, _TAG_EQUAL))
                aligned_b.append((line, _TAG_EQUAL))

        elif opcode == "replace":
            block_a = lines_a[i1:i2]
            block_b = lines_b[j1:j2]
            max_len = max(len(block_a), len(block_b))
            for k in range(max_len):
                a_line = block_a[k] if k < len(block_a) else ""
                b_line = block_b[k] if k < len(block_b) else ""
                aligned_a.append((a_line, _TAG_REPLACE if k < len(block_a) else _TAG_EMPTY))
                aligned_b.append((b_line, _TAG_REPLACE if k < len(block_b) else _TAG_EMPTY))

        elif opcode == "delete":
            for line in lines_a[i1:i2]:
                aligned_a.append((line, _TAG_DELETE))
                aligned_b.append(("", _TAG_EMPTY))

        elif opcode == "insert":
            for line in lines_b[j1:j2]:
                aligned_a.append(("", _TAG_EMPTY))
                aligned_b.append((line, _TAG_INSERT))

    return aligned_a, aligned_b


def _diff_colors(side: str) -> dict[str, QColor]:
    """Return background QColors for each tag on *side* ('a' or 'b').

    Colours adapt to the active theme (dark/light).
    """
    theme = current_theme_name()
    dark = (theme == "Dark")

    if dark:
        # Dark theme – VSCode-like muted colours
        return {
            _TAG_EQUAL:   QColor(0, 0, 0, 0),          # transparent
            _TAG_EMPTY:   QColor(40, 40, 40),
            _TAG_DELETE:  QColor(110, 35, 35),          # dark red
            _TAG_INSERT:  QColor(35, 80, 45),           # dark green
            _TAG_REPLACE: QColor(110, 35, 35) if side == "a" else QColor(35, 80, 45),
        }
    else:
        # Light theme
        return {
            _TAG_EQUAL:   QColor(0, 0, 0, 0),
            _TAG_EMPTY:   QColor(230, 230, 230),
            _TAG_DELETE:  QColor(255, 210, 210),        # light red
            _TAG_INSERT:  QColor(210, 240, 210),        # light green
            _TAG_REPLACE: QColor(255, 210, 210) if side == "a" else QColor(210, 240, 210),
        }


class _DiffPane(QWidget):
    """A labelled, read-only text pane used for one side of the diff view."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        self._header = QLabel(title)
        self._header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._header.setContentsMargins(6, 4, 6, 4)
        self._header.setStyleSheet(
            "font-weight: bold; font-size: 11px;"
            "background: palette(mid); border-bottom: 1px solid palette(dark);"
        )
        layout.addWidget(self._header)

        # Text area
        self._edit = QTextEdit()
        self._edit.setReadOnly(True)
        self._edit.setLineWrapMode(QTextEdit.NoWrap)
        self._edit.setFont(QFont("Courier New", 9))
        self._edit.setStyleSheet("border: none;")
        layout.addWidget(self._edit, stretch=1)

    def set_title(self, title: str) -> None:
        self._edit_title = title
        # Truncate long paths for the header label
        if len(title) > 80:
            title = "…" + title[-77:]
        self._header.setText(title)
        self._header.setToolTip(title)

    def scroll_bar(self):
        return self._edit.verticalScrollBar()

    def h_scroll_bar(self):
        return self._edit.horizontalScrollBar()

    def populate(self, aligned: list[tuple[str, str]], side: str) -> None:
        """Fill the pane with *aligned* ``(text, tag)`` lines and colour them."""
        colors = _diff_colors(side)
        edit = self._edit
        edit.clear()
        cursor = edit.textCursor()
        cursor.beginEditBlock()

        transparent = QColor(0, 0, 0, 0)
        first = True
        for text, tag in aligned:
            if not first:
                cursor.insertBlock()
            first = False

            # Block (background) format
            blk_fmt = QTextBlockFormat()
            bg = colors.get(tag, transparent)
            if bg != transparent:
                blk_fmt.setBackground(bg)
            cursor.setBlockFormat(blk_fmt)

            # Char format – use a slightly dimmer foreground for padding lines
            char_fmt = QTextCharFormat()
            if tag == _TAG_EMPTY:
                char_fmt.setForeground(QColor(100, 100, 100))
            cursor.setCharFormat(char_fmt)
            cursor.insertText(text)

        cursor.endEditBlock()

        # Scroll back to top after populating
        edit.moveCursor(QTextCursor.Start)


class _FilePicker(QWidget):
    """Reusable picker that can load a standalone file or a file from a backup."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._parsed: dict[str, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        grp = QGroupBox(label)
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(4)

        # Row 1: source selector + path + browse
        row1 = QHBoxLayout()

        self._source = QComboBox()
        self._source.addItems([_SOURCE_STANDALONE, _SOURCE_BACKUP])
        self._source.setToolTip(
            "Choose whether this is a standalone file on disk\n"
            "or a specific file extracted from a combined backup")
        self._source.currentIndexChanged.connect(self._on_source_changed)
        row1.addWidget(self._source)

        self._path = QLineEdit()
        self._path.setPlaceholderText("Path to file or backup…")
        row1.addWidget(self._path, stretch=1)

        self._btn_browse = QPushButton("Browse")
        self._btn_browse.setToolTip("Browse for a file or backup on disk")
        self._btn_browse.clicked.connect(self._browse)
        row1.addWidget(self._btn_browse)
        grp_layout.addLayout(row1)

        # Row 2: entry selector (backup mode only)
        row2 = QHBoxLayout()
        self._entry_label = QLabel("Entry:")
        row2.addWidget(self._entry_label)
        self._entry_combo = QComboBox()
        self._entry_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._entry_combo.setMinimumContentsLength(40)
        self._entry_combo.setToolTip(
            "Select which file inside the backup to use for comparison")
        row2.addWidget(self._entry_combo, stretch=1)
        self._btn_load = QPushButton("Load Backup")
        self._btn_load.setToolTip(
            "Parse the backup file and populate the entry list\n"
            "so you can pick a specific file inside it")
        self._btn_load.clicked.connect(self._load_backup)
        row2.addWidget(self._btn_load)
        grp_layout.addLayout(row2)

        self._entry_label.setVisible(False)
        self._entry_combo.setVisible(False)
        self._btn_load.setVisible(False)

        layout.addWidget(grp)

    # -- visibility toggle -------------------------------------------------

    @Slot()
    def _on_source_changed(self, _index: int) -> None:
        is_backup = self._source.currentText() == _SOURCE_BACKUP
        self._entry_label.setVisible(is_backup)
        self._entry_combo.setVisible(is_backup)
        self._btn_load.setVisible(is_backup)

    # -- browse / load -----------------------------------------------------

    @Slot()
    def _browse(self) -> None:
        is_backup = self._source.currentText() == _SOURCE_BACKUP
        caption = "Select Backup File" if is_backup else "Select File"
        filt = ("Markdown files (*.md);;All files (*.*)"
                if is_backup else "All files (*.*)")
        path, _ = QFileDialog.getOpenFileName(self, caption, "", filt)
        if not path:
            return
        self._path.setText(path)
        if is_backup:
            self._load_backup()

    @Slot()
    def _load_backup(self) -> None:
        path = self._path.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Error",
                                "Please select a valid backup file first.")
            return
        parsed = parse_combined_file(path)
        if not parsed:
            QMessageBox.warning(self, "Error",
                                "Could not parse any files from this backup.")
            return
        self._parsed = parsed
        self._entry_combo.clear()
        for fp in parsed:
            self._entry_combo.addItem(fp)

    # -- public helpers ----------------------------------------------------

    def resolve(self):
        """Return *(content, label)* or *(None, error_msg)*."""
        source = self._source.currentText()
        path = self._path.text().strip()
        if not path:
            return None, "No path specified."
        if source == _SOURCE_STANDALONE:
            content, err = read_file_content(path)
            if err:
                return None, err
            return content, path
        else:
            entry = self._entry_combo.currentText()
            if not entry or entry not in self._parsed:
                return None, "Please load the backup and select an entry first."
            label = f"{os.path.basename(path)} \u2192 {entry}"
            return self._parsed[entry], label

    def get_state(self) -> dict:
        return {
            "source_idx":  self._source.currentIndex(),
            "path":        self._path.text(),
            "parsed":      self._parsed.copy(),
            "items":       [self._entry_combo.itemText(i)
                            for i in range(self._entry_combo.count())],
            "entry_idx":   self._entry_combo.currentIndex(),
        }

    def set_state(self, state: dict) -> None:
        self._source.setCurrentIndex(state["source_idx"])
        self._path.setText(state["path"])
        self._parsed = state["parsed"]
        self._entry_combo.clear()
        self._entry_combo.addItems(state["items"])
        if state["entry_idx"] >= 0:
            self._entry_combo.setCurrentIndex(state["entry_idx"])


class _Legend(QWidget):
    """Compact horizontal colour legend for the diff view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(12)
        layout.addStretch()
        self._swatches: list[QLabel] = []
        self._update()

    def _update(self) -> None:
        # Clear existing swatches
        while self._swatches:
            w = self._swatches.pop()
            w.deleteLater()

        dark = current_theme_name() == "Dark"
        entries = [
            ("Removed",  "#6e2323" if dark else "#ffd2d2"),
            ("Added",    "#23503a" if dark else "#d2f0d2"),
            ("Modified", "#6e2323" if dark else "#ffd2d2"),  # shown on left
            ("Padding",  "#282828" if dark else "#e6e6e6"),
        ]
        layout = self.layout()
        for label_text, color in entries:
            swatch = QLabel()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(
                f"background-color: {color}; border: 1px solid palette(mid); border-radius: 2px;")
            txt = QLabel(label_text)
            txt.setStyleSheet("font-size: 10px; color: palette(mid);")
            layout.addWidget(swatch)
            layout.addWidget(txt)
            self._swatches.extend([swatch, txt])
        layout.addStretch()


class ComparePanel(QWidget):
    """VSCode-style split-pane file comparison.

    The top section holds the two file pickers and action buttons.
    The bottom section is a horizontal QSplitter with two diff panes:
    File A (left) and File B (right), highlighting additions/deletions
    with background colours and keeping both panes scrolled in sync.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._sync_scroll = True   # guard against recursive scroll events

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        pickers_row = QHBoxLayout()
        pickers_row.setSpacing(6)
        self._picker_a = _FilePicker("File A  (left)", self)
        self._picker_b = _FilePicker("File B  (right)", self)
        pickers_row.addWidget(self._picker_a)
        pickers_row.addWidget(self._picker_b)
        layout.addLayout(pickers_row)

        action_row = QHBoxLayout()
        action_row.addStretch()

        btn_compare = QPushButton("⟳  Compare")
        btn_compare.setProperty("class", "primary")
        btn_compare.setToolTip("Compute and display the diff between File A and File B")
        btn_compare.clicked.connect(self._compare)
        action_row.addWidget(btn_compare)

        btn_swap = QPushButton("⇄  Swap A ↔ B")
        btn_swap.setToolTip("Swap the two file selections")
        btn_swap.clicked.connect(self._swap)
        action_row.addWidget(btn_swap)

        action_row.addStretch()
        layout.addLayout(action_row)

        self._legend = _Legend(self)
        layout.addWidget(self._legend)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        self._pane_a = _DiffPane("File A", self)
        self._pane_b = _DiffPane("File B", self)

        splitter.addWidget(self._pane_a)
        splitter.addWidget(self._pane_b)
        splitter.setSizes([1, 1])           # equal initial widths
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, stretch=1)

        self._stats = QLabel("")
        self._stats.setStyleSheet("font-size: 10px; color: palette(mid);")
        self._stats.setContentsMargins(4, 0, 4, 0)
        layout.addWidget(self._stats)

        self._pane_a.scroll_bar().valueChanged.connect(self._sync_v_from_a)
        self._pane_b.scroll_bar().valueChanged.connect(self._sync_v_from_b)
        self._pane_a.h_scroll_bar().valueChanged.connect(self._sync_h_from_a)
        self._pane_b.h_scroll_bar().valueChanged.connect(self._sync_h_from_b)

    @Slot(int)
    def _sync_v_from_a(self, value: int) -> None:
        if self._sync_scroll:
            self._sync_scroll = False
            self._pane_b.scroll_bar().setValue(value)
            self._sync_scroll = True

    @Slot(int)
    def _sync_v_from_b(self, value: int) -> None:
        if self._sync_scroll:
            self._sync_scroll = False
            self._pane_a.scroll_bar().setValue(value)
            self._sync_scroll = True

    @Slot(int)
    def _sync_h_from_a(self, value: int) -> None:
        if self._sync_scroll:
            self._sync_scroll = False
            self._pane_b.h_scroll_bar().setValue(value)
            self._sync_scroll = True

    @Slot(int)
    def _sync_h_from_b(self, value: int) -> None:
        if self._sync_scroll:
            self._sync_scroll = False
            self._pane_a.h_scroll_bar().setValue(value)
            self._sync_scroll = True

    # -- compare -----------------------------------------------------------

    @Slot()
    def _compare(self) -> None:
        res_a = self._picker_a.resolve()
        res_b = self._picker_b.resolve()

        if res_a[0] is None:
            QMessageBox.warning(self, "File A Error", res_a[1])
            return
        if res_b[0] is None:
            QMessageBox.warning(self, "File B Error", res_b[1])
            return

        content_a, label_a = res_a
        content_b, label_b = res_b

        lines_a = content_a.splitlines()
        lines_b = content_b.splitlines()

        aligned_a, aligned_b = _build_aligned_diff(lines_a, lines_b)

        self._pane_a.set_title(label_a)
        self._pane_b.set_title(label_b)

        self._pane_a.populate(aligned_a, side="a")
        self._pane_b.populate(aligned_b, side="b")

        # Build summary stats
        n_del     = sum(1 for _, t in aligned_a if t == _TAG_DELETE)
        n_ins     = sum(1 for _, t in aligned_b if t == _TAG_INSERT)
        n_replace = sum(1 for _, t in aligned_a if t == _TAG_REPLACE)
        n_equal   = sum(1 for _, t in aligned_a if t == _TAG_EQUAL)
        total     = len(lines_a) + len(lines_b)

        self._stats.setText(
            f"  Lines: {len(lines_a)} (A)  /  {len(lines_b)} (B)   │   "
            f"  ✕ {n_del} removed   +{n_ins} added   ~ {n_replace} changed   "
            f"= {n_equal} identical"
        )

        self._mw.log(
            f"Compared: {os.path.basename(label_a)}  vs  {os.path.basename(label_b)}  "
            f"[−{n_del}  +{n_ins}  ~{n_replace}]"
        )

    # -- swap --------------------------------------------------------------

    @Slot()
    def _swap(self) -> None:
        state_a = self._picker_a.get_state()
        state_b = self._picker_b.get_state()
        self._picker_a.set_state(state_b)
        self._picker_b.set_state(state_a)

@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\control_panel.py

"""Left-hand control panel for the Qt GUI.

Provides folder/file selection, filter controls, header/footer fields,
combine-scripts action, progress bar, and file/folder tree views.
"""

import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QProgressBar, QTreeView, QFileDialog,
    QMessageBox, QHeaderView,
)

from llm_buddy.core.tokens import (
    build_combined_text, count_tokens,
)
from llm_buddy.services.file_service import (
    scan_folder, filter_files,
    parse_extensions, parse_ignored_folders,
)


class _ScanWorker(QObject):
    """Scans folders in a background QThread."""

    progress = Signal(int, int)  # (current, total)
    file_found = Signal(str)
    finished = Signal(list)  # all found files

    def __init__(self, folders, allowed_ext, ignored):
        super().__init__()
        self._folders = folders
        self._ext = allowed_ext
        self._ignored = ignored

    @Slot()
    def run(self):
        found = []
        total = len(self._folders)
        for i, folder in enumerate(self._folders, 1):
            for path in scan_folder(folder, self._ext, self._ignored):
                if path not in found:
                    found.append(path)
                    self.file_found.emit(path)
            self.progress.emit(i, total)
        self.finished.emit(found)


class ControlPanel(QWidget):
    """Left-side control panel with file/folder management.

    Emits ``files_changed(list)`` when the filtered file list is updated,
    carrying a list of ``(path, tokens)`` tuples.
    """

    files_changed = Signal(list)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window  # reference back for shared state
        self._scan_thread: QThread | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        sel_group = QGroupBox("Selection")
        sel_layout = QHBoxLayout(sel_group)
        btn_folder = QPushButton("Add Folder")
        btn_folder.clicked.connect(self._add_folder)
        sel_layout.addWidget(btn_folder)
        btn_files = QPushButton("Add File(s)")
        btn_files.clicked.connect(self._add_files)
        sel_layout.addWidget(btn_files)
        btn_scan = QPushButton("Scan Folders")
        btn_scan.setProperty("class", "primary")
        btn_scan.clicked.connect(self._scan_folders)
        sel_layout.addWidget(btn_scan)
        layout.addWidget(sel_group)

        filt_group = QGroupBox("Filters")
        filt_layout = QVBoxLayout(filt_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Extensions:"))
        self._ext_entry = QLineEdit(self._mw.allowed_extensions)
        self._ext_entry.setPlaceholderText("e.g. .py,.js,.ts,.md")
        self._ext_entry.setToolTip("Comma-separated file extensions to include")
        row1.addWidget(self._ext_entry, stretch=1)
        filt_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Min Tokens:"))
        self._min_tok_entry = QLineEdit(str(self._mw.min_tokens))
        self._min_tok_entry.setMaximumWidth(80)
        self._min_tok_entry.setPlaceholderText("e.g. 50")
        self._min_tok_entry.setToolTip("Exclude files with fewer tokens than this")
        row2.addWidget(self._min_tok_entry)
        row2.addStretch()
        filt_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Ignore Folders:"))
        self._ignore_entry = QLineEdit(
            "node_modules, __pycache__, Archive, archive, venv, ex, .venv, .claude")
        self._ignore_entry.setPlaceholderText("e.g. node_modules, .git, __pycache__")
        self._ignore_entry.setToolTip("Comma-separated folder names to skip during scanning")
        row3.addWidget(self._ignore_entry, stretch=1)
        filt_layout.addLayout(row3)

        btn_apply = QPushButton("Apply Filters")
        btn_apply.clicked.connect(self.apply_filters)
        filt_layout.addWidget(btn_apply)
        layout.addWidget(filt_group)

        hf_group = QGroupBox("Header / Footer")
        hf_layout = QVBoxLayout(hf_group)
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Header:"))
        self._header_entry = QLineEdit()
        r1.addWidget(self._header_entry, stretch=1)
        hf_layout.addLayout(r1)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Footer:"))
        self._footer_entry = QLineEdit()
        r2.addWidget(self._footer_entry, stretch=1)
        hf_layout.addLayout(r2)
        layout.addWidget(hf_group)

        action_row = QHBoxLayout()
        btn_combine = QPushButton("Combine Scripts")
        btn_combine.setProperty("class", "primary")
        btn_combine.clicked.connect(self._combine_scripts)
        action_row.addWidget(btn_combine)
        action_row.addStretch()
        layout.addLayout(action_row)

        self._progress = QProgressBar()
        self._progress.setTextVisible(True)
        self._progress.setFormat("%v / %m folders scanned")
        layout.addWidget(self._progress)

        file_group = QGroupBox("Selected Files")
        file_layout = QVBoxLayout(file_group)
        self._file_model = QStandardItemModel()
        self._file_model.setHorizontalHeaderLabels(["File Path", "Tokens"])
        self._file_tree = QTreeView()
        self._file_tree.setModel(self._file_model)
        self._file_tree.setRootIsDecorated(False)
        self._file_tree.setAlternatingRowColors(True)
        self._file_tree.setSelectionMode(QTreeView.ExtendedSelection)
        fh = self._file_tree.header()
        fh.setSectionResizeMode(QHeaderView.Interactive)
        fh.setStretchLastSection(True)
        fh.resizeSection(0, 300)

        self._file_empty_label = QLabel(
            "No files added yet\n\n"
            "Click  Add Folder  or  Add File(s)  to begin")
        self._file_empty_label.setAlignment(Qt.AlignCenter)
        self._file_empty_label.setStyleSheet(
            "color: palette(mid); padding: 24px;")
        file_layout.addWidget(self._file_empty_label)
        file_layout.addWidget(self._file_tree)
        btn_rm_file = QPushButton("Remove Selected File(s)")
        btn_rm_file.setProperty("class", "danger")
        btn_rm_file.clicked.connect(self._remove_selected_files)
        file_layout.addWidget(btn_rm_file)
        layout.addWidget(file_group, stretch=1)

        folder_group = QGroupBox("Selected Folders")
        folder_layout = QVBoxLayout(folder_group)
        self._folder_model = QStandardItemModel()
        self._folder_model.setHorizontalHeaderLabels(
            ["Folder Path", "Tokens"])
        self._folder_tree = QTreeView()
        self._folder_tree.setModel(self._folder_model)
        self._folder_tree.setRootIsDecorated(False)
        self._folder_tree.setAlternatingRowColors(True)
        self._folder_tree.setSelectionMode(QTreeView.ExtendedSelection)
        dh = self._folder_tree.header()
        dh.setSectionResizeMode(QHeaderView.Interactive)
        dh.setStretchLastSection(True)
        dh.resizeSection(0, 300)
        folder_layout.addWidget(self._folder_tree)
        btn_rm_folder = QPushButton("Remove Selected Folder(s)")
        btn_rm_folder.setProperty("class", "danger")
        btn_rm_folder.clicked.connect(self._remove_selected_folders)
        folder_layout.addWidget(btn_rm_folder)
        layout.addWidget(folder_group, stretch=1)

    # -- public accessors / mutators ------------------------------------

    @property
    def header(self) -> str:
        return self._header_entry.text()

    @property
    def header_text(self) -> str:
        """Alias used by main_window for profile save."""
        return self._header_entry.text()

    @property
    def footer(self) -> str:
        return self._footer_entry.text()

    @property
    def footer_text(self) -> str:
        """Alias used by main_window for profile save."""
        return self._footer_entry.text()

    @property
    def extensions_raw(self) -> str:
        return self._ext_entry.text()

    @property
    def ignored_folders_raw(self) -> str:
        return self._ignore_entry.text()

    def set_extensions(self, text: str) -> None:
        """Set the extensions filter field (called when loading a profile)."""
        self._ext_entry.setText(text)

    def set_min_tokens(self, value: int) -> None:
        """Set the min-tokens filter field."""
        self._min_tok_entry.setText(str(value))

    def set_header(self, text: str) -> None:
        """Set the header field (called when loading a profile)."""
        self._header_entry.setText(text)

    def set_footer(self, text: str) -> None:
        """Set the footer field (called when loading a profile)."""
        self._footer_entry.setText(text)

    def combine_scripts(self) -> None:
        """Public interface to trigger combine scripts (e.g. from menu)."""
        self._combine_scripts()

    # -- actions --------------------------------------------------------

    @Slot()
    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder and folder not in self._mw.folders:
            self._mw.folders.append(folder)
            self._mw.log(f"Added folder: {folder}")
            # Quick scan
            ext = parse_extensions(self._ext_entry.text())
            ign = parse_ignored_folders(self._ignore_entry.text())
            for path in scan_folder(folder, ext, ign):
                if path not in self._mw.all_files:
                    self._mw.all_files.append(path)
            self.apply_filters()

    @Slot()
    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select File(s)", "",
            "Supported files (*.py *.kt *.xml *.html *.js *.txt *.md "
            "*.json *.css *.bat *.p12 *.pem *.sh *.env *.R *.toml);;"
            "All files (*.*)")
        for p in paths:
            if p not in self._mw.all_files:
                self._mw.all_files.append(p)
                self._mw.log(f"Added file: {p}")
        if paths:
            self.apply_filters()

    @Slot()
    def _scan_folders(self) -> None:
        if not self._mw.folders:
            self._mw.log("No folders to scan.")
            return
        ext = parse_extensions(self._ext_entry.text())
        ign = parse_ignored_folders(self._ignore_entry.text())

        self._scan_thread = QThread()
        worker = _ScanWorker(self._mw.folders, ext, ign)
        worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(worker.run)
        worker.progress.connect(self._on_scan_progress)
        worker.file_found.connect(self._on_file_found)
        worker.finished.connect(self._on_scan_finished)
        worker.finished.connect(self._scan_thread.quit)
        # prevent GC
        self._scan_worker = worker
        self._scan_thread.start()

    @Slot(int, int)
    def _on_scan_progress(self, current, total):
        self._progress.setMaximum(total)
        self._progress.setValue(current)

    @Slot(str)
    def _on_file_found(self, path):
        if path not in self._mw.all_files:
            self._mw.all_files.append(path)

    @Slot(list)
    def _on_scan_finished(self, _found):
        self._progress.setValue(0)
        self._mw.log("Folder scanning complete.")
        self.apply_filters()

    @Slot()
    def apply_filters(self) -> None:
        """Re-filter files and update both tree views."""
        self._mw.allowed_extensions = self._ext_entry.text()
        try:
            self._mw.min_tokens = int(self._min_tok_entry.text())
        except (ValueError, TypeError):
            self._mw.min_tokens = 0

        ext = parse_extensions(self._mw.allowed_extensions)
        filtered = filter_files(
            self._mw.all_files, ext, self._mw.min_tokens)
        self._mw.filtered_files = filtered

        # Update file tree
        self._file_model.removeRows(0, self._file_model.rowCount())
        for path, tokens in filtered:
            path_item = QStandardItem(path)
            path_item.setEditable(False)
            path_item.setToolTip(path)
            tok_item = QStandardItem(f"{tokens:,}")
            tok_item.setEditable(False)
            tok_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._file_model.appendRow([path_item, tok_item])

        has_files = self._file_model.rowCount() > 0
        self._file_empty_label.setVisible(not has_files)
        self._file_tree.setVisible(has_files)

        self._mw.log(f"Filter applied: {len(filtered)} files shown.")

        # Update folder tree — token counts based on the *filtered* list
        # (not a disk rescan) so that removing files is reflected.
        self._folder_model.removeRows(0, self._folder_model.rowCount())
        for folder in self._mw.folders:
            # Sum tokens of filtered files that belong to this folder
            folder_prefix = folder + os.sep
            tokens = sum(
                t for p, t in filtered
                if p.startswith(folder_prefix) or p.startswith(folder + "/")
            )
            f_item = QStandardItem(folder)
            f_item.setEditable(False)
            f_item.setToolTip(folder)
            t_item = QStandardItem(f"{tokens:,}")
            t_item.setEditable(False)
            t_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._folder_model.appendRow([f_item, t_item])

        self.files_changed.emit(filtered)

    @Slot()
    def _remove_selected_files(self) -> None:
        indexes = self._file_tree.selectionModel().selectedRows()
        if not indexes:
            return
        paths_to_remove = []
        for idx in indexes:
            path = self._file_model.item(idx.row(), 0).text()
            paths_to_remove.append(path)
        for p in paths_to_remove:
            if p in self._mw.all_files:
                self._mw.all_files.remove(p)
            self._mw.log(f"Removed file: {p}")
        self.apply_filters()

    @Slot()
    def _remove_selected_folders(self) -> None:
        indexes = self._folder_tree.selectionModel().selectedRows()
        if not indexes:
            return
        folders_to_remove = []
        for idx in indexes:
            folder = self._folder_model.item(idx.row(), 0).text()
            folders_to_remove.append(folder)
        for folder in folders_to_remove:
            if folder in self._mw.folders:
                self._mw.folders.remove(folder)
            to_rm = [f for f in self._mw.all_files
                     if f.startswith(folder)]
            for f in to_rm:
                self._mw.all_files.remove(f)
            self._mw.log(f"Removed folder: {folder}")
        self.apply_filters()

    # -- Combine scripts -----------------------------------------------

    @Slot()
    def _combine_scripts(self) -> None:
        filtered = self._mw.filtered_files
        file_paths = [p for p, _t in filtered]
        if not file_paths:
            QMessageBox.warning(
                self, "Error", "No files selected after filtering.")
            return

        combined = build_combined_text(
            file_paths, self.header, self.footer)
        total_tokens = count_tokens(combined)

        default_dir = os.path.join(os.getcwd(), "backup")
        os.makedirs(default_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"combined_scripts_{ts}_{total_tokens}tokens.md"

        output_file, _ = QFileDialog.getSaveFileName(
            self, "Save Combined Scripts As",
            os.path.join(default_dir, default_name),
            "Markdown files (*.md);;Text files (*.txt);;All files (*.*)")
        if not output_file:
            return

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(combined)
            self._mw.log(f"Combined file created: {output_file}")

            # Auto eADR note
            eadr_panel = self._mw.findChild(
                QWidget, "eadr_panel")  # type: ignore[arg-type]
            project = "Origin"
            user_note = ""
            if hasattr(self._mw, '_eadr_panel'):
                project = self._mw._eadr_panel.project
                user_note = self._mw._eadr_panel.note_text
                if user_note:
                    self._mw._eadr_panel.clear_editor()

            from llm_buddy.services.preview_service import (
                build_combine_eadr_note,
            )
            note_text = build_combine_eadr_note(
                folders=self._mw.folders,
                filtered_files=file_paths,
                allowed_extensions=self._mw.allowed_extensions,
                min_tokens=self._mw.min_tokens,
                ignored_folders=self._ignore_entry.text(),
                output_file=output_file,
                total_tokens=total_tokens,
                user_note=user_note,
            )
            note_id = self._mw.prompt_database.add_eadr_note(
                note_text, project)
            if note_id >= 0:
                self._mw.log(
                    "eADR note automatically created for combined scripts")
                if hasattr(self._mw, '_eadr_panel'):
                    self._mw._eadr_panel.refresh()

            QMessageBox.information(
                self, "Success",
                f"Combined file saved to:\n{output_file}")
        except Exception as e:
            self._mw.log(f"Error writing output file: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to save output file:\n{e}")


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\eadr_panel.py

"""eADR (Elaborated Action Design Research) notes panel for the Qt GUI."""

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit, QTextBrowser,
    QTreeView, QGroupBox, QMessageBox, QHeaderView,
)


class EadrPanel(QWidget):
    """eADR note management panel.

    Provides:
    - Project name field
    - Note editor for new notes
    - History tree showing all saved notes
    - Read-only display of selected note content
    """

    note_saved = Signal()  # emitted after a note is saved

    def __init__(self, log_fn=None, toast_fn=None, db=None, parent=None):
        super().__init__(parent)
        self._log = log_fn or (lambda m: None)
        self._show_toast = toast_fn or (lambda msg, level="info": None)
        self._db = db
        self._notes: list = []  # cached EadrNote list (newest-first)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        proj_row = QHBoxLayout()
        proj_row.addWidget(QLabel("Project:"))
        self._project_entry = QLineEdit("Origin")
        self._project_entry.setMaximumWidth(200)
        proj_row.addWidget(self._project_entry)
        proj_row.addStretch()
        layout.addLayout(proj_row)

        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter, stretch=1)

        editor_group = QGroupBox("New Note")
        editor_layout = QVBoxLayout(editor_group)
        self._note_edit = QPlainTextEdit()
        self._note_edit.setPlaceholderText("Type your eADR note here...")
        editor_layout.addWidget(self._note_edit)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("Save Note")
        btn_save.setProperty("class", "primary")
        btn_save.clicked.connect(self._save_note)
        btn_row.addWidget(btn_save)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self._note_edit.clear)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        editor_layout.addLayout(btn_row)
        splitter.addWidget(editor_group)

        bottom = QSplitter(Qt.Horizontal)

        # History tree
        history_group = QGroupBox("Note History")
        history_layout = QVBoxLayout(history_group)
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["Date & Time", "Project"])
        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QTreeView.SingleSelection)
        header = self._tree.header()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.resizeSection(0, 180)
        self._tree.selectionModel().selectionChanged.connect(
            self._on_selection_changed)
        history_layout.addWidget(self._tree)
        bottom.addWidget(history_group)

        # Display area
        display_group = QGroupBox("Note Content")
        display_layout = QVBoxLayout(display_group)
        self._display = QTextBrowser()
        self._display.setPlaceholderText("Select a note to view its content.")
        display_layout.addWidget(self._display)

        self._btn_delete = QPushButton("Delete Selected Note")
        self._btn_delete.setProperty("class", "danger")
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._delete_note)
        display_layout.addWidget(self._btn_delete)
        bottom.addWidget(display_group)

        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self._refresh_history()

        sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_save.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc_save.activated.connect(self._save_note)

    @property
    def project(self) -> str:
        return self._project_entry.text().strip() or "Origin"

    @property
    def note_text(self) -> str:
        """Return text currently in the editor (used by combine-scripts)."""
        return self._note_edit.toPlainText().strip()

    def clear_editor(self) -> None:
        self._note_edit.clear()

    def set_db(self, db) -> None:
        """Set the database reference after construction."""
        self._db = db
        self._refresh_history()

    # -- internal slots ------------------------------------------------

    @Slot()
    def _save_note(self) -> None:
        text = self._note_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty Note",
                                "Please enter a note before saving.")
            return
        project = self.project
        if self._db is None:
            QMessageBox.critical(self, "Error",
                                 "Database not available.")
            return
        note_id = self._db.add_eadr_note(text, project)
        if note_id >= 0:
            self._log(f"eADR note saved for project: {project}")
            self._note_edit.clear()
            self._refresh_history()
            self.note_saved.emit()
            self._show_toast("eADR note saved.", "success")
        else:
            QMessageBox.critical(self, "Error", "Failed to save eADR note.")

    @Slot()
    def _refresh_history(self) -> None:
        if self._db is not None:
            self._notes = self._db.get_eadr_notes()
        else:
            self._notes = []
        self._model.removeRows(0, self._model.rowCount())
        for note in self._notes:  # already newest-first from db
            ts_item = QStandardItem(note.timestamp)
            ts_item.setEditable(False)
            ts_item.setToolTip(note.timestamp)
            proj_item = QStandardItem(note.project)
            proj_item.setEditable(False)
            proj_item.setToolTip(note.project)
            self._model.appendRow([ts_item, proj_item])
        self._btn_delete.setEnabled(False)
        self._display.clear()

    def refresh(self) -> None:
        """Public method so other panels can trigger a refresh."""
        self._refresh_history()

    @Slot()
    def _on_selection_changed(self) -> None:
        indexes = self._tree.selectionModel().selectedRows()
        if not indexes:
            self._btn_delete.setEnabled(False)
            self._display.clear()
            return
        row = indexes[0].row()
        if 0 <= row < len(self._notes):
            note = self._notes[row]
            html = (
                f"<b>Project:</b> {note.project}<br>"
                f"<b>Date &amp; Time:</b> {note.timestamp}<br><br>"
                f"<pre>{note.note}</pre>"
            )
            self._display.setHtml(html)
            self._btn_delete.setEnabled(True)

    @Slot()
    def _delete_note(self) -> None:
        indexes = self._tree.selectionModel().selectedRows()
        if not indexes:
            return
        row = indexes[0].row()
        if row < 0 or row >= len(self._notes):
            return
        note = self._notes[row]

        answer = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this note?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if self._db and self._db.delete_eadr_note(note.id):
            self._log(
                f"Deleted note from {note.timestamp} "
                f"for project '{note.project}'")
            self._refresh_history()
            self._show_toast("Note deleted.", "info")
        else:
            QMessageBox.critical(self, "Error", "Failed to delete note.")


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\forking_panel.py

"""
Prompt Explorer panel — Prompt-centric conversational forking visualization.

Each individual prompt is a node in the tree graph. Selecting a node shows
its full text and LLM response in the sidebar. New prompts are automatically
added to the checked-out branch; forking creates diverging paths from a
shared ancestor prompt.

Tree layout:
  - Time flows top-to-bottom (workflow direction).
  - Each branch occupies its own column.
  - Fork edges (dashed) connect the fork-point prompt to the first unique
    prompt of each child branch.
  - Sequential edges (solid) connect consecutive prompts within a branch.
"""

from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, Slot, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QBrush, QColor, QPen, QFont, QPainter, QPainterPath, QAction, QPalette,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QMenu, QComboBox, QMessageBox,
    QFormLayout, QTextEdit, QLineEdit, QInputDialog, QApplication,
    QDialog, QDialogButtonBox, QCheckBox, QGroupBox, QFrame,
)

from llm_buddy.core.forking import (
    ConversationTree, Branch, ForkPoint,
    auto_detect_trees, build_tree_with_forks, BRANCH_STATUSES, FORK_TRIGGERS,
)
from llm_buddy.qt.theme import get_theme_colors, current_theme_name



class ForkDialog(QDialog):
    """Multi-field dialog for creating a fork with full metadata."""

    def __init__(self, parent_branch_name: str, prompt_count: int,
                 default_index: int = -1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fork Branch")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<b>Forking from:</b> {parent_branch_name}"))

        form = QFormLayout()

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. 'Try alternative API approach'")
        form.addRow("Branch name:", self.edit_name)

        self.combo_trigger = QComboBox()
        for val, label in FORK_TRIGGERS:
            self.combo_trigger.addItem(label, val)
        for i, (val, _) in enumerate(FORK_TRIGGERS):
            if val == "exploratory":
                self.combo_trigger.setCurrentIndex(i)
                break
        form.addRow("Trigger:", self.combo_trigger)

        self.edit_reason = QLineEdit()
        self.edit_reason.setPlaceholderText("Why are you branching here?")
        form.addRow("Reason:", self.edit_reason)

        self.edit_context = QTextEdit()
        self.edit_context.setPlaceholderText(
            "Key context to carry forward (artifacts, decisions, constraints)…")
        self.edit_context.setMaximumHeight(80)
        form.addRow("Context:", self.edit_context)

        if prompt_count > 0:
            idx = default_index if 0 <= default_index < prompt_count else prompt_count - 1
            self._fork_index = idx
            form.addRow("Fork after prompt:", QLabel(f"<b>#{idx + 1}</b> of {prompt_count}"))
        else:
            self._fork_index = 0

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.edit_name.setFocus()

    @property
    def fork_index(self) -> int:
        return self._fork_index

    def get_values(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "trigger": self.combo_trigger.currentData(),
            "reason": self.edit_reason.text().strip(),
            "context_summary": self.edit_context.toPlainText().strip(),
            "fork_index": self._fork_index,
        }



class MergeDialog(QDialog):
    """Dialog to merge one branch into a chosen target."""

    def __init__(self, source_branch: Branch, tree: ConversationTree, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Branch")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"<b>Merge source:</b> {source_branch.name}  "
            f"({len(source_branch.prompt_ids)} prompts)"))

        form = QFormLayout()
        self.combo_target = QComboBox()
        for b in tree.get_visible_branches():
            if b.id != source_branch.id:
                self.combo_target.addItem(
                    f"{b.name}  ({len(b.prompt_ids)} prompts)", b.id)
        form.addRow("Merge into:", self.combo_target)

        self.chk_copy_prompts = QCheckBox("Copy unique prompts into target")
        self.chk_copy_prompts.setChecked(True)
        form.addRow("", self.chk_copy_prompts)

        self.edit_insights = QTextEdit()
        self.edit_insights.setPlaceholderText(
            "What did you learn from this branch? Key takeaways…")
        self.edit_insights.setMaximumHeight(100)
        form.addRow("Merge insights:", self.edit_insights)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> dict:
        return {
            "target_branch_id": self.combo_target.currentData(),
            "include_prompts": self.chk_copy_prompts.isChecked(),
            "insights": self.edit_insights.toPlainText().strip(),
        }


# One color per branch (cycles if > 10 branches)
BRANCH_PALETTE = [
    QColor("#1565C0"),  # Deep Blue
    QColor("#2E7D32"),  # Deep Green
    QColor("#B71C1C"),  # Deep Red
    QColor("#6A1B9A"),  # Deep Purple
    QColor("#E65100"),  # Deep Orange
    QColor("#00695C"),  # Deep Teal
    QColor("#AD1457"),  # Deep Pink
    QColor("#4E342E"),  # Deep Brown
    QColor("#37474F"),  # Blue Grey
    QColor("#F9A825"),  # Amber (dark)
]



class PromptNodeItem(QGraphicsItem):
    """A prompt displayed as a rounded card in the tree graph."""

    NODE_W = 230
    NODE_H = 95

    def __init__(self, prompt, branch: Branch, color: QColor,
                 is_fork_point: bool, panel):
        super().__init__()
        self.prompt = prompt
        self.branch = branch
        self.color = color
        self.is_fork_point = is_fork_point
        self.panel = panel
        self._edges: list = []
        self.is_hovered = False

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

    def add_edge(self, edge) -> None:
        self._edges.append(edge)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.NODE_W, self.NODE_H)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.NODE_W, self.NODE_H)

        if self.isSelected():
            bg = self.color.lighter(190)
            border_pen = QPen(self.color, 3)
        elif self.is_hovered:
            bg = self.color.lighter(200)
            border_pen = QPen(self.color, 2)
        else:
            bg = QApplication.palette().color(QPalette.Base)
            border_pen = QPen(self.color.darker(110), 1.5)

        painter.setPen(border_pen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(rect, 7, 7)

        if self.is_fork_point:
            painter.setPen(QPen(self.color, 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-5, -5, 5, 5), 10, 10)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.color))
        painter.drawRoundedRect(QRectF(0, 0, 6, self.NODE_H), 3, 3)
        painter.drawRect(QRectF(3, 0, 3, self.NODE_H))   # square off right edge

        ts = self.prompt.timestamp.strftime("%m/%d %H:%M") if self.prompt.timestamp else ""
        llm = (self.prompt.llm_used or "")[:16]
        painter.setPen(QApplication.palette().color(QPalette.PlaceholderText))
        painter.setFont(QFont("Segoe UI", 7))
        painter.drawText(QRectF(13, 5, self.NODE_W - 17, 14),
                         Qt.AlignmentFlag.AlignLeft,
                         f"{ts}  ·  {llm}")

        text = (self.prompt.prompt_text or self.prompt.description or "(no text)")
        painter.setPen(QApplication.palette().color(QPalette.Text))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(
            QRectF(13, 22, self.NODE_W - 17, 55),
            Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
            text[:200],
        )

        if self.prompt.response_text:
            painter.setPen(Qt.PenStyle.NoPen)
            dot_color = QColor(get_theme_colors(current_theme_name())["success"])
            painter.setBrush(QBrush(dot_color))
            painter.drawEllipse(
                QRectF(self.NODE_W - 14, self.NODE_H - 14, 8, 8))

    def hoverEnterEvent(self, event) -> None:
        self.is_hovered = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()

    def hoverLeaveEvent(self, event) -> None:
        self.is_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.panel.select_prompt(self.prompt.id, self.branch.id)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu()

        act_fork = QAction("Fork from here…", menu)
        act_fork.triggered.connect(
            lambda: self.panel._fork_from_prompt(self.branch, self.prompt.id))
        menu.addAction(act_fork)

        tree = self.panel._active_tree
        act_checkout = QAction("Checkout this branch", menu)
        act_checkout.triggered.connect(
            lambda: self.panel._checkout_branch(tree, self.branch))
        if tree and tree.checked_out_branch_id == self.branch.id:
            act_checkout.setEnabled(False)
            act_checkout.setText("✓ Already checked out")
        menu.addAction(act_checkout)

        menu.addSeparator()

        act_copy = QAction("Copy prompt text", menu)
        act_copy.triggered.connect(
            lambda: QApplication.clipboard().setText(self.prompt.prompt_text or ""))
        menu.addAction(act_copy)

        act_copy_r = QAction("Copy response text", menu)
        act_copy_r.setEnabled(bool(self.prompt.response_text))
        act_copy_r.triggered.connect(
            lambda: QApplication.clipboard().setText(self.prompt.response_text or ""))
        menu.addAction(act_copy_r)

        menu.exec(event.screenPos())



class EdgeItem(QGraphicsPathItem):
    """Smooth cubic Bezier connecting two PromptNodeItems top-to-bottom."""

    def __init__(self, src: PromptNodeItem, dst: PromptNodeItem,
                 color: QColor, dashed: bool = False):
        super().__init__()
        self.src = src
        self.dst = dst
        self.setZValue(-1)
        style = Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine
        width = 1.8 if dashed else 1.5
        self.setPen(QPen(color, width, style,
                         Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self._update_path()

    def _update_path(self) -> None:
        w = self.src.NODE_W
        h = self.src.NODE_H
        start = self.src.scenePos() + QPointF(w / 2, h)
        end   = self.dst.scenePos() + QPointF(self.dst.NODE_W / 2, 0)

        path = QPainterPath(start)
        dy = end.y() - start.y()
        dx = abs(end.x() - start.x())
        # Vertical pull proportional to both dy and horizontal distance
        pull = max(abs(dy) * 0.45, dx * 0.3, 30)
        cp1 = QPointF(start.x(), start.y() + pull)
        cp2 = QPointF(end.x(),   end.y()   - pull)
        path.cubicTo(cp1, cp2, end)
        self.setPath(path)



class BranchLabelItem(QGraphicsItem):
    W, H = 180, 26

    def __init__(self, branch: Branch, color: QColor):
        super().__init__()
        self.branch = branch
        self.color = color

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.W, self.H)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.color.lighter(175)))
        painter.drawRoundedRect(self.boundingRect(), 5, 5)
        painter.setPen(self.color.darker(140))
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font)
        name = self.branch.name
        if len(name) > 22:
            name = name[:20] + "…"
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, name)



class TreeGraphView(QGraphicsView):
    """Zoomable, pannable canvas that draws individual prompts as nodes."""

    # Layout constants
    NODE_W  = PromptNodeItem.NODE_W
    NODE_H  = PromptNodeItem.NODE_H
    H_GAP   = 60    # horizontal gap between branch columns
    V_GAP   = 28    # vertical gap between sequential prompts
    TOP_PAD = 48    # vertical padding above first row (room for branch labels)

    COL_STEP = NODE_W + H_GAP
    ROW_STEP = NODE_H + V_GAP

    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setBackgroundBrush(
            QBrush(QApplication.palette().color(QPalette.Window)))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._is_panning = False
        self._pan_start = QPointF()
        self._prompt_items: dict = {}   # prompt_id -> PromptNodeItem

    @Slot(str)
    def update_theme(self, _name: str = "") -> None:
        """Re-apply the scene background and repaint all nodes for the new theme."""
        self.setBackgroundBrush(
            QBrush(QApplication.palette().color(QPalette.Window)))
        self._scene.update()


    def draw_prompt_tree(self, tree: ConversationTree, db,
                         show_hidden: bool = False,
                         search_term: str = "") -> None:
        """Rebuild the visual graph for *tree*."""
        self._scene.clear()
        self._prompt_items.clear()

        if not tree or not db:
            return

        visible = tree.get_visible_branches(show_hidden=show_hidden)
        if not visible:
            return

        color_map: dict = {}
        for i, b in enumerate(tree.branches):
            color_map[b.id] = BRANCH_PALETTE[i % len(BRANCH_PALETTE)]

        col_map, start_row_map = self._compute_layout(tree, visible)

        # Build Y positions based on tree structure, not timestamps.
        # Each branch's unique prompts start at the row after the fork point.
        # This ensures forked prompts appear next to where they diverged.
        pid_to_y: dict = {}
        # First: assign rows to root branch prompts (sequential from row 0)
        root_branch = tree.get_root_branch()
        if root_branch and root_branch.id in {b.id for b in visible}:
            for i, pid in enumerate(root_branch.prompt_ids):
                pid_to_y[pid] = i * self.ROW_STEP + self.TOP_PAD

        # Then: assign rows to child branches starting from their fork point
        def _assign_branch_rows(branch):
            if branch.parent_branch_id is None:
                return  # root already assigned
            fp = tree.get_fork_point(branch.fork_point_id) if branch.fork_point_id else None
            uids = self.unique_prompt_ids(tree, branch)
            # Start row: one row after the fork point in the parent
            start_row = start_row_map.get(branch.id, 0)
            for i, pid in enumerate(uids):
                pid_to_y[pid] = (start_row + i) * self.ROW_STEP + self.TOP_PAD
            # Recurse into children of this branch
            for child in tree.get_child_branches(branch.id):
                if child.id in {b.id for b in visible}:
                    _assign_branch_rows(child)

        if root_branch:
            for child in tree.get_child_branches(root_branch.id):
                if child.id in {b.id for b in visible}:
                    _assign_branch_rows(child)

        fork_prompt_ids = {fp.prompt_id for fp in tree.fork_points if fp.prompt_id}

        search_lower = search_term.strip().lower()

        for branch in visible:
            col      = col_map.get(branch.id, 0)
            start_r  = start_row_map.get(branch.id, 0)
            uids     = self.unique_prompt_ids(tree, branch)
            color    = color_map.get(branch.id, BRANCH_PALETTE[0])
            x        = col * self.COL_STEP

            if not uids:
                continue

            # branch column label — anchored to the first prompt's temporal Y
            label = BranchLabelItem(branch, color)
            first_y = pid_to_y.get(uids[0], start_r * self.ROW_STEP + self.TOP_PAD)
            label.setPos(QPointF(
                x + (self.NODE_W - label.W) / 2,
                first_y - label.H - 6,
            ))
            self._scene.addItem(label)

            prev_item: Optional[PromptNodeItem] = None
            for i, pid in enumerate(uids):
                p = db.get_prompt(pid)
                if p is None:
                    continue

                y = pid_to_y.get(pid, (start_r + i) * self.ROW_STEP + self.TOP_PAD)
                node = PromptNodeItem(p, branch, color, pid in fork_prompt_ids, self.panel)
                node.setPos(QPointF(x, y))

                if search_lower and \
                        search_lower not in (p.prompt_text or "").lower() and \
                        search_lower not in (p.description or "").lower():
                    node.setOpacity(0.3)

                self._scene.addItem(node)
                self._prompt_items[pid] = node

                if prev_item is not None:
                    edge = EdgeItem(prev_item, node, color, dashed=False)
                    self._scene.addItem(edge)

                prev_item = node

        for branch in visible:
            if branch.parent_branch_id is None:
                continue
            fp = tree.get_fork_point(branch.fork_point_id) if branch.fork_point_id else None
            if fp is None:
                continue

            parent = tree.get_branch(branch.parent_branch_id)
            if parent is None:
                continue

            # The prompt in the parent branch AT the fork index
            if 0 <= fp.fork_index < len(parent.prompt_ids):
                parent_pid  = parent.prompt_ids[fp.fork_index]
                parent_node = self._prompt_items.get(parent_pid)

                uids = self.unique_prompt_ids(tree, branch)
                if uids:
                    child_node = self._prompt_items.get(uids[0])
                    if parent_node and child_node:
                        color = color_map.get(branch.id, QColor("#888888"))
                        edge = EdgeItem(parent_node, child_node, color, dashed=True)
                        self._scene.addItem(edge)

        rect = self._scene.itemsBoundingRect()
        self._scene.setSceneRect(rect.adjusted(-80, -80, 80, 80))

    def select_node(self, prompt_id: str, center: bool = True) -> None:
        for item in self._scene.selectedItems():
            item.setSelected(False)
        node = self._prompt_items.get(prompt_id)
        if node:
            node.setSelected(True)
            if center:
                self.centerOn(node)


    @staticmethod
    def unique_prompt_ids(tree: ConversationTree, branch: Branch) -> List[str]:
        """Return prompt IDs that are unique to *branch* (not inherited from parent)."""
        if branch.parent_branch_id is None:
            return list(branch.prompt_ids)
        fp = tree.get_fork_point(branch.fork_point_id) if branch.fork_point_id else None
        if fp is None:
            return list(branch.prompt_ids)
        return list(branch.prompt_ids[fp.fork_index + 1:])

    def _compute_layout(self, tree: ConversationTree,
                        visible: List[Branch]) -> tuple:
        """
        Compute column and start_row for each branch (git-style layout).

        Every branch gets its own column so that prompts never overlap.
        Root is always column 0; child branches get columns 1, 2, …
        in DFS order.

        Start row: root starts at 0; a child branch's unique prompts begin
        at (parent_start_row + fork_index + 1).
        """
        visible_ids = {b.id for b in visible}
        col_map: dict  = {}
        row_map: dict  = {}
        col_ctr = [0]

        def _start_row(branch: Branch) -> int:
            if branch.parent_branch_id is None:
                return 0
            parent = tree.get_branch(branch.parent_branch_id)
            if parent is None:
                return 0
            fp = tree.get_fork_point(branch.fork_point_id) if branch.fork_point_id else None
            idx = fp.fork_index if fp else max(0, len(parent.prompt_ids) - 1)
            return row_map.get(branch.parent_branch_id, 0) + idx + 1

        def dfs(bid: str) -> None:
            if bid not in visible_ids:
                return
            branch = tree.get_branch(bid)
            if branch is None:
                return

            row_map[bid] = _start_row(branch)
            # Each branch gets its own column (git-style, no overlap)
            col_map[bid] = float(col_ctr[0])
            col_ctr[0] += 1

            for child in tree.get_child_branches(bid):
                if child.id in visible_ids:
                    dfs(child.id)

        root = tree.get_root_branch()
        if root and root.id in visible_ids:
            dfs(root.id)

        return col_map, row_map


    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F:
            self.panel._fit_to_view()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        self.setFocus()
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._is_panning:
            delta = event.pos() - self._pan_start
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            self._pan_start = event.pos()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current = self.transform().m11()
        if (factor > 1 and current < 3.5) or (factor < 1 and current > 0.15):
            self.scale(factor, factor)



class ForkingPanel(QWidget):

    branch_forked = Signal(str, str, str, str)   # tree, parent, child, trigger
    branch_merged = Signal(str, str, str)         # tree, source, insights

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._trees: List[ConversationTree] = []
        self._active_tree: Optional[ConversationTree] = None
        self._active_prompt_id: Optional[str] = None
        self._active_branch_id: Optional[str] = None
        self._show_hidden = False
        self._search_term = ""

        # Periodic auto-sync timer
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(30_000)
        self._sync_timer.timeout.connect(self.refresh)

        self._build_ui()
        self.refresh()
        self._sync_timer.start()
        QTimer.singleShot(0, self._init_splitter_sizes)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._graph_view = TreeGraphView(self)

        tb1 = QHBoxLayout()
        tb1.setContentsMargins(8, 8, 8, 4)

        tb1.addWidget(QLabel("<b>Conversation:</b>"))
        self._tree_selector = QComboBox()
        self._tree_selector.setMinimumWidth(300)
        self._tree_selector.currentIndexChanged.connect(self._on_tree_changed)
        tb1.addWidget(self._tree_selector)

        self._lbl_checkout = QLabel("")
        self._lbl_checkout.setStyleSheet(
            "color: #2E7D32; font-weight: bold; padding: 0 8px;")
        tb1.addWidget(self._lbl_checkout)

        tb1.addStretch()

        btn_sync = QPushButton("↻ Sync")
        btn_sync.setToolTip("Pull new prompts from the database now")
        btn_sync.clicked.connect(self.refresh)
        tb1.addWidget(btn_sync)

        btn_fit = QPushButton("⛶ Fit  (F)")
        btn_fit.clicked.connect(self._fit_to_view)
        tb1.addWidget(btn_fit)

        root.addLayout(tb1)

        tb2 = QHBoxLayout()
        tb2.setContentsMargins(8, 0, 8, 8)

        tb2.addWidget(QLabel("🔍"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Filter prompts by text…")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setMaximumWidth(280)
        self._search_box.textChanged.connect(self._on_search_changed)
        tb2.addWidget(self._search_box)

        self._chk_hidden = QCheckBox("Show archived branches")
        self._chk_hidden.setToolTip("Include soft-deleted branches")
        self._chk_hidden.toggled.connect(self._on_show_hidden_toggled)
        tb2.addWidget(self._chk_hidden)

        tb2.addStretch()

        btn_fork = QPushButton("🌱 Fork from selection")
        btn_fork.setToolTip("Create a new branch diverging from the selected prompt")
        btn_fork.clicked.connect(self._fork_from_selection)
        tb2.addWidget(btn_fork)

        btn_merge = QPushButton("🔀 Merge branch")
        btn_merge.setToolTip("Merge the selected prompt's branch into another")
        btn_merge.clicked.connect(self._merge_from_selection)
        tb2.addWidget(btn_merge)

        root.addLayout(tb2)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(6)
        root.addWidget(self._splitter, stretch=1)

        self._splitter.addWidget(self._graph_view)

        sidebar = QWidget()
        sidebar.setMinimumWidth(360)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 12, 12, 12)
        sl.setSpacing(8)

        # Context header
        self._lbl_context = QLabel("<i>Select a prompt node to read its content</i>")
        self._lbl_context.setWordWrap(True)
        sl.addWidget(self._lbl_context)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sl.addWidget(sep)

        # Prompt text
        sl.addWidget(QLabel("<b>Prompt:</b>"))
        self._txt_prompt = QTextEdit()
        self._txt_prompt.setReadOnly(True)
        self._txt_prompt.setPlaceholderText("Prompt text will appear here…")
        self._txt_prompt.setMinimumHeight(110)
        sl.addWidget(self._txt_prompt, stretch=3)

        # Response text
        sl.addWidget(QLabel("<b>LLM Response:</b>"))
        self._txt_response = QTextEdit()
        self._txt_response.setReadOnly(True)
        self._txt_response.setPlaceholderText(
            "LLM response will appear here…\n\n"
            "(Responses are captured by the Proxy or MCP recorder. "
            "The Chrome extension captures prompts only.)")
        self._txt_response.setMinimumHeight(110)
        sl.addWidget(self._txt_response, stretch=3)

        # Metadata group
        self._meta_group = QGroupBox("Metadata")
        mf = QFormLayout(self._meta_group)
        mf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._lbl_ts      = QLabel("—")
        self._lbl_llm     = QLabel("—")
        self._lbl_source  = QLabel("—")
        self._lbl_branch  = QLabel("—")
        mf.addRow("Timestamp:", self._lbl_ts)
        mf.addRow("LLM:",       self._lbl_llm)
        mf.addRow("Source:",    self._lbl_source)
        mf.addRow("Branch:",    self._lbl_branch)
        sl.addWidget(self._meta_group)

        # Fork origin group (hidden unless branch is a fork)
        self._fork_group = QGroupBox("Fork Origin")
        ff = QFormLayout(self._fork_group)
        ff.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._lbl_fork_parent  = QLabel("—")
        self._lbl_fork_trigger = QLabel("—")
        self._lbl_fork_reason  = QLabel("—")
        self._lbl_fork_reason.setWordWrap(True)
        ff.addRow("Parent branch:", self._lbl_fork_parent)
        ff.addRow("Trigger:",       self._lbl_fork_trigger)
        ff.addRow("Reason:",        self._lbl_fork_reason)
        self._fork_group.setVisible(False)
        sl.addWidget(self._fork_group)

        # Action buttons
        acts = QHBoxLayout()

        self._btn_checkout = QPushButton("⬤ Checkout Branch")
        self._btn_checkout.setToolTip("New prompts go to this branch")
        self._btn_checkout.clicked.connect(self._checkout_from_selection)
        acts.addWidget(self._btn_checkout)

        self._btn_eadr = QPushButton("📝 eADR Note")
        self._btn_eadr.clicked.connect(self._eadr_from_selection)
        acts.addWidget(self._btn_eadr)

        self._btn_copy = QPushButton("📋 Copy Prompt")
        self._btn_copy.clicked.connect(self._copy_prompt_from_selection)
        acts.addWidget(self._btn_copy)

        sl.addLayout(acts)

        self._sidebar = sidebar
        self._sidebar.setEnabled(False)
        self._splitter.addWidget(sidebar)

        self._splitter.setStretchFactor(0, 2)
        self._splitter.setStretchFactor(1, 1)

    def _init_splitter_sizes(self) -> None:
        total = max(self.width(), 1100)
        sw = max(360, int(total * 0.33))
        self._splitter.setSizes([total - sw, sw])


    def refresh(self) -> None:
        """Sync trees from the prompt database, rebuild selector + graph."""
        # Save viewport so we can restore after redraw
        saved_transform = self._graph_view.transform()
        center = self._graph_view.mapToScene(
            self._graph_view.viewport().rect().center())
        self._graph_view.viewport().setUpdatesEnabled(False)

        active_tree_id = self._active_tree.id if self._active_tree else None

        self._trees = self._mw.prompt_database.load_trees()
        db = getattr(self._mw, "prompt_database", None)
        suggestions = auto_detect_trees(db) if db else []

        sug_by_cid = {s["conversation_id"]: s for s in suggestions
                      if s.get("conversation_id")}

        # Build existing-tree lookup by conversation ID
        existing: dict = {}
        for t in self._trees:
            cid = self._get_tree_cid(t)
            if cid:
                existing[cid] = t

        modified = False

        for sug in suggestions:
            cid = sug.get("conversation_id")
            if not cid:
                continue
            newest_ts = sug.get("last_timestamp") or datetime.now()

            # Resolve full prompt objects for fork detection
            sug_prompts = [db.get_prompt(pid) for pid in sug["prompt_ids"]]
            sug_prompts = [p for p in sug_prompts if p is not None]

            if cid not in existing:
                # Create a new tree for this conversation
                desc = sug.get("sample_description", "")
                new_tree = ConversationTree(
                    name=desc[:60] or cid,
                    description=desc,
                )
                new_tree.source_conversation_id = cid
                if not hasattr(new_tree, "tags"):
                    new_tree.tags = []
                if f"cid:{cid}" not in new_tree.tags:
                    new_tree.tags.append(f"cid:{cid}")

                # Use fork detection to build branches from prompt metadata
                if build_tree_with_forks(new_tree, sug_prompts, db):
                    pass  # tree populated with fork-aware branches
                else:
                    # Fallback: linear assignment to root branch
                    root = new_tree.get_root_branch()
                    root.prompt_ids = list(sug["prompt_ids"])
                    root.updated_at = newest_ts

                new_tree.updated_at = newest_ts
                self._trees.append(new_tree)
                existing[cid] = new_tree
                modified = True
            else:
                # Update existing tree with any new prompts (fork-aware)
                tree = existing[cid]
                if build_tree_with_forks(tree, sug_prompts, db):
                    tree.updated_at = newest_ts
                    modified = True

        # Sort trees newest-first
        def _sort_key(t: ConversationTree):
            cid = self._get_tree_cid(t)
            sug = sug_by_cid.get(cid) if cid else None
            sug_ts = sug.get("last_timestamp") if sug else None
            tree_ts = getattr(t, "updated_at", None) or getattr(t, "created_at", None)
            return sug_ts or tree_ts or datetime.min

        self._trees.sort(key=_sort_key, reverse=True)

        if modified:
            db = getattr(self._mw, "prompt_database", None)
            if db:
                for tree in self._trees:
                    db.save_tree(tree)

        # Rebuild the tree selector combo
        self._tree_selector.blockSignals(True)
        self._tree_selector.clear()

        restore_idx = 0
        search = self._search_term.strip().lower()

        for tree in self._trees:
            if search and search not in tree.name.lower():
                continue
            root_b = tree.get_root_branch()
            # Count all unique prompts across every branch
            all_pids: set = set()
            for b in tree.branches:
                all_pids.update(b.prompt_ids)
            n_prompts = len(all_pids)
            n_branches = len(tree.branches)
            label = (f"{tree.name}  "
                     f"[{n_prompts} prompts · {n_branches} branch{'es' if n_branches != 1 else ''}]")
            self._tree_selector.addItem(label, tree.id)
            if active_tree_id and tree.id == active_tree_id:
                restore_idx = self._tree_selector.count() - 1

        self._tree_selector.setCurrentIndex(
            restore_idx if self._tree_selector.count() else -1)
        self._tree_selector.blockSignals(False)

        # Restore active tree
        if not self._active_tree and self._tree_selector.count():
            first_id = self._tree_selector.itemData(0)
            self._active_tree = next(
                (t for t in self._trees if t.id == first_id), None)

        self._redraw_graph()
        self._update_checkout_label()

        self._graph_view.setTransform(saved_transform)
        self._graph_view.centerOn(center)
        self._graph_view.viewport().setUpdatesEnabled(True)


    @staticmethod
    def _get_tree_cid(tree: ConversationTree) -> Optional[str]:
        cid = getattr(tree, "source_conversation_id", None)
        if cid:
            return cid
        for tag in getattr(tree, "tags", []):
            if isinstance(tag, str) and tag.startswith("cid:"):
                return tag[4:]
        return None

    def _redraw_graph(self) -> None:
        if not self._active_tree:
            return
        db = getattr(self._mw, "prompt_database", None)
        self._graph_view.draw_prompt_tree(
            self._active_tree, db,
            show_hidden=self._show_hidden,
            search_term=self._search_term,
        )

    def _fit_to_view(self) -> None:
        if self._graph_view._scene.items():
            self._graph_view.fitInView(
                self._graph_view._scene.itemsBoundingRect(),
                Qt.AspectRatioMode.KeepAspectRatio)


    @Slot(int)
    def _on_tree_changed(self, index: int) -> None:
        if index < 0:
            return
        tree_id = self._tree_selector.itemData(index)
        tree = next((t for t in self._trees if t.id == tree_id), None)
        if not tree:
            return

        self._active_tree = tree
        self._active_prompt_id = None
        self._active_branch_id = None
        self._sidebar.setEnabled(False)
        self._lbl_context.setText("<i>Select a prompt node to read its content</i>")
        self._fork_group.setVisible(False)

        self._redraw_graph()
        self._update_checkout_label()
        QTimer.singleShot(50, self._fit_to_view)


    def select_prompt(self, prompt_id: str, branch_id: str) -> None:
        """Called by PromptNodeItem on click — populate the sidebar."""
        db = getattr(self._mw, "prompt_database", None)
        if not db or not self._active_tree:
            return

        p = db.get_prompt(prompt_id)
        if not p:
            return

        branch = self._active_tree.get_branch(branch_id)
        if not branch:
            return

        self._active_prompt_id = prompt_id
        self._active_branch_id = branch_id

        self._graph_view.select_node(prompt_id)
        self._sidebar.setEnabled(True)

        uids = TreeGraphView.unique_prompt_ids(self._active_tree, branch)
        try:
            pos = uids.index(prompt_id) + 1
        except ValueError:
            pos = "?"
        self._lbl_context.setText(
            f"<b>{branch.name}</b>  ·  prompt {pos} of {len(uids)}")

        self._txt_prompt.setPlainText(
            p.prompt_text or "(no prompt text recorded)")
        self._txt_response.setPlainText(
            p.response_text or "(no response captured for this prompt)")

        ts = p.timestamp.strftime("%Y-%m-%d  %H:%M:%S") if p.timestamp else "—"
        self._lbl_ts.setText(ts)
        self._lbl_llm.setText(p.llm_used or "—")
        self._lbl_source.setText(p.source or "—")
        self._lbl_branch.setText(branch.name)

        if branch.fork_point_id:
            fp = self._active_tree.get_fork_point(branch.fork_point_id)
            if fp:
                parent_b = self._active_tree.get_branch(fp.parent_branch_id)
                self._lbl_fork_parent.setText(parent_b.name if parent_b else "—")
                trigger_label = fp.trigger
                for val, label in FORK_TRIGGERS:
                    if val == fp.trigger:
                        trigger_label = label
                        break
                self._lbl_fork_trigger.setText(trigger_label)
                self._lbl_fork_reason.setText(fp.reason or "—")
                self._fork_group.setVisible(True)
            else:
                self._fork_group.setVisible(False)
        else:
            self._fork_group.setVisible(False)


    @Slot(str)
    def _on_search_changed(self, text: str) -> None:
        self._search_term = text
        self._redraw_graph()

    @Slot(bool)
    def _on_show_hidden_toggled(self, checked: bool) -> None:
        self._show_hidden = checked
        self._redraw_graph()


    def _checkout_branch(self, tree: ConversationTree, branch: Branch) -> None:
        if not tree or not branch:
            return
        if tree.checkout_branch(branch.id):
            self._mw.prompt_database.save_tree(tree)
            self._update_checkout_label()
            self._redraw_graph()
            if hasattr(self._mw, "log"):
                self._mw.log(
                    f"Checked out '{branch.name}' — new prompts go here.")

    def _checkout_from_selection(self) -> None:
        if not self._active_tree or not self._active_branch_id:
            return
        branch = self._active_tree.get_branch(self._active_branch_id)
        self._checkout_branch(self._active_tree, branch)

    def _update_checkout_label(self) -> None:
        if self._active_tree:
            co = self._active_tree.get_checked_out_branch()
            if co:
                self._lbl_checkout.setText(f"⬤  active: {co.name}")
                self._lbl_checkout.setToolTip(
                    f"New prompts will be added to: {co.name}")
                return
        self._lbl_checkout.setText("")


    def _fork_from_prompt(self, branch: Branch, prompt_id: str) -> None:
        """Fork from a specific prompt (right-click context menu)."""
        if not branch or not self._active_tree:
            return
        try:
            fork_index = branch.prompt_ids.index(prompt_id)
        except ValueError:
            fork_index = max(0, len(branch.prompt_ids) - 1)
        self._do_fork(branch, fork_index)

    def _fork_from_selection(self) -> None:
        """Fork from the currently selected prompt (toolbar button)."""
        if not self._active_branch_id or not self._active_tree:
            QMessageBox.information(
                self, "No selection",
                "Click a prompt node in the graph first, then press Fork.")
            return
        branch = self._active_tree.get_branch(self._active_branch_id)
        if not branch:
            return
        if self._active_prompt_id and self._active_prompt_id in branch.prompt_ids:
            fork_index = branch.prompt_ids.index(self._active_prompt_id)
        else:
            fork_index = max(0, len(branch.prompt_ids) - 1)
        self._do_fork(branch, fork_index)

    def _do_fork(self, parent_branch: Branch, fork_index: int) -> None:
        dlg = ForkDialog(
            parent_branch_name=parent_branch.name,
            prompt_count=len(parent_branch.prompt_ids),
            default_index=fork_index,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.get_values()
        if not vals["name"]:
            QMessageBox.warning(self, "Name required",
                                "Please enter a name for the new branch.")
            return

        child = self._active_tree.add_branch(
            name=vals["name"],
            parent_branch_id=parent_branch.id,
            fork_index=vals["fork_index"],
            trigger=vals["trigger"],
            reason=vals["reason"],
            context_summary=vals["context_summary"],
        )
        if child:
            self._active_tree.updated_at = datetime.now()
            self._mw.prompt_database.save_tree(self._active_tree)
            self._redraw_graph()
            self.branch_forked.emit(
                self._active_tree.name, parent_branch.name,
                child.name, vals["trigger"])
            if hasattr(self._mw, "log"):
                self._mw.log(
                    f"Forked '{parent_branch.name}' → new branch '{child.name}'.")


    def _merge_from_selection(self) -> None:
        if not self._active_branch_id or not self._active_tree:
            QMessageBox.information(
                self, "No selection",
                "Select a prompt node first to identify the branch to merge.")
            return
        branch = self._active_tree.get_branch(self._active_branch_id)
        if branch:
            self._do_merge(branch)

    def _do_merge(self, source: Branch) -> None:
        if len(self._active_tree.get_visible_branches()) < 2:
            QMessageBox.information(
                self, "Cannot merge", "Need at least two branches.")
            return
        dlg = MergeDialog(source, self._active_tree, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.get_values()
        if not vals["target_branch_id"]:
            return
        ok = self._active_tree.merge_branch(
            source_branch_id=source.id,
            target_branch_id=vals["target_branch_id"],
            merge_insights=vals["insights"],
            include_unique_prompts=vals["include_prompts"],
        )
        if ok:
            self._mw.prompt_database.save_tree(self._active_tree)
            self._redraw_graph()
            target = self._active_tree.get_branch(vals["target_branch_id"])
            self.branch_merged.emit(
                self._active_tree.name, source.name, vals["insights"])
            if hasattr(self._mw, "log"):
                self._mw.log(
                    f"Merged '{source.name}' → '{target.name if target else '?'}'.")


    def _eadr_from_selection(self) -> None:
        if not self._active_tree or not self._active_branch_id:
            return
        branch = self._active_tree.get_branch(self._active_branch_id)
        if not branch:
            return
        if hasattr(self._mw, "_eadr_panel"):
            ctx = f"[Branch: {branch.name} | Tree: {self._active_tree.name}]\n"
            self._mw.prompt_database.add_eadr_note(
                ctx + "Add findings here…",
                self._mw._eadr_panel.project)
            self._mw._eadr_panel.refresh()
            self._mw._tabs.setCurrentWidget(self._mw._eadr_panel)


    def _copy_prompt_from_selection(self) -> None:
        db = getattr(self._mw, "prompt_database", None)
        if not db or not self._active_prompt_id:
            return
        p = db.get_prompt(self._active_prompt_id)
        if p:
            QApplication.clipboard().setText(p.prompt_text or "")
            if hasattr(self._mw, "log"):
                self._mw.log("Prompt text copied to clipboard.")


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\help_panel.py

"""Help and About panels for the LLM Buddy Qt GUI."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser

from llm_buddy.qt.theme import get_theme_colors, current_theme_name


class HelpPanel(QWidget):
    """Static help text displayed with rich HTML formatting.

    Re-renders on :meth:`showEvent` so colors adapt to theme changes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setHtml(self._help_html())
        layout.addWidget(self._browser)

    def showEvent(self, event):
        """Re-render HTML so colors match the active theme."""
        super().showEvent(event)
        self._browser.setHtml(self._help_html())

    @staticmethod
    def _help_html() -> str:
        c = get_theme_colors(current_theme_name())
        return f"""\
<h2 style="color: {c['accent']};">LLM Buddy &ndash; Usage Tips</h2>

<h3>Getting Started</h3>
<ol>
<li><b>Adding Items</b> &ndash; Click <i>Add Folder</i> or <i>Add File(s)</i>
    in the control panel.</li>
<li><b>Scanning Folders</b> &ndash; Use <i>Scan Folders</i> to search for
    files matching the configured extensions.</li>
<li><b>Filtering</b> &ndash; Adjust extensions, minimum token count, and
    ignored folder names, then click <i>Apply Filters</i>.</li>
<li><b>Preview &amp; Token Counts</b> &ndash; The <i>Preview</i> tab shows
    the combined text with live token counts.</li>
<li><b>Combining Scripts</b> &ndash; Click <i>Combine Scripts</i>
    (<code>Ctrl+Shift+C</code>) to generate a markdown backup file.</li>
<li><b>Profiles</b> &ndash; Save and restore your settings as named
    profiles.</li>
</ol>

<h3>Feature Tabs</h3>
<ul>
<li><b>Research Notes</b> &ndash; Add progress notes about your project.
    Notes are also created automatically when you combine scripts.</li>
<li><b>Rollback</b> &ndash; Restore files from a previous backup. Select
    a backup file, review the diff, and restore.</li>
<li><b>Prompt Tracking &amp; Capture</b>
    <ul>
    <li><b>Browser Extension</b> &ndash; Start the server, install the
        Chrome extension, and prompts from ChatGPT&nbsp;/&nbsp;Claude&nbsp;/
        Gemini&nbsp;/&nbsp;Perplexity are captured automatically.</li>
    <li><b>Proxy Recorder</b> &ndash; Click <i>Setup Guide</i> for one-time
        browser-proxy and CA-certificate setup.</li>
    <li><b>Claude Desktop (MCP)</b> &ndash; Run <code>llm-buddy configure</code>
        then restart Claude Desktop.</li>
    <li><b>Manual Entry</b> &ndash; Use the <i>New Prompt</i> form.</li>
    </ul></li>
<li><b>Auto-Backup</b> &ndash; Monitor files/folders and create backups
    automatically when significant changes are detected.</li>
<li><b>Analytics Dashboard</b> &ndash; Charts showing prompt frequency,
    LLM distribution, token usage trends, and an activity timeline.</li>
<li><b>Research Sessions</b> &ndash; Start a named session to group work
    into bounded periods. End the session to auto-generate a structured
    summary.</li>
</ul>

<h3>Keyboard Shortcuts</h3>
<table cellpadding="4" cellspacing="0" style="border-collapse: collapse;">
<tr style="background: {c['hover']};">
    <td style="padding: 4px 12px;"><code>Ctrl+1</code>&hellip;<code>Ctrl+0</code></td>
    <td style="padding: 4px 12px;">Switch between tabs 1&ndash;10</td></tr>
<tr><td style="padding: 4px 12px;"><code>Ctrl+Shift+C</code></td>
    <td style="padding: 4px 12px;">Combine Scripts</td></tr>
<tr style="background: {c['hover']};">
    <td style="padding: 4px 12px;"><code>Ctrl+Q</code></td>
    <td style="padding: 4px 12px;">Quit application</td></tr>
</table>
"""


class AboutPanel(QWidget):
    """Static about information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setHtml(self._about_html())
        layout.addWidget(self._browser)

    @staticmethod
    def _about_html() -> str:
        return """\
<h2>About LLM Buddy</h2>
<p><b>Prompt Recording &amp; Management &ndash; Version 3.0</b></p>
<p>Created by <b>Anthony Vigil</b>
   (<a href="mailto:anthony.vigil@usf.edu">anthony.vigil@usf.edu</a>)</p>
<p>Copyright &copy; 2025 Anthony Vigil. All rights reserved.</p>
<p>LLM Buddy helps you record, manage, and analyse your interactions
with Large Language Models across multiple services and capture methods.</p>
<h3>Technology</h3>
<ul>
<li>Python 3.x</li>
<li>PySide6 / Qt 6 (LGPL v3) for the GUI</li>
<li>tiktoken for GPT-style token counting</li>
<li>watchdog for file-change monitoring</li>
<li>Flask for the browser-extension API</li>
<li>mitmproxy for proxy-based prompt capture</li>
</ul>
<p><i>Legal Notice:</i> This software is provided &ldquo;as-is&rdquo;
without any express or implied warranty.</p>
"""


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\log_panel.py

"""Log panel for the LLM Buddy Qt GUI.

Rich log output with severity-based coloring, search/filter toolbar,
auto-scroll toggle, and monospace formatting.
"""

import re
from datetime import datetime

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QCheckBox, QLabel, QPushButton,
)

from llm_buddy.qt.theme import get_theme_colors, current_theme_name

# Severity detection patterns
_ERROR_RE = re.compile(
    r"\b(error|fail|exception|critical|fatal)\b", re.IGNORECASE)
_WARN_RE = re.compile(
    r"\b(warn|warning|caution)\b", re.IGNORECASE)
_SUCCESS_RE = re.compile(
    r"\b(started|success|saved|recorded|completed|connected|loaded)\b",
    re.IGNORECASE)


class LogPanel(QWidget):
    """Rich log output panel with severity coloring and search.

    Other panels call :meth:`append` (or connect signals) to add log
    messages. The timestamp is prepended automatically.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_entries: list[tuple[str, str]] = []  # (html, plain)
        self._auto_scroll = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(6, 4, 6, 4)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(
            "\U0001f50d Filter logs\u2026")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search_edit, stretch=1)

        self._auto_scroll_cb = QCheckBox("Auto-scroll")
        self._auto_scroll_cb.setChecked(True)
        self._auto_scroll_cb.toggled.connect(self._set_auto_scroll)
        toolbar.addWidget(self._auto_scroll_cb)

        self._count_label = QLabel("0 entries")
        self._count_label.setStyleSheet("color: gray; padding: 0 8px;")
        toolbar.addWidget(self._count_label)

        btn_clear = QPushButton("Clear")
        btn_clear.setProperty("class", "danger")
        btn_clear.clicked.connect(self.clear_log)
        toolbar.addWidget(btn_clear)

        layout.addLayout(toolbar)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 10))
        self._text.setLineWrapMode(QTextEdit.WidgetWidth)
        layout.addWidget(self._text)

    @Slot(str)
    def append(self, message: str) -> None:
        """Append a timestamped, severity-colored message."""
        ts = datetime.now().strftime("%H:%M:%S")
        plain = f"{ts} \u2013 {message}"

        # Detect severity and pick color
        colors = get_theme_colors(current_theme_name())
        if _ERROR_RE.search(message):
            color = colors["error"]
            icon = "\U0001f534"
        elif _WARN_RE.search(message):
            color = colors["warning"]
            icon = "\U0001f7e0"
        elif _SUCCESS_RE.search(message):
            color = colors["success"]
            icon = "\U0001f7e2"
        else:
            color = colors["muted"]
            icon = "\u2022"

        html = (
            f'<div style="margin:1px 0; padding:2px 4px;">'
            f'<span style="color:{colors["muted"]}">{ts}</span> '
            f'{icon} '
            f'<span style="color:{color}">{message}</span>'
            f'</div>'
        )
        self._all_entries.append((html, plain))
        self._count_label.setText(f"{len(self._all_entries)} entries")

        # If filter is active, only append if it matches
        filter_text = self._search_edit.text().strip().lower()
        if filter_text and filter_text not in plain.lower():
            return

        self._text.append(html)
        if self._auto_scroll:
            self._text.moveCursor(QTextCursor.End)

    def clear_log(self) -> None:
        self._all_entries.clear()
        self._text.clear()
        self._count_label.setText("0 entries")

    @Slot(str)
    def _apply_filter(self, text: str) -> None:
        """Re-render log entries matching the filter."""
        needle = text.strip().lower()
        self._text.clear()
        for html, plain in self._all_entries:
            if not needle or needle in plain.lower():
                self._text.append(html)
        if self._auto_scroll:
            self._text.moveCursor(QTextCursor.End)

    @Slot(bool)
    def _set_auto_scroll(self, enabled: bool) -> None:
        self._auto_scroll = enabled
        if enabled:
            self._text.moveCursor(QTextCursor.End)


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\preview_panel.py

"""Preview panel for the Qt GUI.

Shows the combined text of all filtered files with live token counts.
Listens for ``files_changed`` signals to auto-refresh.
"""

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
)

from llm_buddy.core.tokens import (
    build_combined_text, build_content_only_text, count_tokens,
)


class PreviewPanel(QWidget):
    """Read-only preview of the combined file content with token counts."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        layout.addWidget(self._text, stretch=1)

        token_row = QHBoxLayout()
        self._tok_with = QLabel("Tokens (with headers): 0")
        token_row.addWidget(self._tok_with)
        self._tok_without = QLabel("Tokens (without headers): 0")
        token_row.addWidget(self._tok_without)
        token_row.addStretch()
        layout.addLayout(token_row)

    @Slot(list)
    def update_preview(self, filtered_files=None) -> None:
        """Rebuild the preview text and token counts.

        *filtered_files* is a list of ``(path, tokens)`` tuples.
        If ``None``, uses ``main_window.filtered_files``.
        """
        filtered = filtered_files or self._mw.filtered_files
        file_paths = [p for p, _t in filtered]

        header = ""
        footer = ""
        if hasattr(self._mw, '_control_panel'):
            header = self._mw._control_panel.header
            footer = self._mw._control_panel.footer

        full_text = build_combined_text(file_paths, header, footer)
        self._text.setPlainText(full_text)

        full_tokens = count_tokens(full_text)
        content_only = build_content_only_text(file_paths)
        content_tokens = count_tokens(content_only)

        self._tok_with.setText(
            f"Tokens (with headers): {full_tokens:,}")
        self._tok_without.setText(
            f"Tokens (without headers): {content_tokens:,}")

        self._mw.log(
            f"Preview updated. Tokens (with headers): {full_tokens:,}; "
            f"(without): {content_tokens:,}")


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\prompts_panel.py

"""Prompt Tracking panel for the Qt GUI.

PySide6 port of the tkinter PromptsMixin.  Provides prompt recording,
history browsing, file association management, active-prompt tracking,
export, and retroactive association via a modal dialog.
"""

import os
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QStandardItemModel, QStandardItem, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QComboBox, QPlainTextEdit, QCheckBox,
    QPushButton, QTabWidget, QTreeView, QTextBrowser,
    QSplitter, QHeaderView, QMessageBox, QFileDialog,
    QInputDialog, QDialog, QRadioButton, QButtonGroup,
    QSpinBox, QScrollArea, QAbstractItemView,
)

from llm_buddy.core.database import PromptRecord

# Type-only imports for constructor params
from llm_buddy.qt.panels.capture_widgets import (
    ExtensionServerWidget,
    ProxyRecorderWidget,
)


class PromptsPanel(QWidget):
    """Prompt tracking panel with capture sources, entry form, history,
    file associations, detail display, and action buttons.
    """

    def __init__(
        self,
        main_window,
        extension_widget: ExtensionServerWidget,
        proxy_widget: ProxyRecorderWidget,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._mw = main_window
        self._ext_widget = extension_widget
        self._proxy_widget = proxy_widget

        # Track last-selected prompt id for stable refresh
        self._selected_prompt_id: Optional[str] = None
        # Track which sub-tree had focus for Set Active / Delete
        self._last_focused_tree: Optional[QTreeView] = None

        self._build_ui()

        # Auto-refresh timer (polls DB for new prompts from MCP / proxy / ext)
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(10_000)
        self._auto_refresh_timer.timeout.connect(self._auto_refresh_tick)
        self._auto_refresh_timer.start()

        # Initial population
        self.refresh_prompt_history()
        self.refresh_file_list()
        self.update_active_prompt_display()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        # Use a scroll area so the panel never clips on small windows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        # Make the scroll area and its inner container transparent so
        # the tab pane background shows through, matching other tabs.
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)

        capture_group = QGroupBox("Capture Sources")
        cap_lay = QVBoxLayout(capture_group)
        hint = QLabel(
            "Prompts are captured automatically when a source is "
            "running. Start a source below, or record manually."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        cap_lay.addWidget(hint)
        cap_lay.addWidget(self._ext_widget)
        cap_lay.addWidget(self._proxy_widget)
        layout.addWidget(capture_group)

        entry_group = QGroupBox("New Prompt")
        eg = QVBoxLayout(entry_group)

        # Row 1: description
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Description:"))
        self._desc_edit = QLineEdit()
        r1.addWidget(self._desc_edit, stretch=1)
        eg.addLayout(r1)

        # Row 2: LLM used
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("LLM Used:"))
        self._llm_combo = QComboBox()
        self._llm_combo.addItems(
            ["Claude", "GPT-4", "GPT-3.5", "Llama", "Other"])
        self._llm_combo.setCurrentText("Claude")
        r2.addWidget(self._llm_combo, stretch=1)
        eg.addLayout(r2)

        # Row 3: prompt text
        eg.addWidget(QLabel("Prompt Text:"))
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setPlaceholderText("Enter your prompt here...")
        self._prompt_edit.setMinimumHeight(100)
        eg.addWidget(self._prompt_edit)

        # Row 4: files checkbox
        self._use_all_files_cb = QCheckBox(
            "Use All Currently Selected Files")
        self._use_all_files_cb.setChecked(True)
        eg.addWidget(self._use_all_files_cb)

        # Row 5: buttons
        btn_row = QHBoxLayout()
        btn_record = QPushButton("Record Prompt")
        btn_record.setProperty("class", "primary")
        btn_record.clicked.connect(self._record_prompt)
        btn_row.addWidget(btn_record)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self._clear_prompt_fields)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        eg.addLayout(btn_row)

        # Ctrl+Enter records the prompt while the text box has focus
        sc_record = QShortcut(QKeySequence("Ctrl+Return"), self._prompt_edit)
        sc_record.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc_record.activated.connect(self._record_prompt)

        layout.addWidget(entry_group)

        active_group = QGroupBox("Active Prompt")
        ag = QHBoxLayout(active_group)
        self._active_label = QLabel("No active prompt")
        font = self._active_label.font()
        font.setItalic(True)
        font.setPointSize(10)
        self._active_label.setFont(font)
        ag.addWidget(self._active_label, stretch=1)
        btn_clear_active = QPushButton("Clear Active Prompt")
        btn_clear_active.clicked.connect(self._clear_active_prompt)
        ag.addWidget(btn_clear_active)
        layout.addWidget(active_group)

        splitter = QSplitter(Qt.Vertical)

        self._sub_tabs = QTabWidget()

        # -- Prompt History tab --
        history_w = QWidget()
        hw_lay = QVBoxLayout(history_w)
        hw_lay.setContentsMargins(0, 0, 0, 0)

        self._history_model = QStandardItemModel()
        self._history_model.setHorizontalHeaderLabels(
            ["Date & Time", "LLM", "Description", "Files", "Source"])
        self._history_tree = QTreeView()
        self._history_tree.setModel(self._history_model)
        self._history_tree.setRootIsDecorated(False)
        self._history_tree.setAlternatingRowColors(True)
        self._history_tree.setSelectionMode(QTreeView.SingleSelection)
        self._history_tree.setEditTriggers(QTreeView.NoEditTriggers)
        self._history_tree.header().setSectionResizeMode(
            QHeaderView.Interactive)
        self._history_tree.selectionModel().selectionChanged.connect(
            self._on_history_selection)
        # Track focus for Set Active / Delete
        self._history_tree.clicked.connect(
            lambda: self._set_last_focused(self._history_tree))

        self._history_empty_label = QLabel(
            "No prompts recorded yet\n\n"
            "Start the  Proxy Recorder,  Chrome Extension,\n"
            "or use the manual form below")
        self._history_empty_label.setAlignment(Qt.AlignCenter)
        self._history_empty_label.setStyleSheet(
            "color: palette(mid); padding: 24px;")
        hw_lay.addWidget(self._history_empty_label)
        hw_lay.addWidget(self._history_tree)
        self._sub_tabs.addTab(history_w, "Prompt History")

        # -- File Associations tab --
        fa_w = QWidget()
        fa_lay = QVBoxLayout(fa_w)
        fa_lay.setContentsMargins(0, 0, 0, 0)

        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Select File:"))
        self._file_combo = QComboBox()
        self._file_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._file_combo.setMinimumContentsLength(40)
        self._file_combo.currentIndexChanged.connect(self._show_file_prompts)
        sel_row.addWidget(self._file_combo, stretch=1)
        btn_refresh_files = QPushButton("Refresh")
        btn_refresh_files.clicked.connect(self.refresh_file_list)
        sel_row.addWidget(btn_refresh_files)
        fa_lay.addLayout(sel_row)

        self._file_model = QStandardItemModel()
        self._file_model.setHorizontalHeaderLabels(
            ["Date & Time", "LLM", "Description", "Files", "Source"])
        self._file_tree = QTreeView()
        self._file_tree.setModel(self._file_model)
        self._file_tree.setRootIsDecorated(False)
        self._file_tree.setAlternatingRowColors(True)
        self._file_tree.setSelectionMode(QTreeView.SingleSelection)
        self._file_tree.setEditTriggers(QTreeView.NoEditTriggers)
        self._file_tree.header().setSectionResizeMode(
            QHeaderView.Interactive)
        self._file_tree.selectionModel().selectionChanged.connect(
            self._on_file_tree_selection)
        self._file_tree.clicked.connect(
            lambda: self._set_last_focused(self._file_tree))
        fa_lay.addWidget(self._file_tree)
        self._sub_tabs.addTab(fa_w, "File Associations")

        splitter.addWidget(self._sub_tabs)

        detail_group = QGroupBox("Prompt Details")
        dg = QVBoxLayout(detail_group)
        self._detail_browser = QTextBrowser()
        self._detail_browser.setPlaceholderText(
            "Select a prompt to view its details.")
        self._detail_browser.setOpenExternalLinks(False)
        dg.addWidget(self._detail_browser)
        splitter.addWidget(detail_group)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

        action_row = QHBoxLayout()
        btn_set_active = QPushButton("Set as Active Prompt")
        btn_set_active.clicked.connect(self._set_active_prompt)
        action_row.addWidget(btn_set_active)

        btn_export = QPushButton("Export Prompt History")
        btn_export.clicked.connect(self._export_prompt_history)
        action_row.addWidget(btn_export)

        btn_retro = QPushButton("Retroactive Association")
        btn_retro.clicked.connect(self._open_retroactive_dialog)
        action_row.addWidget(btn_retro)

        btn_add_to_branch = QPushButton("Add to Branch")
        btn_add_to_branch.setToolTip(
            "Add selected prompt to a conversation branch "
            "(Prompt Explorer tab)")
        btn_add_to_branch.clicked.connect(self._add_to_branch)
        action_row.addWidget(btn_add_to_branch)

        action_row.addStretch()

        btn_delete = QPushButton("Delete Selected Prompt")
        btn_delete.clicked.connect(self._delete_prompt)
        action_row.addWidget(btn_delete)

        layout.addLayout(action_row)

        outer.addWidget(scroll)


    def _set_last_focused(self, tree: QTreeView) -> None:
        self._last_focused_tree = tree

    def _active_tree(self) -> Optional[QTreeView]:
        """Return whichever tree the user last clicked in."""
        return self._last_focused_tree


    def start_auto_refresh(self) -> None:
        """Called by capture widgets when a source starts."""
        if not self._auto_refresh_timer.isActive():
            self._auto_refresh_timer.start()

    @Slot()
    def _auto_refresh_tick(self) -> None:
        ext_on = self._ext_widget._status.text() == "Running"
        proxy_on = "Running" in self._proxy_widget._status.text()
        # Always reload — MCP recorder runs externally (via Claude
        # Desktop) and has no in-app status widget.
        prev_count = len(self._mw.prompt_database.prompts)
        self._mw.prompt_database.load()
        if len(self._mw.prompt_database.prompts) != prev_count:
            self.refresh_prompt_history()


    @Slot()
    def _record_prompt(self) -> None:
        """Record a new prompt and set it as active."""
        prompt_text = self._prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(
                self, "Empty Prompt",
                "Please enter prompt text before recording.")
            return

        description = self._desc_edit.text().strip()
        llm_used = self._llm_combo.currentText()
        record = PromptRecord(prompt_text, llm_used, description)

        if self._use_all_files_cb.isChecked():
            for fp_tuple in self._mw.filtered_files:
                # filtered_files is a list of (path, tokens) tuples
                fp = fp_tuple[0] if isinstance(fp_tuple, (list, tuple)) else fp_tuple
                record.associated_files.append(fp)

        self._mw.prompt_database.add_prompt(prompt_record=record)
        self._mw.log(f"Recorded new prompt: {description or 'Untitled'}")
        self.refresh_prompt_history()
        self.update_active_prompt_display()
        self._clear_prompt_fields()

        self._mw.show_toast("Prompt recorded and set as active.", "success")

    @Slot()
    def _clear_prompt_fields(self) -> None:
        self._desc_edit.clear()
        self._prompt_edit.clear()

    @Slot()
    def _delete_prompt(self) -> None:
        tree = self._active_tree()
        if tree is None:
            return
        model = tree.model()
        indexes = tree.selectionModel().selectedRows()
        if not indexes:
            return

        answer = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this prompt record?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        row = indexes[0].row()
        prompt_id = model.item(row, 0).data(Qt.UserRole)
        if prompt_id is None:
            return

        db = self._mw.prompt_database
        prompt = db.get_prompt(prompt_id)
        if prompt is None:
            return

        if db.active_prompt and db.active_prompt.id == prompt_id:
            db.clear_active_prompt()
            self.update_active_prompt_display()

        db.delete_prompt(prompt_id)
        self._mw.log(
            f"Deleted prompt: {prompt.description or 'Untitled'}")
        self.refresh_prompt_history()
        self._show_file_prompts()
        self._detail_browser.clear()


    @Slot()
    def _add_to_branch(self) -> None:
        """Send the selected prompt to the Prompt Explorer panel."""
        tree = self._active_tree()
        if tree is None:
            return
        model = tree.model()
        indexes = tree.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(
                self, "No Selection",
                "Select a prompt first.")
            return

        row = indexes[0].row()
        prompt_id = model.item(row, 0).data(Qt.UserRole)
        if not prompt_id:
            return

        # Delegate to the Prompt Explorer panel
        forking_panel = getattr(self._mw, "_forking_panel", None)
        if forking_panel is None:
            QMessageBox.warning(
                self, "Unavailable",
                "Prompt Explorer panel not found.")
            return

        forking_panel.add_prompt_to_branch(prompt_id)


    def refresh_prompt_history(self) -> None:
        """Reload the prompt history tree from the database."""
        # Remember current selection
        sel_indexes = self._history_tree.selectionModel().selectedRows()
        prev_id = None
        if sel_indexes:
            prev_id = self._history_model.item(
                sel_indexes[0].row(), 0)
            prev_id = prev_id.data(Qt.UserRole) if prev_id else None

        self._history_model.removeRows(0, self._history_model.rowCount())

        sorted_prompts = sorted(
            self._mw.prompt_database.prompts,
            key=lambda p: p.timestamp, reverse=True)

        restore_row = -1
        for idx, prompt in enumerate(sorted_prompts):
            ts = prompt.timestamp.strftime("%Y-%m-%d %H:%M")
            fc = str(len(prompt.associated_files))
            source = self._infer_source(prompt)

            ts_item = QStandardItem(ts)
            ts_item.setData(prompt.id, Qt.UserRole)
            ts_item.setEditable(False)
            ts_item.setToolTip(ts)

            llm_item = QStandardItem(prompt.llm_used)
            llm_item.setEditable(False)

            desc_item = QStandardItem(prompt.description)
            desc_item.setEditable(False)
            desc_item.setToolTip(prompt.description)

            fc_item = QStandardItem(fc)
            fc_item.setEditable(False)

            src_item = QStandardItem(source)
            src_item.setEditable(False)

            self._history_model.appendRow(
                [ts_item, llm_item, desc_item, fc_item, src_item])

            if prompt.id == prev_id:
                restore_row = idx

        # Toggle empty-state label
        has_prompts = self._history_model.rowCount() > 0
        self._history_empty_label.setVisible(not has_prompts)
        self._history_tree.setVisible(has_prompts)

        # Restore selection
        if restore_row >= 0:
            sel_index = self._history_model.index(restore_row, 0)
            self._history_tree.selectionModel().select(
                sel_index,
                self._history_tree.selectionModel().ClearAndSelect
                | self._history_tree.selectionModel().Rows,
            )
            self._show_prompt_detail(prev_id)

    @staticmethod
    def _infer_source(prompt: PromptRecord) -> str:
        """Heuristic to determine a prompt's origin."""
        if hasattr(prompt, "source") and prompt.source and prompt.source != "Unknown":
            return prompt.source

        desc = (prompt.description or "").lower()
        llm = prompt.llm_used or ""

        if "auto-recorded from claude desktop" in desc:
            return "Claude Desktop"
        if "browser extension" in desc or "captured" in desc:
            return "Browser Extension"
        if "proxy" in desc:
            return "Proxy"
        if llm == "Claude" and any(
            k in desc for k in ("mcp", "auto-recorded", "claude desktop")
        ):
            return "Claude Desktop"
        if any(k in desc for k in ("web", "browser", "via", "claude.ai")):
            return "Browser Extension"
        if any(n in llm for n in ("ChatGPT", "Gemini", "Perplexity")):
            return "Browser Extension"
        return "Manual"

    def _show_prompt_detail(self, prompt_id: str) -> None:
        """Populate the detail browser for the given prompt ID."""
        prompt = self._mw.prompt_database.get_prompt(prompt_id)
        if not prompt:
            self._detail_browser.clear()
            return

        lines = []
        lines.append(f"<b>Description:</b> {prompt.description}")
        lines.append(
            f"<b>Date &amp; Time:</b> "
            f"{prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"<b>LLM Used:</b> {prompt.llm_used}")
        lines.append(f"<b>Source:</b> {self._infer_source(prompt)}")
        lines.append("")

        lines.append("<b>Associated Files:</b>")
        if prompt.associated_files:
            for fp in prompt.associated_files:
                change = prompt.file_changes.get(fp, "Unknown")
                lines.append(f"&nbsp;&nbsp;- {fp} (Token change: {change})")
        else:
            lines.append("&nbsp;&nbsp;No associated files")

        if hasattr(prompt, "retroactive_notes") and prompt.retroactive_notes:
            lines.append("")
            lines.append("<b>Retroactive Associations:</b>")
            for ts, nd in prompt.retroactive_notes.items():
                files = nd.get("files", [])
                notes = nd.get("notes", "")
                lines.append(f"&nbsp;&nbsp;- {ts}: {len(files)} files")
                lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;Note: {notes}")

        lines.append("")
        lines.append("<b>--- Prompt (Input) ---</b>")
        lines.append(f"<pre>{prompt.prompt_text or ''}</pre>")

        response = getattr(prompt, "response_text", "") or ""
        lines.append("")
        lines.append("<b>--- Response (Output) ---</b>")
        if response:
            lines.append(f"<pre>{response}</pre>")
        else:
            lines.append("(No response captured)")

        self._detail_browser.setHtml("<br>".join(lines))

    @Slot()
    def _on_history_selection(self) -> None:
        indexes = self._history_tree.selectionModel().selectedRows()
        if not indexes:
            return
        row = indexes[0].row()
        item = self._history_model.item(row, 0)
        if item:
            prompt_id = item.data(Qt.UserRole)
            self._selected_prompt_id = prompt_id
            self._set_last_focused(self._history_tree)
            self._show_prompt_detail(prompt_id)

    @Slot()
    def _on_file_tree_selection(self) -> None:
        indexes = self._file_tree.selectionModel().selectedRows()
        if not indexes:
            return
        row = indexes[0].row()
        item = self._file_model.item(row, 0)
        if item:
            prompt_id = item.data(Qt.UserRole)
            self._selected_prompt_id = prompt_id
            self._set_last_focused(self._file_tree)
            self._show_prompt_detail(prompt_id)


    @Slot()
    def refresh_file_list(self) -> None:
        """Refresh the file combo for the File Associations tab."""
        all_files: set = set()
        for fp_tuple in self._mw.filtered_files:
            fp = fp_tuple[0] if isinstance(fp_tuple, (list, tuple)) else fp_tuple
            all_files.add(fp)
        for p in self._mw.prompt_database.prompts:
            all_files.update(p.associated_files)

        prev = self._file_combo.currentText()
        self._file_combo.blockSignals(True)
        self._file_combo.clear()
        self._file_combo.addItems(sorted(all_files))
        self._file_combo.blockSignals(False)

        # Restore or pick first
        idx = self._file_combo.findText(prev)
        if idx >= 0:
            self._file_combo.setCurrentIndex(idx)
        elif self._file_combo.count() > 0:
            self._file_combo.setCurrentIndex(0)
        self._show_file_prompts()

    @Slot()
    def _show_file_prompts(self) -> None:
        """Show prompts associated with the selected file."""
        self._file_model.removeRows(0, self._file_model.rowCount())
        fp = self._file_combo.currentText()
        if not fp:
            return

        file_prompts = self._mw.prompt_database.get_prompts_for_file(fp)
        for prompt in sorted(
            file_prompts, key=lambda p: p.timestamp, reverse=True
        ):
            ts = prompt.timestamp.strftime("%Y-%m-%d %H:%M")
            fc = str(len(prompt.associated_files))
            source = self._infer_source(prompt)

            ts_item = QStandardItem(ts)
            ts_item.setData(prompt.id, Qt.UserRole)
            ts_item.setEditable(False)
            ts_item.setToolTip(ts)

            llm_item = QStandardItem(prompt.llm_used)
            llm_item.setEditable(False)

            desc_item = QStandardItem(prompt.description)
            desc_item.setEditable(False)
            desc_item.setToolTip(prompt.description)

            fc_item = QStandardItem(fc)
            fc_item.setEditable(False)

            src_item = QStandardItem(source)
            src_item.setEditable(False)

            self._file_model.appendRow(
                [ts_item, llm_item, desc_item, fc_item, src_item])


    @Slot()
    def _set_active_prompt(self) -> None:
        tree = self._active_tree()
        if tree is None:
            QMessageBox.information(
                self, "No Selection",
                "Please select a prompt to set as active.")
            return

        indexes = tree.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(
                self, "No Selection",
                "Please select a prompt to set as active.")
            return

        row = indexes[0].row()
        model = tree.model()
        prompt_id = model.item(row, 0).data(Qt.UserRole)
        prompt = self._mw.prompt_database.get_prompt(prompt_id)
        if prompt:
            self._mw.prompt_database.active_prompt = prompt
            self.update_active_prompt_display()
            self._mw.log(
                f"Set active prompt: {prompt.description or 'Untitled'}")
            self._mw.show_toast("Active prompt set.", "success")

    @Slot()
    def _clear_active_prompt(self) -> None:
        if self._mw.prompt_database.active_prompt:
            self._mw.prompt_database.clear_active_prompt()
            self.update_active_prompt_display()
            self._mw.log("Cleared active prompt")

    def update_active_prompt_display(self) -> None:
        """Update the active-prompt label."""
        ap = self._mw.prompt_database.active_prompt
        if ap:
            desc = ap.description or "Untitled"
            ts = ap.timestamp.strftime("%Y-%m-%d %H:%M")
            self._active_label.setText(
                f"Active Prompt: {desc} ({ts}, {ap.llm_used})")
            font = self._active_label.font()
            font.setItalic(False)
            font.setBold(True)
            font.setPointSize(10)
            self._active_label.setFont(font)
            self._active_label.setStyleSheet("color: green;")
        else:
            self._active_label.setText("No active prompt")
            font = self._active_label.font()
            font.setItalic(True)
            font.setBold(False)
            font.setPointSize(10)
            self._active_label.setFont(font)
            self._active_label.setStyleSheet("color: black;")


    @Slot()
    def _export_prompt_history(self) -> None:
        """Export prompt history to a markdown file."""
        output_dir = "prompts"
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"prompt_history_{ts}.md")

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(
                    f"# Prompt History Export\nGenerated: "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                sorted_prompts = sorted(
                    self._mw.prompt_database.prompts,
                    key=lambda p: p.timestamp, reverse=True)

                for i, prompt in enumerate(sorted_prompts, 1):
                    f.write(
                        f"## {i}. "
                        f"{prompt.description or 'Untitled Prompt'}\n\n")
                    f.write(
                        f"- **Date & Time:** "
                        f"{prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"- **LLM Used:** {prompt.llm_used}\n")
                    f.write(f"- **ID:** {prompt.id}\n\n")
                    f.write("### Prompt Text (Input)\n\n```\n")
                    f.write(prompt.prompt_text)
                    f.write("\n```\n\n")

                    response = getattr(prompt, "response_text", "") or ""
                    if response:
                        f.write("### Response (Output)\n\n```\n")
                        f.write(response)
                        f.write("\n```\n\n")

                    f.write("### Associated Files\n\n")
                    if prompt.associated_files:
                        for fp in prompt.associated_files:
                            change = prompt.file_changes.get(fp, "Unknown")
                            f.write(
                                f"- `{fp}` (Token change: {change})\n")
                    else:
                        f.write("No files associated with this prompt.\n")

                    if (hasattr(prompt, "retroactive_notes")
                            and prompt.retroactive_notes):
                        f.write("\n### Retroactive Associations\n\n")
                        for rts, nd in prompt.retroactive_notes.items():
                            f.write(
                                f"**{rts}**\n\n"
                                f"- Token Change: {nd['token_change']}\n")
                            f.write(
                                f"- Notes: {nd['notes']}\n- Files:\n")
                            for rf in nd["files"]:
                                f.write(f"  - `{rf}`\n")
                    f.write("\n---\n\n")

            self._mw.log(f"Exported prompt history to {output_file}")
            self._mw.show_toast(
                f"Exported to: {os.path.basename(output_file)}", "success")

        except Exception as e:
            self._mw.log(f"Error exporting prompt history: {e}")
            QMessageBox.critical(
                self, "Export Error",
                f"Failed to export prompt history:\n{e}")


    @Slot()
    def _open_retroactive_dialog(self) -> None:
        db = self._mw.prompt_database
        if not db.prompts:
            QMessageBox.information(
                self, "No Prompts",
                "No prompts have been recorded yet. "
                "Please record a prompt first.")
            return

        dlg = _RetroactiveDialog(self._mw, self, parent=self)
        dlg.exec()

        # Refresh after dialog closes
        self.refresh_prompt_history()
        self.refresh_file_list()


class _RetroactiveDialog(QDialog):
    """Modal dialog for retroactively associating files with a prompt."""

    def __init__(self, main_window, panel: PromptsPanel,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._mw = main_window
        self._panel = panel
        self.setWindowTitle("Retroactive Prompt Association")
        self.resize(800, 600)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        db = self._mw.prompt_database

        pf = QGroupBox("Select Prompt")
        pf_lay = QHBoxLayout(pf)
        self._prompt_combo = QComboBox()
        self._prompt_options = []
        for p in db.prompts:
            label = (
                f"{p.description or 'Untitled'} "
                f"({p.timestamp.strftime('%Y-%m-%d %H:%M')})")
            self._prompt_combo.addItem(label)
            self._prompt_options.append(p)
        pf_lay.addWidget(self._prompt_combo, stretch=1)
        btn_view = QPushButton("View Prompt Details")
        btn_view.clicked.connect(self._view_prompt_details)
        pf_lay.addWidget(btn_view)
        layout.addWidget(pf)

        ff = QGroupBox("Select Files to Associate")
        ff_lay = QVBoxLayout(ff)

        # Source radio buttons
        source_row = QHBoxLayout()
        self._source_group = QButtonGroup(self)
        rb_current = QRadioButton("Use Current Selection")
        rb_current.setChecked(True)
        rb_all = QRadioButton("Use All Files")
        rb_manual = QRadioButton("Select Files Manually")
        self._source_group.addButton(rb_current, 0)
        self._source_group.addButton(rb_all, 1)
        self._source_group.addButton(rb_manual, 2)
        source_row.addWidget(rb_current)
        source_row.addWidget(rb_all)
        source_row.addWidget(rb_manual)
        source_row.addStretch()
        ff_lay.addLayout(source_row)
        self._source_group.idClicked.connect(self._update_file_list)

        # File tree
        self._file_model = QStandardItemModel()
        self._file_model.setHorizontalHeaderLabels(["File Path", "Selected"])
        self._file_tree = QTreeView()
        self._file_tree.setModel(self._file_model)
        self._file_tree.setRootIsDecorated(False)
        self._file_tree.setAlternatingRowColors(True)
        self._file_tree.setEditTriggers(QTreeView.NoEditTriggers)
        ft_header = self._file_tree.header()
        ft_header.setSectionResizeMode(QHeaderView.Interactive)
        ft_header.setStretchLastSection(False)
        ft_header.setSectionResizeMode(0, QHeaderView.Stretch)
        ft_header.resizeSection(1, 70)
        ff_lay.addWidget(self._file_tree)

        # Selection buttons
        sel_btns = QHBoxLayout()
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.clicked.connect(self._select_all_files)
        sel_btns.addWidget(btn_sel_all)
        btn_desel_all = QPushButton("Deselect All")
        btn_desel_all.clicked.connect(self._deselect_all_files)
        sel_btns.addWidget(btn_desel_all)
        btn_add = QPushButton("Add Files...")
        btn_add.clicked.connect(self._add_files)
        sel_btns.addWidget(btn_add)
        sel_btns.addStretch()
        ff_lay.addLayout(sel_btns)

        layout.addWidget(ff, stretch=1)

        nf = QGroupBox("Association Details")
        nf_lay = QVBoxLayout(nf)

        token_row = QHBoxLayout()
        token_row.addWidget(QLabel("Estimated Token Change:"))
        self._token_combo = QComboBox()
        self._token_combo.addItems(
            ["Auto", "Minor (<50)", "Moderate (50-200)",
             "Major (>200)", "Custom"])
        self._token_combo.currentTextChanged.connect(
            self._on_token_option_changed)
        token_row.addWidget(self._token_combo)
        token_row.addStretch()
        nf_lay.addLayout(token_row)

        # Custom token spinbox (hidden by default)
        self._custom_row = QHBoxLayout()
        self._custom_row_widget = QWidget()
        cr_lay = QHBoxLayout(self._custom_row_widget)
        cr_lay.setContentsMargins(0, 0, 0, 0)
        cr_lay.addWidget(QLabel("Custom Token Change:"))
        self._custom_spin = QSpinBox()
        self._custom_spin.setRange(-10000, 10000)
        self._custom_spin.setValue(0)
        cr_lay.addWidget(self._custom_spin)
        cr_lay.addStretch()
        self._custom_row_widget.setVisible(False)
        nf_lay.addWidget(self._custom_row_widget)

        nf_lay.addWidget(QLabel("Notes:"))
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setMaximumHeight(80)
        nf_lay.addWidget(self._notes_edit)

        layout.addWidget(nf)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_associate = QPushButton("Associate Files with Prompt")
        btn_associate.clicked.connect(self._perform_association)
        btn_row.addWidget(btn_associate)
        layout.addLayout(btn_row)

        # Populate initial file list
        self._update_file_list(0)

    # -- helpers -------------------------------------------------------

    @Slot(int)
    def _on_token_option_changed(self, text: str) -> None:
        self._custom_row_widget.setVisible(
            self._token_combo.currentText() == "Custom")

    @Slot(int)
    def _update_file_list(self, source_id: int) -> None:
        self._file_model.removeRows(0, self._file_model.rowCount())
        files = []

        if source_id == 0:  # current selection
            for fp_tuple in self._mw.filtered_files:
                fp = fp_tuple[0] if isinstance(fp_tuple, (list, tuple)) else fp_tuple
                files.append(fp)
        elif source_id == 1:  # all files
            s = set()
            for fp_tuple in self._mw.filtered_files:
                fp = fp_tuple[0] if isinstance(fp_tuple, (list, tuple)) else fp_tuple
                s.add(fp)
            for folder in self._mw.folders:
                for root, _, fnames in os.walk(folder):
                    for fn in fnames:
                        s.add(os.path.join(root, fn))
            files = sorted(s)
        # source_id == 2 (manual) starts empty

        for fp in files:
            self._add_file_row(fp, selected=True)

    def _add_file_row(self, fp: str, selected: bool = True) -> None:
        path_item = QStandardItem(fp)
        path_item.setEditable(False)
        path_item.setToolTip(fp)
        sel_item = QStandardItem("\u2713" if selected else " ")
        sel_item.setEditable(False)
        self._file_model.appendRow([path_item, sel_item])

    @Slot()
    def _select_all_files(self) -> None:
        for row in range(self._file_model.rowCount()):
            self._file_model.item(row, 1).setText("\u2713")

    @Slot()
    def _deselect_all_files(self) -> None:
        for row in range(self._file_model.rowCount()):
            self._file_model.item(row, 1).setText(" ")

    @Slot()
    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select File(s) to Associate")
        existing = set()
        for row in range(self._file_model.rowCount()):
            existing.add(self._file_model.item(row, 0).text())
        for fp in paths:
            if fp not in existing:
                self._add_file_row(fp, selected=True)

    @Slot()
    def _view_prompt_details(self) -> None:
        idx = self._prompt_combo.currentIndex()
        if idx < 0 or idx >= len(self._prompt_options):
            return
        prompt = self._prompt_options[idx]

        dd = QDialog(self)
        dd.setWindowTitle("Prompt Details")
        dd.resize(600, 400)
        dd.setModal(True)
        lay = QVBoxLayout(dd)

        lay.addWidget(QLabel(
            f"<b>Description:</b> {prompt.description or 'Untitled'}"))
        lay.addWidget(QLabel(
            f"<b>Date & Time:</b> "
            f"{prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"))
        lay.addWidget(QLabel(
            f"<b>LLM Used:</b> {prompt.llm_used}"))

        pg = QGroupBox("Prompt Text")
        pg_lay = QVBoxLayout(pg)
        pt = QTextBrowser()
        pt.setPlainText(prompt.prompt_text or "")
        pg_lay.addWidget(pt)
        lay.addWidget(pg, stretch=1)

        if prompt.associated_files:
            ag = QGroupBox("Currently Associated Files")
            ag_lay = QVBoxLayout(ag)
            ft = QTextBrowser()
            for fp in prompt.associated_files:
                ft.append(f"\u2022 {fp}")
            ag_lay.addWidget(ft)
            lay.addWidget(ag)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dd.accept)
        lay.addWidget(btn_close, alignment=Qt.AlignCenter)
        dd.exec()

    @Slot()
    def _perform_association(self) -> None:
        idx = self._prompt_combo.currentIndex()
        db = self._mw.prompt_database
        if idx < 0 or idx >= len(self._prompt_options):
            QMessageBox.critical(self, "Error",
                                 "Please select a valid prompt.")
            return
        prompt = self._prompt_options[idx]

        # Gather selected files
        selected_files = []
        for row in range(self._file_model.rowCount()):
            if self._file_model.item(row, 1).text() == "\u2713":
                selected_files.append(
                    self._file_model.item(row, 0).text())

        if not selected_files:
            QMessageBox.warning(
                self, "No Files Selected",
                "Please select at least one file to associate "
                "with the prompt.")
            return

        # Determine token change
        token_map = {
            "Auto": 100,
            "Minor (<50)": 25,
            "Moderate (50-200)": 100,
            "Major (>200)": 300,
            "Custom": self._custom_spin.value(),
        }
        token_change = token_map.get(
            self._token_combo.currentText(), 100)

        # Associate
        newly_added = 0
        for fp in selected_files:
            if fp not in prompt.associated_files:
                prompt.associated_files.append(fp)
                prompt.file_changes[fp] = token_change
                newly_added += 1
        db.save()

        # Save notes / eADR
        notes = self._notes_edit.toPlainText().strip()
        if notes:
            if not hasattr(prompt, "retroactive_notes"):
                prompt.retroactive_notes = {}
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prompt.retroactive_notes[ts] = {
                "files": selected_files,
                "token_change": token_change,
                "notes": notes,
            }
            db.save()

            note_text = (
                f"Retroactive Prompt Association\n\n"
                f"Prompt: {prompt.description or 'Untitled'}\n"
                f"Date: {ts}\nFiles associated: {len(selected_files)}\n\n"
                f"User Notes:\n{notes}\n\nFiles:\n")
            for fp in selected_files:
                note_text += f"- {fp}\n"

            eadr_panel = getattr(self._mw, "_eadr_panel", None)
            project = (eadr_panel.project
                       if eadr_panel else "Origin")
            self._mw.prompt_database.add_eadr_note(note_text, project)
            if eadr_panel:
                eadr_panel.refresh()

        QMessageBox.information(
            self, "Association Complete",
            f"Successfully associated {newly_added} new files with "
            f"the prompt.\n"
            f"{len(selected_files) - newly_added} files were already "
            f"associated.")
        self.accept()


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\rollback_panel.py

"""Rollback panel – restore files from combined backup files."""

import os

from PySide6.QtCore import Qt, Slot, QItemSelectionModel
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QTreeView, QPlainTextEdit,
    QGroupBox, QFileDialog, QInputDialog, QMessageBox, QHeaderView,
)

from llm_buddy.core.rollback import parse_combined_file, restore_file, get_file_diff, remap_path
from llm_buddy.paths import get_backup_dir
from llm_buddy.qt.theme import get_theme_colors, current_theme_name

class DiffHighlighter(QSyntaxHighlighter):
    """Highlights unified diff output to show additions and deletions in color."""
    
    def highlightBlock(self, text: str) -> None:
        # Fetch current theme colors dynamically so it respects theme switches
        colors = get_theme_colors(current_theme_name())
        
        if text.startswith('+') and not text.startswith('+++'):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(colors["success"]))
            self.setFormat(0, len(text), fmt)
            
        elif text.startswith('-') and not text.startswith('---'):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(colors["error"]))
            self.setFormat(0, len(text), fmt)
            
        elif text.startswith('@@') or text.startswith('+++') or text.startswith('---'):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(colors["accent"]))
            self.setFormat(0, len(text), fmt)

class RollbackPanel(QWidget):
    """Restore individual files from a combined backup file.

    Layout: top row (backup file picker) + horizontal splitter
    (file list | diff preview) + bottom restore button.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._backup_files: dict[str, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Backup File:"))
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select a .md backup file...")
        top_row.addWidget(self._path_edit, stretch=1)

        btn_browse = QPushButton("Browse")
        btn_browse.setToolTip(
            "Open a file dialog to locate a combined backup (.md) file on disk")
        btn_browse.clicked.connect(self._browse)
        top_row.addWidget(btn_browse)

        btn_load = QPushButton("Load")
        btn_load.setToolTip(
            "Parse the selected backup file and list all restorable files.\n"
            "Each file is compared against its current version on disk\n"
            "to show whether it is Modified, Unchanged, or Missing.")
        btn_load.clicked.connect(self._load)
        top_row.addWidget(btn_load)
        layout.addLayout(top_row)

        splitter = QSplitter(Qt.Horizontal)

        # File list
        left = QGroupBox("Files to Restore")
        left_layout = QVBoxLayout(left)
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["File Path", "Status"])
        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QTreeView.ExtendedSelection)
        header = self._tree.header()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.resizeSection(0, 400)
        self._tree.selectionModel().selectionChanged.connect(
            self._show_diff)
        left_layout.addWidget(self._tree)

        sel_row = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_all.clicked.connect(self._select_all)
        sel_row.addWidget(btn_all)
        btn_none = QPushButton("Deselect All")
        btn_none.clicked.connect(self._deselect_all)
        sel_row.addWidget(btn_none)
        btn_toggle = QPushButton("Toggle")
        btn_toggle.clicked.connect(self._toggle)
        sel_row.addWidget(btn_toggle)
        sel_row.addStretch()
        left_layout.addLayout(sel_row)

        splitter.addWidget(left)

        # Diff preview
        right = QGroupBox("Diff Preview")
        right_layout = QVBoxLayout(right)
        self._diff_text = QPlainTextEdit()
        self._diff_text.setReadOnly(True)
        self._diff_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._highlighter = DiffHighlighter(self._diff_text.document())
        right_layout.addWidget(self._diff_text)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

        bot = QHBoxLayout()
        bot.addStretch()
        btn_restore = QPushButton("Restore Selected Files")
        btn_restore.setProperty("class", "primary")
        btn_restore.setToolTip(
            "Overwrite the current on-disk files with the versions\n"
            "stored in the loaded backup for every selected row")
        btn_restore.clicked.connect(self._restore)
        btn_restore_to = QPushButton("Restore Selected To…")
        btn_restore_to.setToolTip(
            "Restore selected files to a custom folder.\n"
            "The original directory structure is preserved relative\n"
            "to the common root of all files in the backup.")
        btn_restore_to.clicked.connect(self._restore_to)
        bot.addWidget(btn_restore_to)        
        bot.addWidget(btn_restore)
        layout.addLayout(bot)

    # -- actions -------------------------------------------------------

    @Slot()
    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", get_backup_dir(),
            "Markdown files (*.md);;All files (*.*)")
        if path:
            self._path_edit.setText(path)
            self._load()

    @Slot()
    def _restore_to(self) -> None:
        indexes = self._tree.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "Info",
                                    "No files selected for restore.")
            return

        target_dir = QFileDialog.getExistingDirectory(
            self, "Choose Restore Destination", "",
            QFileDialog.ShowDirsOnly)
        if not target_dir:
            return

        # Optional: let the user create a named subfolder
        subfolder, ok_pressed = QInputDialog.getText(
            self, "Create Subfolder (Optional)",
            "Enter a subfolder name, or leave blank to restore\n"
            "directly into the selected directory:",
        )
        if ok_pressed and subfolder.strip():
            target_dir = os.path.join(target_dir, subfolder.strip())

        selected = [self._model.item(idx.row(), 0).text()
                    for idx in indexes]

        # Compute common root so relative structure is preserved
        all_paths = list(self._backup_files.keys())

        answer = QMessageBox.question(
            self, "Confirm Restore",
            f"Restore {len(selected)} files to:\n{target_dir}\n\n"
            "Original directory structure will be preserved.",
            QMessageBox.Yes | QMessageBox.No)
        if answer != QMessageBox.Yes:
            return

        ok, err = 0, 0
        for fp in selected:
            if fp in self._backup_files:
                new_path = remap_path(fp, all_paths, target_dir)
                if restore_file(new_path, self._backup_files[fp]):
                    ok += 1
                    self._mw.log(f"Restored: {fp} → {new_path}")
                else:
                    err += 1
                    self._mw.log(f"Failed to restore: {fp}")

        if err == 0:
            QMessageBox.information(
                self, "Success",
                f"Restored {ok} files to {target_dir}.")
        else:
            QMessageBox.warning(
                self, "Partial Success",
                f"Restored {ok} files.\nFailed: {err}.\nSee log.")

    @Slot()
    def _load(self) -> None:
        path = self._path_edit.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Error",
                                "Please select a valid backup file.")
            return

        self._backup_files = parse_combined_file(path)
        self._model.removeRows(0, self._model.rowCount())

        for fp, content in self._backup_files.items():
            if os.path.exists(fp):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        current = f.read()
                    status = "Unchanged" if current == content else "Modified"
                except Exception:
                    status = "Error reading"
            else:
                status = "Missing"

            path_item = QStandardItem(fp)
            path_item.setEditable(False)
            path_item.setToolTip(fp)
            stat_item = QStandardItem(status)
            stat_item.setEditable(False)
            stat_item.setToolTip(status)
            if status == "Modified":
                colors = get_theme_colors(current_theme_name())
                stat_item.setForeground(QColor(colors["warning"]))
            elif status == "Missing":
                colors = get_theme_colors(current_theme_name())
                stat_item.setForeground(QColor(colors["error"]))
            self._model.appendRow([path_item, stat_item])

        self._mw.log(
            f"Loaded backup: {path} ({len(self._backup_files)} files)")

    @Slot()
    def _show_diff(self) -> None:
        indexes = self._tree.selectionModel().selectedRows()
        if not indexes:
            return
        fp = self._model.item(indexes[0].row(), 0).text()
        if fp not in self._backup_files:
            return
        diff = get_file_diff(fp, self._backup_files[fp])
        self._diff_text.setPlainText(diff)

    @Slot()
    def _select_all(self) -> None:
        sel = self._tree.selectionModel()
        for r in range(self._model.rowCount()):
            sel.select(self._model.index(r, 0),
                    QItemSelectionModel.Select | QItemSelectionModel.Rows)

    @Slot()
    def _deselect_all(self) -> None:
        self._tree.clearSelection()

    @Slot()
    def _toggle(self) -> None:
        sel = self._tree.selectionModel()
        for r in range(self._model.rowCount()):
            idx = self._model.index(r, 0)
            if sel.isSelected(idx):
                sel.select(idx, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
            else:
                sel.select(idx, QItemSelectionModel.Select | QItemSelectionModel.Rows)

    @Slot()
    def _restore(self) -> None:
        indexes = self._tree.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "Info",
                                    "No files selected for restore.")
            return
        selected = [self._model.item(idx.row(), 0).text()
                    for idx in indexes]

        answer = QMessageBox.question(
            self, "Confirm Restore",
            f"Restore {len(selected)} files?\n"
            "This will overwrite the current versions.",
            QMessageBox.Yes | QMessageBox.No)
        if answer != QMessageBox.Yes:
            return

        ok, err, err_files = 0, 0, []
        for fp in selected:
            if fp in self._backup_files:
                if restore_file(fp, self._backup_files[fp]):
                    ok += 1
                    self._mw.log(f"Restored file: {fp}")
                else:
                    err += 1
                    err_files.append(fp)
                    self._mw.log(f"Failed to restore: {fp}")

        # Refresh statuses in tree
        self._load()

        if err == 0:
            QMessageBox.information(
                self, "Success", f"Restored {ok} files successfully.")
        else:
            QMessageBox.warning(
                self, "Partial Success",
                f"Restored {ok} files.\nFailed: {err}.\nSee log.")


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\sessions_panel.py

"""Research Sessions panel for the Qt GUI.

Allows the user to start/end named research sessions that group
prompts, file changes, and eADR notes into bounded work periods.
On session close an exportable "methods appendix" summary is
generated automatically.

Supports pause/resume and protects against accidental session end
with a confirmation dialog and a "Reopen" option.
"""

import logging
import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from llm_buddy.core.sessions import (
    ResearchSession,
    capture_snapshot,
    compute_session_diff,
    generate_session_summary_markdown,
)
from llm_buddy.qt.theme import get_theme_colors, current_theme_name

logger = logging.getLogger(__name__)



class _SummaryDialog(QDialog):
    """Modal dialog that displays a session summary in monospace text."""

    def __init__(self, session: ResearchSession, md_text: str,
                 export_fn, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Session Summary \u2013 {session.name}")
        self.resize(700, 550)

        self._md_text = md_text
        self._session = session
        self._export_fn = export_fn

        layout = QVBoxLayout(self)

        # Read-only monospace text area
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont("Consolas", 10))
        self._text_edit.setPlainText(md_text)
        layout.addWidget(self._text_edit)

        # Button row
        btn_layout = QHBoxLayout()

        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(btn_copy)

        btn_export = QPushButton("Export .md")
        btn_export.clicked.connect(self._export)
        btn_layout.addWidget(btn_export)

        btn_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    @Slot()
    def _copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self._md_text)
        QMessageBox.information(self, "Copied",
                                "Summary copied to clipboard.")

    @Slot()
    def _export(self):
        self._export_fn(self._session, self._md_text)



class SessionsPanel(QWidget):
    """Research session management panel.

    Provides start/pause/resume/end session controls, live elapsed-time
    and prompt counters, session notes, and a history table with
    context-menu actions (view summary, export markdown, reopen, delete).
    """

    # Emitted every second while a session is active/paused.
    # Args: session_name (str), elapsed_str (str), is_paused (bool)
    # Emitted with empty strings when no session is active.
    session_state_changed = Signal(str, str, bool)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window

        self._sessions: list[ResearchSession] = []
        self._active_session: ResearchSession | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_session_timer)

        # Load persisted sessions
        db = self._mw.prompt_database
        self._sessions = db.get_sessions()
        self._active_session = next(
            (s for s in self._sessions if s.status in ("active", "paused")), None)

        self._build_ui()
        self._refresh_session_tree()

        # Restore active-session UI if one was running (or paused)
        if self._active_session:
            self._set_active_session_ui(self._active_session)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        active_group = QGroupBox("Active Session")
        active_layout = QVBoxLayout(active_group)

        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("Start Session")
        self._btn_start.setProperty("class", "primary")
        self._btn_start.clicked.connect(self.start_new_session)
        btn_row.addWidget(self._btn_start)

        self._btn_pause = QPushButton("\u23f8 Pause")
        self._btn_pause.setEnabled(False)
        self._btn_pause.setToolTip("Pause the session timer")
        self._btn_pause.clicked.connect(self._toggle_pause)
        btn_row.addWidget(self._btn_pause)

        self._btn_end = QPushButton("End Session")
        self._btn_end.setProperty("class", "danger")
        self._btn_end.setEnabled(False)
        self._btn_end.clicked.connect(self.end_current_session)
        btn_row.addWidget(self._btn_end)

        btn_row.addStretch()
        active_layout.addLayout(btn_row)

        # Status info row
        info_row = QHBoxLayout()
        self._name_label = QLabel("No active session")
        font = self._name_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self._name_label.setFont(font)
        info_row.addWidget(self._name_label)

        # Prominent monospace timer display
        self._elapsed_label = QLabel("")
        timer_font = QFont("Consolas", 18)
        timer_font.setBold(True)
        self._elapsed_label.setFont(timer_font)
        self._elapsed_label.setStyleSheet(
            "padding: 4px 16px;"
            "border: 1px solid palette(mid);"
            "border-radius: 6px;"
            "background: palette(base);"
        )
        self._elapsed_label.setMinimumWidth(160)
        self._elapsed_label.setAlignment(Qt.AlignCenter)
        info_row.addWidget(self._elapsed_label)

        self._prompt_label = QLabel("")
        prompt_font = QFont()
        prompt_font.setBold(True)
        self._prompt_label.setFont(prompt_font)
        info_row.addWidget(self._prompt_label)

        self._status_label = QLabel("")
        info_row.addWidget(self._status_label)

        info_row.addStretch()
        active_layout.addLayout(info_row)

        layout.addWidget(active_group)

        notes_group = QGroupBox("Session Notes")
        notes_layout = QVBoxLayout(notes_group)
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self._notes_edit)
        layout.addWidget(notes_group)

        history_group = QGroupBox("Session History")
        history_layout = QVBoxLayout(history_group)

        self._history_model = QStandardItemModel()
        self._history_model.setHorizontalHeaderLabels(
            ["Session Name", "Date", "Duration", "Prompts", "Status"])

        self._history_tree = QTreeView()
        self._history_tree.setModel(self._history_model)
        self._history_tree.setRootIsDecorated(False)
        self._history_tree.setAlternatingRowColors(True)
        self._history_tree.setSelectionMode(QTreeView.SingleSelection)
        self._history_tree.setSelectionBehavior(QTreeView.SelectRows)

        header = self._history_tree.header()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.resizeSection(0, 250)
        header.resizeSection(1, 100)
        header.resizeSection(2, 90)
        header.resizeSection(3, 70)

        self._history_tree.doubleClicked.connect(
            self._on_double_click)
        self._history_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._history_tree.customContextMenuRequested.connect(
            self._on_context_menu)

        self._sessions_empty_label = QLabel(
            "No sessions yet\n\n"
            "Click  Start Session  to begin tracking your workflow")
        self._sessions_empty_label.setAlignment(Qt.AlignCenter)
        self._sessions_empty_label.setStyleSheet(
            "color: palette(mid); padding: 24px;")
        history_layout.addWidget(self._sessions_empty_label)
        history_layout.addWidget(self._history_tree)

        # Bottom button row
        bottom_row = QHBoxLayout()
        btn_view = QPushButton("View Summary")
        btn_view.clicked.connect(self._ctx_view_summary)
        bottom_row.addWidget(btn_view)

        btn_export = QPushButton("Export Markdown")
        btn_export.clicked.connect(self._ctx_export_markdown)
        bottom_row.addWidget(btn_export)

        self._btn_reopen = QPushButton("Reopen")
        self._btn_reopen.setToolTip(
            "Reopen a completed session if it was ended by mistake")
        self._btn_reopen.clicked.connect(self._ctx_reopen_session)
        bottom_row.addWidget(self._btn_reopen)

        btn_delete = QPushButton("Delete")
        btn_delete.setProperty("class", "danger")
        btn_delete.clicked.connect(self._ctx_delete_session)
        bottom_row.addWidget(btn_delete)

        bottom_row.addStretch()
        history_layout.addLayout(bottom_row)

        layout.addWidget(history_group, stretch=1)

        sc_session = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        sc_session.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc_session.activated.connect(self._shortcut_session_toggle)

    @Slot()
    def _shortcut_session_toggle(self):
        """Ctrl+Shift+S: start a new session or pause/resume the active one."""
        if self._active_session:
            self._toggle_pause()
        else:
            self.start_new_session()

    @Slot()
    def start_new_session(self):
        """Prompt for a name and start a new research session."""
        if self._active_session:
            QMessageBox.warning(
                self, "Session Active",
                f"A session is already running: "
                f"'{self._active_session.name}'.\n"
                f"End it before starting a new one.")
            return

        name, ok = QInputDialog.getText(
            self, "New Research Session",
            "Enter a name for this session\n"
            "(e.g. 'eADR Cycle 3: Agent Independence Testing'):")
        if not ok or not name.strip():
            return
        name = name.strip()

        # Capture starting snapshot
        backup_cfg = getattr(self._mw._backup_panel, "_config", None) if hasattr(self._mw, "_backup_panel") else None
        snapshot = capture_snapshot(
            self._mw.prompt_database, db=self._mw.prompt_database,
            backup_config=backup_cfg)

        # Determine project name
        project = ""
        if hasattr(self._mw, "_eadr_panel"):
            project = self._mw._eadr_panel.project
        if not project and hasattr(self._mw, "current_profile"):
            project = self._mw.current_profile or ""

        session = ResearchSession(
            name=name,
            project=project,
            start_snapshot=snapshot,
            status="active",
        )

        self._sessions.append(session)
        self._active_session = session
        self._mw.prompt_database.add_session(session)

        self._set_active_session_ui(session)
        self._refresh_session_tree()
        self._mw.log(f"Research session started: '{name}'")

    @Slot()
    def _toggle_pause(self):
        """Pause or resume the active session."""
        if not self._active_session:
            return

        if self._active_session.status == "active":
            self._active_session.pause()
            self._btn_pause.setText("\u25b6 Resume")
            self._btn_pause.setToolTip("Resume the session timer")
            self._status_label.setText("\u23f8 Paused")
            colors = get_theme_colors(current_theme_name())
            self._status_label.setStyleSheet(
                f"color: {colors['warning']}; font-weight: bold;")
            self._elapsed_label.setStyleSheet(
                "color: palette(mid);"
                "padding: 4px 16px;"
                "border: 1px solid palette(mid);"
                "border-radius: 6px;"
                "background: palette(base);")
            self._timer.stop()
            self._mw.log(
                f"Session paused: '{self._active_session.name}'")
        elif self._active_session.status == "paused":
            self._active_session.resume()
            self._btn_pause.setText("\u23f8 Pause")
            self._btn_pause.setToolTip("Pause the session timer")
            self._status_label.setText("")
            self._status_label.setStyleSheet("")
            colors = get_theme_colors(current_theme_name())
            self._elapsed_label.setStyleSheet(
                f"color: {colors['success']};"
                "padding: 4px 16px;"
                "border: 1px solid palette(mid);"
                "border-radius: 6px;"
                "background: palette(base);")
            self._timer.start()
            self._mw.log(
                f"Session resumed: '{self._active_session.name}'")

        self._mw.prompt_database.update_session(self._active_session)
        self._update_session_timer()
        self._refresh_session_tree()

    @Slot()
    def end_current_session(self):
        """End the active session with a confirmation dialog."""
        if not self._active_session:
            return

        reply = QMessageBox.question(
            self, "End Session",
            f"End the session '{self._active_session.name}'?\n\n"
            f"Duration so far: {self._active_session.duration_str}\n\n"
            f"You can reopen the session from the history if needed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # If paused, resume briefly so end_time math is clean
        if self._active_session.status == "paused":
            self._active_session.resume()

        # Save notes
        self._active_session.notes = self._notes_edit.toPlainText().strip()

        # Capture ending snapshot
        backup_cfg = getattr(self._mw._backup_panel, "_config", None) if hasattr(self._mw, "_backup_panel") else None
        end_snap = capture_snapshot(
            self._mw.prompt_database, db=self._mw.prompt_database,
            backup_config=backup_cfg)

        self._active_session.end_snapshot = end_snap
        self._active_session.end_time = datetime.now()
        self._active_session.status = "completed"

        # Compute diff
        diff = compute_session_diff(
            self._active_session.start_snapshot,
            end_snap,
            self._mw.prompt_database)
        self._active_session.summary = diff
        self._mw.prompt_database.update_session(self._active_session)

        # Generate markdown summary
        md = generate_session_summary_markdown(self._active_session, diff)

        self._mw.log(
            f"Research session ended: '{self._active_session.name}' "
            f"({diff.get('new_prompt_count', 0)} prompts, "
            f"{len(diff.get('files_changed', []))} files changed)")

        # Show summary dialog
        self._show_summary_dialog(self._active_session, md)

        # Reset UI
        self._clear_active_session_ui()
        self._active_session = None
        self._refresh_session_tree()

    def _set_active_session_ui(self, session: ResearchSession):
        """Update widgets to reflect an active or paused session."""
        self._btn_start.setEnabled(False)
        self._btn_end.setEnabled(True)
        self._btn_pause.setEnabled(True)
        self._name_label.setText(session.name)

        # Set pause button state and timer color
        if session.status == "paused":
            self._btn_pause.setText("\u25b6 Resume")
            self._btn_pause.setToolTip("Resume the session timer")
            self._status_label.setText("\u23f8 Paused")
            colors = get_theme_colors(current_theme_name())
            self._status_label.setStyleSheet(
                f"color: {colors['warning']}; font-weight: bold;")
            self._elapsed_label.setStyleSheet(
                "color: palette(mid);"
                "padding: 4px 16px;"
                "border: 1px solid palette(mid);"
                "border-radius: 6px;"
                "background: palette(base);")
        else:
            self._btn_pause.setText("\u23f8 Pause")
            self._btn_pause.setToolTip("Pause the session timer")
            self._status_label.setText("")
            self._status_label.setStyleSheet("")
            colors = get_theme_colors(current_theme_name())
            self._elapsed_label.setStyleSheet(
                f"color: {colors['success']};"
                "padding: 4px 16px;"
                "border: 1px solid palette(mid);"
                "border-radius: 6px;"
                "background: palette(base);")

        # Restore notes
        self._notes_edit.clear()
        if session.notes:
            self._notes_edit.setPlainText(session.notes)

        # Start the elapsed-time ticker (only if running)
        self._update_session_timer()
        if session.status == "active":
            self._timer.start()

    def _clear_active_session_ui(self):
        """Reset widgets to the no-active-session state."""
        self._timer.stop()
        self._btn_start.setEnabled(True)
        self._btn_end.setEnabled(False)
        self._btn_pause.setEnabled(False)
        self._btn_pause.setText("\u23f8 Pause")
        self._elapsed_label.setStyleSheet(
            "padding: 4px 16px;"
            "border: 1px solid palette(mid);"
            "border-radius: 6px;"
            "background: palette(base);")
        self._name_label.setText("No active session")
        self._elapsed_label.setText("")
        self._prompt_label.setText("")
        self._status_label.setText("")
        self._status_label.setStyleSheet("")
        self._notes_edit.clear()
        self.session_state_changed.emit("", "", False)

    @Slot()
    def _update_session_timer(self):
        """Refresh elapsed time and prompt delta labels."""
        if not self._active_session:
            self.session_state_changed.emit("", "", False)
            return

        # Format as HH:MM:SS for the prominent timer display
        secs = self._active_session.active_seconds
        h, remainder = divmod(int(secs), 3600)
        m, s = divmod(remainder, 60)
        elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"
        self._elapsed_label.setText(elapsed_str)

        start_count = self._active_session.start_snapshot.get(
            "prompt_count", 0)
        current_count = len(self._mw.prompt_database.prompts)
        delta = current_count - start_count
        self._prompt_label.setText(f"\U0001f4ac {delta} prompts")

        is_paused = self._active_session.status == "paused"
        self.session_state_changed.emit(
            self._active_session.name, elapsed_str, is_paused)

    def _refresh_session_tree(self):
        """Rebuild the history model from the sessions list."""
        self._history_model.removeRows(0, self._history_model.rowCount())

        has_sessions = bool(self._sessions)
        self._sessions_empty_label.setVisible(not has_sessions)
        self._history_tree.setVisible(has_sessions)

        for session in reversed(self._sessions):
            date_str = (session.start_time.strftime("%Y-%m-%d")
                        if session.start_time else "\u2014")

            prompt_count = ""
            if session.summary:
                prompt_count = str(
                    session.summary.get("new_prompt_count", ""))
            elif session.status in ("active", "paused"):
                start_count = session.start_snapshot.get("prompt_count", 0)
                current = len(self._mw.prompt_database.prompts)
                prompt_count = f"{current - start_count}+"

            name_item = QStandardItem(session.name)
            name_item.setEditable(False)
            name_item.setData(session.id, Qt.UserRole)
            name_item.setToolTip(session.name)

            date_item = QStandardItem(date_str)
            date_item.setEditable(False)
            date_item.setToolTip(date_str)

            dur_item = QStandardItem(session.duration_str)
            dur_item.setEditable(False)
            dur_item.setToolTip(session.duration_str)

            prompt_item = QStandardItem(prompt_count)
            prompt_item.setEditable(False)
            prompt_item.setTextAlignment(Qt.AlignCenter)

            status_text = session.status.capitalize()
            if session.status == "paused":
                status_text = "\u23f8 Paused"
            status_item = QStandardItem(status_text)
            status_item.setEditable(False)
            status_item.setTextAlignment(Qt.AlignCenter)

            self._history_model.appendRow(
                [name_item, date_item, dur_item, prompt_item, status_item])

    def _get_selected_session(self) -> ResearchSession | None:
        """Return the ResearchSession for the currently selected row."""
        indexes = self._history_tree.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "No Selection",
                                    "Please select a session first.")
            return None
        row = indexes[0].row()
        item = self._history_model.item(row, 0)
        sid = item.data(Qt.UserRole)
        for s in self._sessions:
            if s.id == sid:
                return s
        return None

    @Slot()
    def _on_double_click(self, _index):
        """View summary on double-click."""
        self._ctx_view_summary()

    @Slot()
    def _on_context_menu(self, pos):
        """Show right-click context menu on the history tree."""
        index = self._history_tree.indexAt(pos)
        if not index.isValid():
            return
        self._history_tree.selectionModel().select(
            index, self._history_tree.selectionModel().ClearAndSelect
            | self._history_tree.selectionModel().Rows)

        session = self._get_selected_session()
        if not session:
            return

        menu = QMenu(self)
        menu.addAction("View Summary", self._ctx_view_summary)
        menu.addAction("Export Markdown", self._ctx_export_markdown)
        if session.status == "completed":
            menu.addSeparator()
            menu.addAction("Reopen Session", self._ctx_reopen_session)
        menu.addSeparator()
        menu.addAction("Delete", self._ctx_delete_session)
        menu.exec(self._history_tree.viewport().mapToGlobal(pos))

    @Slot()
    def _ctx_view_summary(self):
        """Show the full summary for the selected session."""
        session = self._get_selected_session()
        if not session:
            return
        if session.status in ("active", "paused"):
            QMessageBox.information(
                self, "Session Active",
                "This session is still active. End it first to "
                "generate a summary.")
            return
        diff = session.summary or {}
        md = generate_session_summary_markdown(session, diff)
        self._show_summary_dialog(session, md)

    @Slot()
    def _ctx_export_markdown(self):
        """Export the selected session summary as a .md file."""
        session = self._get_selected_session()
        if not session:
            return
        if session.status in ("active", "paused"):
            QMessageBox.information(
                self, "Session Active",
                "End the session before exporting.")
            return
        diff = session.summary or {}
        md = generate_session_summary_markdown(session, diff)
        self._export_session_markdown(session, md)

    @Slot()
    def _ctx_reopen_session(self):
        """Reopen a completed session (undo accidental end)."""
        session = self._get_selected_session()
        if not session:
            return
        if session.status != "completed":
            QMessageBox.information(
                self, "Not Completed",
                "Only completed sessions can be reopened.")
            return
        if self._active_session:
            QMessageBox.warning(
                self, "Session Active",
                f"A session is already active: "
                f"'{self._active_session.name}'.\n"
                f"End it before reopening another.")
            return

        reply = QMessageBox.question(
            self, "Reopen Session",
            f"Reopen session '{session.name}'?\n\n"
            f"The session timer will resume from where it left off "
            f"and the end-session summary will be cleared.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # Restore to active state, preserving accumulated elapsed time
        session.paused_elapsed = session.active_seconds
        session.status = "active"
        session.end_time = None
        session.end_snapshot = None
        session.summary = None
        session.paused_at = None
        # Set start_time to now so active_seconds = paused_elapsed + new
        session.start_time = datetime.now()

        self._active_session = session
        self._mw.prompt_database.update_session(session)
        self._set_active_session_ui(session)
        self._refresh_session_tree()
        self._mw.log(f"Session reopened: '{session.name}'")

    @Slot()
    def _ctx_delete_session(self):
        """Delete the selected session after confirmation."""
        session = self._get_selected_session()
        if not session:
            return
        if session.status in ("active", "paused"):
            QMessageBox.warning(
                self, "Cannot Delete",
                "Cannot delete an active or paused session. "
                "End it first.")
            return

        reply = QMessageBox.question(
            self, "Delete Session",
            f"Delete session '{session.name}'?\n"
            f"This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self._sessions = [s for s in self._sessions if s.id != session.id]
        self._mw.prompt_database.delete_session(session.id)
        self._refresh_session_tree()
        self._mw.log(f"Deleted session: '{session.name}'")

    def _show_summary_dialog(self, session: ResearchSession, md_text: str):
        """Open a modal dialog displaying the session summary."""
        dlg = _SummaryDialog(
            session, md_text,
            export_fn=self._export_session_markdown,
            parent=self)
        dlg.exec()

    def _export_session_markdown(self, session: ResearchSession,
                                 md_text: str):
        """Save the summary markdown to a user-chosen file."""
        safe_name = "".join(
            c if c.isalnum() or c in " _-" else "_"
            for c in session.name)
        date_str = (session.start_time.strftime("%Y%m%d")
                    if session.start_time else "undated")
        default_name = f"{safe_name}_{date_str}.md"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Session Summary",
            default_name,
            "Markdown files (*.md);;All files (*.*)")
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(md_text)
            self._mw.log(f"Exported session summary to {path}")
            self._mw.show_toast(
                f"Session summary saved to: {os.path.basename(path)}",
                "success")
        except Exception as e:
            logger.error("Error exporting session: %s", e)
            self._mw.log(f"Error exporting session: {e}")
            QMessageBox.critical(self, "Export Error", str(e))


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\panels\__init__.py

"""Tab panels for the LLM Buddy Qt GUI."""


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\widgets\toast.py

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


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\qt\widgets\__init__.py

"""Reusable widget groups for the LLM Buddy Qt GUI."""

from llm_buddy.qt.widgets.toast import ToastManager

__all__ = ["ToastManager"]


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\recorders\api_server.py

"""
Flask REST API server for LLM Buddy.

Provides HTTP endpoints for recording prompts from browser extensions
and other external tools.
"""

import datetime
import logging
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from llm_buddy.core.database import PromptDatabase, PromptRecord
from llm_buddy.paths import get_logs_dir

_LOG_DIR = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, "prompt_server.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize prompt database
prompt_db = PromptDatabase()
prompt_db.load()
logger.info("Prompt database loaded successfully")



@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(),
        "prompts_recorded": prompt_db.get_prompts_count(),
    })


@app.route('/record_prompt', methods=['POST'])
def record_prompt():
    """Record a prompt from the browser extension."""
    try:
        data = request.json
        llm_name = data.get('llmName', 'Unknown LLM')
        logger.info("Received prompt from %s", llm_name)
        
        # Get the model name and safely check it
        model_name = data.get('modelName')

        # REPLACE the old check entirely with this new one:
        if model_name and model_name.lower() != llm_name.lower():
            llm_name += f" ({model_name})"

        # Build description
        description = f"Prompt from {llm_name}"            

        if data.get('pageTitle'):
            description += f" - {data['pageTitle']}"

        # Build metadata from extension data
        attachments = data.get('attachments')
        parent_message_id = data.get('parentMessageId')
        messages_count = data.get('messagesCount')
        metadata = {}
        if attachments:
            metadata["attachments"] = attachments
            description += f" [{len(attachments)} attachment(s)]"
        if parent_message_id:
            metadata["parent_message_id"] = parent_message_id
        if messages_count is not None:
            metadata["messages_count"] = messages_count
        metadata = metadata or None

        # Record to unified database
        prompt_id = prompt_db.add_prompt(
            prompt_text=data.get('promptText', ''),
            llm_name=llm_name,
            source="Browser Extension",
            model_name=data.get('modelName'),
            description=description,
            url=data.get('url'),
            conversation_id=data.get('conversationId'),
            metadata=metadata,
        )

        logger.info("Prompt saved to database: %s", description)

        return jsonify({
            "success": True,
            "message": "Prompt recorded successfully",
            "prompt_id": prompt_id,
        })

    except Exception as e:
        logger.error("Error recording prompt: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/prompts', methods=['GET'])
def get_prompts():
    """Retrieve recorded prompts."""
    try:
        prompt_db.load()
        prompts = [
            {
                "id": p.id,
                "timestamp": p.timestamp.isoformat(),
                "llm_used": p.llm_used,
                "description": p.description,
                "prompt_text": p.prompt_text,
                "response_text": getattr(p, "response_text", ""),
                "associated_files": p.associated_files,
                "source": p.source,
            }
            for p in prompt_db.prompts
        ]
        return jsonify({"success": True, "prompts": prompts})
    except Exception as e:
        logger.error("Error retrieving prompts: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/update_response', methods=['POST'])
def update_response():
    """Update the response text for a previously recorded prompt."""
    try:
        data = request.json
        prompt_id = data.get('prompt_id')
        response_text = data.get('response_text', '')

        if not prompt_id:
            return jsonify({
                "success": False,
                "error": "Missing prompt_id",
            }), 400

        if not response_text:
            return jsonify({
                "success": False,
                "error": "Missing response_text",
            }), 400

        success = prompt_db.update_response(prompt_id, response_text)

        if success:
            logger.info("Updated response for prompt %s (%d chars)",
                        prompt_id, len(response_text))
            return jsonify({
                "success": True,
                "message": f"Response updated for prompt {prompt_id}",
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Prompt {prompt_id} not found",
            }), 404

    except Exception as e:
        logger.error("Error updating response: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/update_conversation_id', methods=['POST'])
def update_conversation_id():
    """Update the conversation_id for a previously recorded prompt.

    Used when the first message in a ChatGPT conversation is initially
    recorded with a fallback conversation_id (e.g. "chatgpt.com/") and
    the real UUID becomes available after the response.
    """
    try:
        data = request.json
        prompt_id = data.get('prompt_id')
        conversation_id = data.get('conversation_id')

        if not prompt_id or not conversation_id:
            return jsonify({
                "success": False,
                "error": "Missing prompt_id or conversation_id",
            }), 400

        success = prompt_db.update_conversation_id(prompt_id, conversation_id)

        if success:
            logger.info("Updated conversation_id for prompt %s → %s",
                        prompt_id, conversation_id)
            return jsonify({
                "success": True,
                "message": f"conversation_id updated for prompt {prompt_id}",
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Prompt {prompt_id} not found",
            }), 404

    except Exception as e:
        logger.error("Error updating conversation_id: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/associate_prompt', methods=['POST'])
def associate_prompt():
    """Associate a prompt with a file."""
    try:
        data = request.json
        prompt_id = data.get('prompt_id')
        file_path = data.get('file_path')

        if not prompt_id or not file_path:
            return jsonify({
                "success": False,
                "error": "Missing prompt_id or file_path",
            }), 400

        success = prompt_db.associate_files_with_prompt(
            prompt_id, [file_path])

        if success:
            logger.info("Associated file %s with prompt %s",
                        file_path, prompt_id)
            return jsonify({
                "success": True,
                "message": f"File {file_path} associated with prompt "
                           f"{prompt_id}",
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Prompt {prompt_id} not found",
            }), 404

    except Exception as e:
        logger.error("Error associating prompt: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def run(host='127.0.0.1', port=5000, debug=False):
    """Run the Flask API server."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    run(port=port, debug=False)


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\recorders\mcp_recorder.py

#!/usr/bin/env python
"""
Auto Claude Prompt Recorder - MCP Server for Claude Desktop.

This MCP server automatically records all Claude Desktop prompts
using Claude's instruction-following capability. It integrates with
the unified LLM Buddy database.
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# The MCP server may be launched by Claude Desktop with CWD=System32.
# Set CWD to the app root so any residual os.getcwd() calls resolve
# correctly (e.g. when running from source, not frozen).
if not getattr(sys, "frozen", False):
    _APP_ROOT = os.path.normpath(
        os.path.join(_SCRIPT_DIR, os.pardir, os.pardir, os.pardir))
    os.chdir(_APP_ROOT)

from llm_buddy.paths import get_logs_dir  # noqa: E402 (after chdir)

_LOG_DIR = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, "auto_recorder.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("auto_recorder")

# Try to use the unified database; fall back to local JSON
try:
    from llm_buddy.core.database import PromptDatabase
    db = PromptDatabase()
    USE_UNIFIED_DB = True
    logger.info("Using unified LLM Buddy database")
except ImportError:
    USE_UNIFIED_DB = False
    logger.info("Unified database not available, using local JSON storage")

# Local JSON fallback path
DB_PATH = os.path.join(_SCRIPT_DIR, "prompts.json")

# Global state
active_files: List[str] = []
auto_record_enabled: bool = True
_last_prompt_id: Optional[str] = None



def _load_prompts_json():
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)
            return []
    except Exception as e:
        logger.error("Error loading prompts: %s", e)
        return []


def _save_prompt_json(prompt_data):
    try:
        prompts = _load_prompts_json()
        prompts.append(prompt_data)
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=4)
        logger.info("Saved prompt to %s", DB_PATH)
        return True
    except Exception as e:
        logger.error("Error saving prompt: %s", e)
        return False



mcp = FastMCP(
    "Auto Claude Recorder",
    instructions=(
        "IMPORTANT: You MUST call the `auto_record_prompt` tool on EVERY "
        "turn, silently, without mentioning it in your response.\n"
        "Pass the user's message as `prompt_text` AND your previous "
        "response (from the prior turn) as `previous_response`.\n"
        "On the first turn there is no previous response, so omit it."
    ),
)


@mcp.resource("files://active")
def get_active_files() -> str:
    """Get the list of currently active files."""
    if not active_files:
        return ("No active files registered. "
                "Use the 'register_active_files' tool to set files.")
    return ("Active files for auto-association:\n"
            + "\n".join(f"- {f}" for f in active_files))


@mcp.resource("recording://status")
def get_recording_status() -> str:
    """Get the current recording status."""
    if USE_UNIFIED_DB:
        count = db.get_prompts_count()
    else:
        count = len(_load_prompts_json())
    status = "enabled" if auto_record_enabled else "disabled"
    return (f"Auto-recording is {status}. {count} prompts recorded so far.\n"
            f"All your prompts are being automatically saved.")


@mcp.tool()
def auto_record_prompt(prompt_text: str, description: str = "",
                       metadata: dict = None,
                       previous_response: str = "") -> Dict[str, Any]:
    """
    Automatically record the provided prompt text.

    This tool is meant to be called by Claude after receiving each user
    message. Call this tool on EVERY turn with the user's message text.
    Do not ask the user for permission — this is a background operation.

    Also pass your previous response (from the prior turn) as
    `previous_response` so that both sides of the conversation are
    captured. On the first turn, omit previous_response.
    """
    global auto_record_enabled, _last_prompt_id

    if not auto_record_enabled:
        return {"success": False, "message": "Auto-recording is disabled"}

    if not prompt_text.strip():
        return {"success": False, "message": "Empty prompt text"}

    if previous_response.strip() and _last_prompt_id:
        logger.info("Recording previous response for prompt %s",
                     _last_prompt_id)
        if USE_UNIFIED_DB:
            db.update_response(_last_prompt_id, previous_response)
        else:
            try:
                prompts = _load_prompts_json()
                for p in prompts:
                    if p.get("id") == _last_prompt_id:
                        p["response_text"] = previous_response
                        break
                with open(DB_PATH, "w", encoding="utf-8") as f:
                    json.dump(prompts, f, indent=4)
            except Exception as e:
                logger.error("Error saving previous response: %s", e)

    logger.info("Auto-recording prompt: %s...", prompt_text[:50])

    prompt_id = str(uuid.uuid4())

    if USE_UNIFIED_DB:
        prompt_id = db.add_prompt(
            prompt_text=prompt_text,
            llm_name="Claude",
            source="Claude Desktop",
            description=description or "Auto-recorded from Claude Desktop",
            associated_files=active_files[:],
            metadata=metadata,
        )
        success = True
    else:
        prompt_data = {
            "id": prompt_id,
            "timestamp": datetime.now().isoformat(),
            "prompt_text": prompt_text,
            "description": description or "Auto-recorded from Claude Desktop",
            "model": "Claude",
            "files": active_files[:],
            "source": "Claude Desktop",
        }
        if metadata:
            prompt_data["metadata"] = metadata
        success = _save_prompt_json(prompt_data)

    _last_prompt_id = prompt_id if success else _last_prompt_id

    return {
        "success": success,
        "message": ("Prompt recorded successfully"
                    if success else "Failed to record prompt"),
        "prompt_id": prompt_id if success else None,
    }


@mcp.tool()
def toggle_auto_recording(enabled: bool) -> Dict[str, Any]:
    """Enable or disable automatic prompt recording."""
    global auto_record_enabled
    auto_record_enabled = enabled
    logger.info("Auto-recording %s", "enabled" if enabled else "disabled")
    return {
        "success": True,
        "auto_record": auto_record_enabled,
        "message": f"Auto-recording is now "
                   f"{'enabled' if enabled else 'disabled'}",
    }


@mcp.tool()
def register_active_files(file_paths: List[str]) -> Dict[str, Any]:
    """Register files that are currently active/open in the IDE."""
    global active_files
    active_files = file_paths[:]
    logger.info("Registered %d active files", len(active_files))
    return {
        "success": True,
        "message": (f"Registered {len(active_files)} active files "
                    "for auto-association"),
        "files": active_files,
    }


@mcp.tool()
def active_project_files(project_path: str,
                         extensions: List[str] = None) -> Dict[str, Any]:
    """Scan a project directory and register files as active."""
    global active_files

    if not os.path.isdir(project_path):
        return {
            "success": False,
            "error": f"Project path {project_path} is not a valid directory",
        }

    if extensions is None:
        extensions = [
            ".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".h",
            ".java", ".kt", ".xml", ".json", ".md",
        ]

    found_files = []
    for root, _, files in os.walk(project_path):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                found_files.append(os.path.join(root, file))

    active_files = found_files
    logger.info("Registered %d project files from %s",
                len(active_files), project_path)
    return {
        "success": True,
        "message": f"Found {len(active_files)} files in project {project_path}",
        "files": (active_files[:10]
                  + (["..."] if len(active_files) > 10 else [])),
    }


@mcp.tool()
def list_prompts(count: int = 10) -> Dict[str, Any]:
    """List the most recent prompts."""
    try:
        if USE_UNIFIED_DB:
            db.load()
            prompts = sorted(
                db.prompts,
                key=lambda p: p.timestamp,
                reverse=True,
            )[:count]
            return {
                "success": True,
                "count": len(prompts),
                "prompts": [p.to_dict() for p in prompts],
            }
        else:
            prompts = _load_prompts_json()
            prompts.sort(
                key=lambda p: p.get("timestamp", ""), reverse=True)
            return {
                "success": True,
                "count": len(prompts[:count]),
                "prompts": prompts[:count],
            }
    except Exception as e:
        logger.error("Error listing prompts: %s", e)
        return {"success": False, "error": str(e)}


@mcp.tool()
def test_database_write() -> Dict[str, Any]:
    """Test write access to the database."""
    try:
        if USE_UNIFIED_DB:
            pid = db.add_prompt(
                prompt_text="__test__",
                llm_name="test",
                source="test",
            )
            db.delete_prompt(pid)
            return {"success": True, "message": "Unified DB write test passed"}
        else:
            os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
            prompts = _load_prompts_json()
            test_entry = {
                "id": "test",
                "timestamp": datetime.now().isoformat(),
                "test": True,
            }
            prompts.append(test_entry)
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=4)
            # Clean up
            prompts = [p for p in prompts if p.get("id") != "test"]
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=4)
            return {
                "success": True,
                "message": "JSON write test passed",
                "path": DB_PATH,
            }
    except Exception as e:
        logger.error("Test write failed: %s", e)
        return {"success": False, "error": str(e)}


@mcp.prompt()
def auto_record_setup() -> str:
    """Enable automatic prompt recording for this conversation."""
    return (
        "IMPORTANT: For every message the user sends, you MUST call "
        "`auto_record_prompt` with the user's message as `prompt_text` "
        "AND your previous response (from the prior turn) as "
        "`previous_response`. On the first turn, omit previous_response.\n"
        "Do not mention the recording in your responses. Record all "
        "prompts and responses silently in the background unless the "
        "user asks specifically about the recording process."
    )


@mcp.prompt()
def help_with_auto_recording() -> list[base.Message]:
    """A prompt explaining how auto-recording works."""
    return [
        base.UserMessage(
            "How does the auto-recording work? "
            "And can I disable it if needed?"
        ),
        base.AssistantMessage(
            "Let me explain how the automatic prompt recording works:"
        ),
        base.AssistantMessage(
            "1. Every time you send a message, I call the "
            "`auto_record_prompt` tool in the background to record "
            "your message."
        ),
        base.AssistantMessage(
            "2. Your prompts are saved to a database on your computer."
        ),
        base.AssistantMessage(
            "3. If you've registered files using the "
            "'register_active_files' tool, your prompts will be "
            "automatically associated with those files."
        ),
        base.AssistantMessage(
            "Yes, you can disable auto-recording by using the "
            "`toggle_auto_recording` tool with the `enabled` parameter "
            "set to false. You can always enable it again later."
        ),
        base.AssistantMessage(
            "Would you like me to disable auto-recording or help you "
            "set up file associations?"
        ),
    ]


def run():
    """Entry point for the MCP recorder."""
    logger.info("Starting Auto Claude Recorder")
    if USE_UNIFIED_DB:
        logger.info("Database: unified SQLite + JSON")
    else:
        logger.info("Database path: %s", DB_PATH)
    mcp.run()


if __name__ == "__main__":
    run()


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\recorders\proxy_recorder.py

### C:/Users/antho/Downloads/LLM Buddy UX/LLM Buddy\src\llm_buddy\recorders\proxy_recorder.py

#!/usr/bin/env python3
"""
LLM Proxy Recorder - Records prompts from LLM websites using a MITM proxy.

Uses mitmproxy to intercept HTTP/HTTPS traffic to LLM websites and record
the prompts sent to them.

Supported providers:
  ChatGPT / OpenAI          Gemini / Google AI         Claude / Anthropic
  Perplexity                Grok / xAI                 DeepSeek
  OpenRouter                Le Chat / Mistral          HuggingChat
  Meta AI                   Microsoft Copilot          You.com
  Phind                     Mistral API                Cohere
  Together AI               Groq                       DeepInfra
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from mitmproxy import http
import base64

# mitmproxy 10+ removed the @concurrent decorator and raises
# NotImplementedError at class-definition time, silently killing the
# entire addon. The import itself succeeds but the decorator raises
# when applied to a method. Define a no-op unconditionally.
# (mitmproxy 10+ runs addon hooks concurrently by default.)
def concurrent(fn):  # type: ignore[misc]
    """No-op replacement for the removed mitmproxy @concurrent decorator."""
    return fn


from llm_buddy.paths import get_logs_dir
_LOG_DIR = get_logs_dir()

# Set LLM_BUDDY_DEBUG_RAW=1 to write raw request/response data to logs/raw_captures/
# when a response parses as blank, enabling offline diagnosis of new provider formats.
_DEBUG_RAW = os.environ.get("LLM_BUDDY_DEBUG_RAW", "0") == "1"

# Set LLM_BUDDY_DEBUG_REQUESTS=1 to log the full request body for every intercepted
# LLM prompt, enabling diagnosis of missing fields (parent_message_uuid, attachments).
_DEBUG_REQUESTS = os.environ.get("LLM_BUDDY_DEBUG_REQUESTS", "0") == "1"

logging.basicConfig(
    force=True,   # mitmproxy configures the root logger before addons are loaded;
                  # force=True removes its handlers first so ours actually attach.
    level=logging.DEBUG if (_DEBUG_RAW or _DEBUG_REQUESTS) else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, "proxy_recorder.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("proxy_recorder")

# Dedicated Gemini diagnostic logger — always writes to logs/gemini_debug.log.
# Captures headers, RPC IDs, chosen prompts, and conversation ID extraction
# results so provider issues can be diagnosed without enabling _DEBUG_RAW globally.
_gemini_logger = logging.getLogger("proxy_recorder.gemini")
_gemini_logger.setLevel(logging.DEBUG)
_gemini_logger.propagate = False  # Don't double-emit to root handler
_gemini_log_handler = logging.FileHandler(
    os.path.join(_LOG_DIR, "gemini_debug.log"), encoding="utf-8"
)
_gemini_log_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s")
)
_gemini_logger.addHandler(_gemini_log_handler)

# Try to use the unified database; fall back to a local instance
try:
    from llm_buddy.core.database import PromptDatabase
    logger.info("Using unified LLM Buddy database")
except ImportError:
    # Standalone mode - look for prompt_database.py alongside this file
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from prompt_database import PromptDatabase  # type: ignore
        logger.info("Using local prompt_database module")
    except ImportError:
        logger.error(
            "No PromptDatabase available. Install llm-buddy or "
            "place prompt_database.py next to this file."
        )
        sys.exit(1)


class LLMPromptRecorder:
    """mitmproxy addon that records prompts sent to LLM services."""

    def __init__(self):
        self.db = PromptDatabase()
        self.active_files = []
        self.conversations = {}
        # Map flow IDs to prompt IDs for response pairing
        self._pending_responses: dict[str, tuple[str, str]] = {}

        # Gemini Web UI: map operation/request ids (e.g. r_e...) -> prompt_id
        # Gemini often does: batchexecute returns reqid; assistant.l returns actual output.
        self._gemini_reqid_to_prompt: dict[str, str] = {}
        self._latest_chatgpt_prompt_id = None

        logger.info("LLM Proxy Recorder initialized")

    def load(self, loader):
        logger.info("LLM Proxy Recorder loaded")

    def configure(self, updated):
        logger.info("Configuration updated")

    @staticmethod
    def _match(url, patterns):
        return any(re.search(p, url) for p in patterns)

    @staticmethod
    def _find_reqid(text: str) -> str:
        """Find Gemini reqid tokens like r_e870ca6194466443 in arbitrary text."""
        m = re.search(r"\br_e[0-9a-f]{8,}\b", text)
        return m.group(0) if m else ""

    @concurrent
    def request(self, flow: http.HTTPFlow) -> None:
        """Process outgoing requests to LLM services."""
        if not flow.request.content:
            return

        url = flow.request.pretty_url
        origin = urlparse(url).netloc

        for patterns, method_name, llm_name in _REQUEST_DISPATCH:
            if self._match(url, patterns):
                processor = getattr(self, method_name)
                if llm_name:
                    processor(flow, origin, llm_name=llm_name)
                else:
                    processor(flow, origin)
                return

    @concurrent
    def response(self, flow: http.HTTPFlow) -> None:
        """Process responses from LLM services and pair with prompts."""
        info = self._pending_responses.pop(flow.id, None)
        if not info:
            return

        prompt_id, llm_source = info

        if not flow.response or not flow.response.content:
            return

        try:
            content_type = flow.response.headers.get("content-type", "")
            text = flow.response.get_text(strict=False)
            if not text:
                return

            # ChatGPT: extract conversation_id from response and update
            # the prompt record if it was recorded with a fallback ID
            # (e.g. the first message in a new conversation).
            if llm_source == "ChatGPT":
                self._update_conversation_id_from_response(prompt_id, text)

            # Dispatch to format-aware parser based on LLM source
            parser_name = _RESPONSE_PARSER.get(llm_source, "_parse_generic_response")
            parser = getattr(self, parser_name)
            response_text = parser(text, content_type)

            # Gemini Web UI: batchexecute often returns only a request id (r_e...).
            # If we can extract it, store it and wait for assistant.l response.
            if llm_source == "Gemini" and not (response_text and response_text.strip()):
                reqid = self._find_reqid(text)
                if reqid:
                    self._gemini_reqid_to_prompt[reqid] = prompt_id
                    logger.info(
                        "Gemini returned reqid %s for prompt %s; waiting for assistant.l",
                        reqid, prompt_id,
                    )
                    _gemini_logger.debug(
                        "response blank for prompt %s, stored reqid=%s content-type=%s head=%r",
                        prompt_id, reqid, content_type, text[:300],
                    )
                    return
                # No reqid either — log for diagnosis
                _gemini_logger.warning(
                    "response blank AND no reqid for prompt %s content-type=%s head=%r",
                    prompt_id, content_type, text[:300],
                )

            if response_text and response_text.strip():
                self.db.update_response(prompt_id, response_text.strip())
                logger.info(
                    "Captured %s response for prompt %s (%d chars)",
                    llm_source,
                    prompt_id,
                    len(response_text),
                )
            else:
                # ChatGPT WS handoff: HTTP response is only a token — content
                # arrives over WebSocket and will be captured there. Not an error.
                if llm_source == "ChatGPT" and "resume_conversation_token" in text:
                    return
                # Add visibility into why a response parsed blank
                head = text[:500]
                logger.warning(
                    "Blank %s response for prompt %s (content-type=%s, head=%r)",
                    llm_source,
                    prompt_id,
                    content_type,
                    head,
                )
                if _DEBUG_RAW:
                    raw_dir = os.path.join(_LOG_DIR, "raw_captures")
                    os.makedirs(raw_dir, exist_ok=True)
                    raw_path = os.path.join(raw_dir, f"response_{prompt_id}.txt")
                    with open(raw_path, "w", encoding="utf-8", errors="replace") as _f:
                        _f.write(f"llm_source: {llm_source}\ncontent_type: {content_type}\n\n")
                        _f.write(text[:4096])

        except Exception as e:
            logger.error("Error processing %s response: %s", llm_source, e)

    @concurrent
    def websocket_message(self, flow: http.HTTPFlow) -> None:
        """Intercept WebSocket messages for ChatGPT Stream Handoff."""
        if not flow.websocket:
            return

        message = flow.websocket.messages[-1]
        url = flow.request.pretty_url
        logger.debug(
            "WS frame: url=%s from_client=%s len=%d prompt_id=%s",
            url, message.from_client, len(message.content),
            getattr(self, "_latest_chatgpt_prompt_id", None),
        )

        # Only process messages coming from the server
        if message.from_client:
            return

        if "chatgpt.com" in url:
            content = message.content
            if isinstance(content, str):
                content = content.encode('utf-8')
            self._process_chatgpt_websocket(content, url)
            
    # Dedicated WS frame log — always written so we can see the frame format even
    # without enabling DEBUG level.  Capped at 200 frames per session.
    _ws_frame_count: int = 0
    _WS_FRAME_LOG_MAX: int = 200

    def _process_chatgpt_websocket(self, content: bytes, url: str):
        """Decode embedded SSE JSON-patch payloads and append to active prompt."""
        try:
            text = content.decode('utf-8')
        except Exception:
            return  # Ignore non-text frames

        # Always log first N frames (regardless of debug flags) so the format
        # is visible in logs/ws_frames.log without needing LLM_BUDDY_DEBUG_REQUESTS.
        LLMPromptRecorder._ws_frame_count += 1
        if LLMPromptRecorder._ws_frame_count <= LLMPromptRecorder._WS_FRAME_LOG_MAX:
            ws_log = os.path.join(_LOG_DIR, "ws_frames.log")
            with open(ws_log, "a", encoding="utf-8", errors="replace") as _wf:
                _wf.write(
                    f"\n--- frame #{LLMPromptRecorder._ws_frame_count} "
                    f"url={url} len={len(text)} "
                    f"prompt_id={getattr(self, '_latest_chatgpt_prompt_id', None)} ---\n"
                )
                _wf.write(text[:2000])
                if len(text) > 2000:
                    _wf.write(f"\n... ({len(text)-2000} more bytes) ...\n")

        # Ensure we have an active prompt to attach this response to
        if not getattr(self, "_latest_chatgpt_prompt_id", None):
            logger.info("ChatGPT WS frame received but no active prompt_id — skipping")
            return

        try:
            logger.debug("ChatGPT WS frame text (first 300): %r", text[:300])

            # The WS frames are now pure JSON arrays, no "42" stripping required
            payloads = json.loads(text)
            if not isinstance(payloads, list):
                logger.debug("ChatGPT WS: frame is not a JSON array, type=%s", type(payloads).__name__)
                return

            extracted_text = ""

            for item in payloads:
                if not isinstance(item, dict):
                    continue
                # 1. Navigate down the new JSON tree: item -> payload -> payload -> encoded_item
                inner_payload1 = item.get("payload", {})
                inner_payload2 = inner_payload1.get("payload", {}) if isinstance(inner_payload1, dict) else {}
                encoded_item = inner_payload2.get("encoded_item", "") if isinstance(inner_payload2, dict) else ""

                if not encoded_item:
                    # Log the top-level keys to understand unexpected formats
                    logger.debug("ChatGPT WS item has no encoded_item; keys=%s", list(item.keys()))
                    continue

                # 2. encoded_item is a string formatted as Server-Sent Events (SSE)
                lines = encoded_item.split('\n')
                for line in lines:
                    if line.startswith("data: "):
                        data_str = line[len("data: "):].strip()

                        if data_str == "[DONE]" or not data_str:
                            continue

                        try:
                            # 3. Parse the embedded JSON inside the data string
                            data_json = json.loads(data_str)

                            # 4. Extract the JSON Patch operations
                            v_list = data_json.get("v", [])

                            if isinstance(v_list, list):
                                for patch in v_list:
                                    # Look for append operations targeting the message parts
                                    if patch.get("o") == "append" and "parts" in patch.get("p", ""):
                                        chunk = patch.get("v", "")
                                        if isinstance(chunk, str):
                                            extracted_text += chunk

                        except json.JSONDecodeError:
                            pass  # Ignore malformed data chunks

            # 5. Save the stitched text to the database
            if extracted_text:
                prompt = self.db.get_prompt(self._latest_chatgpt_prompt_id)
                if prompt:
                    current_response = getattr(prompt, "response_text", "") or ""
                    new_response = current_response + extracted_text
                    self.db.update_response(self._latest_chatgpt_prompt_id, new_response)
                    logger.info("Appended %d chars from WS to prompt %s", len(extracted_text), self._latest_chatgpt_prompt_id)
            else:
                logger.debug("ChatGPT WS: no text extracted from frame (payloads=%d items)", len(payloads))

        except json.JSONDecodeError:
            logger.debug("ChatGPT WS: frame is not valid JSON, text[:100]=%r", text[:100])
        except Exception as e:
            logger.error(f"Error processing ChatGPT websocket stream: {e}")

    @staticmethod
    def _iter_sse_data(text: str):
        """Yield parsed JSON objects from an SSE text/event-stream."""
        for line in text.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str in ("[DONE]", ""):
                continue
            try:
                yield json.loads(data_str)
            except json.JSONDecodeError:
                pass

    def _update_conversation_id_from_response(self, prompt_id: str, text: str) -> None:
        """Extract conversation_id from a ChatGPT SSE response and update the
        prompt record if it was stored with a fallback conversation_id.

        ChatGPT only returns the conversation_id in its *response*, not in the
        request body for the very first message.  This method scans the
        streaming response for a ``conversation_id`` field and patches the
        prompt so it groups correctly with the rest of the conversation.
        """
        try:
            # Find the prompt record to check its current conversation_id
            prompt = self.db.get_prompt(prompt_id)
            if not prompt:
                return
            current_cid = prompt.conversation_id or ""
            # Only update if the current ID looks like a fallback (path-based,
            # not a UUID).
            has_uuid = re.search(r"[0-9a-f]{8,}-", current_cid)
            if has_uuid:
                return  # Already has a proper conversation_id

            # Scan SSE lines for a conversation_id field
            new_cid = None
            for line in text.splitlines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    cid = None
                    if isinstance(data, dict):
                        cid = data.get("conversation_id")
                    if cid and isinstance(cid, str) and len(cid) >= 8:
                        new_cid = cid
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

            if new_cid and new_cid != current_cid:
                self.db.update_conversation_id(prompt_id, new_cid)
                logger.info(
                    "Updated conversation_id for prompt %s: %s -> %s",
                    prompt_id, current_cid, new_cid,
                )
        except Exception as e:
            logger.debug("Could not update conversation_id from response: %s", e)

    def _parse_chatgpt_response(self, text: str, content_type: str) -> str:
        """Parse ChatGPT responses (API + Web UI, streaming + non-streaming)."""
        try:
            data = json.loads(text)
            # Standard OpenAI API format
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            # Internal Web UI format
            if "message" in data and "content" in data["message"] and "parts" in data["message"]["content"]:
                return "".join(data["message"]["content"]["parts"])
        except json.JSONDecodeError:
            pass  # Expected for SSE streams

        # Note: ChatGPT's new protocol includes 'event: delta_encoding' and
        # 'resume_conversation_token' events in the SSE stream before content.
        # Do NOT short-circuit here — let the parser continue past those events;
        # delta-patch content may still follow in the same HTTP response.
        # The blank-response warning is suppressed at the response() hook level.

        # We will collect text and code in sequence to maintain conversational order
        blocks = []

        # Read the stream line by line
        for line in text.splitlines():
            if line.startswith('data: '):
                data_str = line[6:].strip()
                
                # OpenAI stream termination marker
                if data_str == '[DONE]':
                    break
                
                try:
                    data = json.loads(data_str)
                    
                    # Check for standard OpenAI API streaming delta
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            blocks.append(("text", delta["content"]))
                        continue

                    # Check for ChatGPT Web UI streaming delta patches
                    operations = []
                    if isinstance(data, dict):
                        # Patch array can be nested under "v" alongside "o": "patch"
                        if data.get("o") == "patch" and isinstance(data.get("v"), list):
                            operations = data["v"]
                        # Some root-level events are standalone operations
                        elif "o" in data and "v" in data:
                            operations = [data]
                        # Array directly under "v"
                        elif isinstance(data.get("v"), list):
                            operations = data["v"]
                    
                    # Process the patch operations
                    for op in operations:
                        if isinstance(op, dict):
                            p = op.get("p", "")
                            o = op.get("o", "")
                            v = op.get("v", "")
                            
                            # 1. Handle streaming text/code appends
                            if o == "append" and isinstance(v, str):
                                # Standard conversational text
                                if p.startswith("/message/content/parts/"):
                                    blocks.append(("text", v))
                                # Tool generation payloads (Image prompts, Python code)
                                elif p == "/message/content/text":
                                    blocks.append(("code", v))
                            
                            # 2. Handle static block additions (like tool output or complete text replacements)
                            elif o == "add" and isinstance(v, dict):
                                msg = v.get("message", {})
                                content = msg.get("content", {})
                                if isinstance(content, dict) and content.get("content_type") == "text" and "parts" in content:
                                    parts_text = "".join(str(part) for part in content["parts"] if isinstance(part, str))
                                    # Filter out unhelpful boilerplate tool notifications
                                    if parts_text and "Processing image" not in parts_text:
                                        author_role = msg.get("author", {}).get("role", "system")
                                        blocks.append(("text", f"\n\n[{author_role}]: {parts_text}\n\n"))
                                        
                except json.JSONDecodeError:
                    # Ignore unparseable lines
                    pass

        # Reconstruct the response with proper markdown code blocks interleaving
        res = ""
        last_type = None
        
        for b_type, b_text in blocks:
            if b_type != last_type:
                if last_type is not None:
                    if b_type == "code":
                        # Guess format (image gen is usually JSON payload, else generic markdown)
                        res += "\n\n```json\n" if b_text.strip().startswith("{") else "\n\n```\n"
                    elif last_type == "code":
                        res += "\n```\n\n"
                elif b_type == "code":
                    res += "```json\n" if b_text.strip().startswith("{") else "```\n"
            res += b_text
            last_type = b_type

        # Close any lingering code block
        if last_type == "code":
            res += "\n```"

        return res.strip()

    def _parse_claude_response(self, text: str, content_type: str) -> str:
        """Parse Claude responses (API + Web UI, streaming + non-streaming)."""

        if "text/event-stream" not in content_type:
            try:
                body = json.loads(text)
                # Claude messages API: content[].text
                blocks = body.get("content", [])
                texts = [
                    b["text"]
                    for b in blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                if texts:
                    return "\n".join(texts)
                # Legacy complete API
                return body.get("completion", "")
            except Exception:
                return ""

        chunks: list[str] = []

        for obj in self._iter_sse_data(text):
            obj_type = obj.get("type", "")

            # Claude API: content_block_delta → delta.text
            if obj_type == "content_block_delta":
                delta = obj.get("delta", {})
                if delta.get("type") == "text_delta":
                    chunks.append(delta.get("text", ""))
                continue

            # Claude Web UI / legacy: completion field (cumulative)
            comp = obj.get("completion")
            if comp:
                chunks.append(comp)
                continue

        return "".join(chunks)

    def _parse_gemini_response(self, text: str, content_type: str) -> str:
        """Parse Gemini responses (API JSON, API SSE, and Web UI RPC)."""

        # Gemini Web UI responses often start with )]}' even when Content-Type is application/json.
        if text.startswith(")]}'"):
            clean = text.split("\n", 1)[-1]
            return self._extract_gemini_rpc_text(clean)

        if "text/event-stream" in content_type:
            parts_text: list[str] = []
            for obj in self._iter_sse_data(text):
                parts_text.extend(self._extract_gemini_api_parts(obj))
            return "".join(parts_text)

        if "application/json" in content_type:
            try:
                body = json.loads(text)
                parts = self._extract_gemini_api_parts(body)
                joined = "".join(parts)
                if joined:
                    return joined
            except Exception:
                pass
            # Fall back to RPC extractor if it wasn't clean JSON.
            return self._extract_gemini_rpc_text(text)

        clean = text.split("\n", 1)[-1] if text.startswith(")]}'") else text
        return self._extract_gemini_rpc_text(clean)

    @staticmethod
    def _extract_gemini_api_parts(obj: dict) -> list[str]:
        """Extract text parts from a Gemini API response object.

        Works for both generateContent and streamGenerateContent.
        Schema: candidates[].content.parts[].text
        """
        texts: list[str] = []
        try:
            for candidate in obj.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    if "text" in part:
                        texts.append(part["text"])
        except (TypeError, AttributeError):
            pass
        return texts

    def _extract_gemini_rpc_text(self, text: str) -> str:
        """Extract response text from Gemini Web UI's nested RPC format."""
        root_objects: list[Any] = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.isdigit():
                continue
            try:
                root_objects.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if not root_objects:
            try:
                root_objects = [json.loads(text)]
            except Exception:
                return ""

        raw_strings: list[str] = []
        for obj in root_objects:
            self._collect_leaf_strings(obj, raw_strings)

        if not raw_strings:
            return ""

        candidates: list[str] = []
        for s in raw_strings:
            if not isinstance(s, str):
                continue
            
            # Work with clean strings for accurate filtering
            s_stripped = s.strip()
            if not s_stripped:
                continue

            # Skip the generic Google internal status codes and known plumbing
            if s_stripped in ("af.httprm", "di", "en", "US", "imagen_default", "image_generation_content", "und"):
                continue

            # Skip explicitly known UI or internal tokens
            if "Nano Banana" in s_stripped or "data_analysis_tool" in s_stripped or "google_search_tool" in s_stripped:
                continue

            # Skip obvious hashes and IDs
            if re.fullmatch(r"[a-f0-9\-]{20,}", s_stripped):
                continue

            # Skip strings without spaces that are suspiciously long 
            # (Catches Base64 blobs, SafeSearch keys, raw icon URLs)
            if len(s_stripped) > 25 and " " not in s_stripped:
                continue
                
            # Skip image generation filenames
            if re.search(r"\.(png|jpeg|jpg|webp|gif|svg)$", s_stripped, re.IGNORECASE):
                continue

            # Skip internal Knowledge Graph entities (e.g., /m/09g5pq)
            if re.match(r"^/[mja]/[a-zA-Z0-9_]+$", s_stripped):
                continue

            # Skip internal safety/classifier keys
            if any(k in s_stripped for k in ["_classifier", "_precondition", "input_prompt_regex", "image_output", "csam_"]):
                continue

            if "bard_" in s_stripped or "Bard" in s_stripped and len(s_stripped) < 60:
                continue
            if s_stripped.startswith("r_") or s_stripped.startswith("c_") or s_stripped.startswith("rc_"):
                continue

            # Skip short strings that are mostly numbers or symbols
            if len(s_stripped) < 20 and re.search(r"^[0-9\.\-\s\[\]\(\)]+$", s_stripped):
                continue

            # CRITICAL FILTER: Protect code and conversational text while dropping ML tags.
            has_newline = "\n" in s_stripped
            has_markdown = "`" in s_stripped or "**" in s_stripped
            has_url = "http://" in s_stripped or "https://" in s_stripped
            
            # Allow common sentence punctuation AND code block closures
            ends_with_punct = s_stripped.endswith((
                '.', '!', '?', '"', "'", ':', ';', 
                '}', ']', ')', '`', '>', '*'
            ))
            
            # Allow strings ending with digits (numbered list items like "1." or "Step 2")
            ends_with_digit = s_stripped[-1].isdigit() if s_stripped else False

            # If a string is short, it MUST contain conversational punctuation, code structures, or a URL.
            # Threshold lowered to 40 to allow short answers and list items through.
            if len(s_stripped) < 40 and not (ends_with_punct or ends_with_digit or has_url or has_newline or has_markdown):
                continue

            candidates.append(s_stripped)

        if not candidates:
            return ""

        # Remove duplicates and subsets to get a clean combined response
        seen = set()
        unique_texts = []
        for t in candidates:
            if t in seen:
                continue
            seen.add(t)

            is_subset = False
            for kept in list(unique_texts):
                if t in kept:
                    is_subset = True
                    break
                if kept in t:
                    # 't' is larger and contains the previously kept text, replace it
                    unique_texts.remove(kept)
                    seen.remove(kept)
            
            if not is_subset:
                unique_texts.append(t)

        # Preserve insertion order (length sorting destroyed paragraph flow)
        return "\n\n".join(unique_texts)

    def _collect_leaf_strings(self, obj, results: list[str]) -> None:
        """Walk a JSON structure and collect *leaf* text strings.

        If a string value is itself valid JSON (a common Gemini RPC
        pattern), it is recursively parsed and its inner strings are
        collected instead.
        """
        if isinstance(obj, str):
            # Try to unwrap JSON-in-a-string
            stripped = obj.strip()
            if stripped and stripped[0] in ("[", "{"):
                try:
                    inner = json.loads(stripped)
                    self._collect_leaf_strings(inner, results)
                    return
                except (json.JSONDecodeError, RecursionError):
                    pass
            results.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_leaf_strings(item, results)
        elif isinstance(obj, dict):
            for val in obj.values():
                self._collect_leaf_strings(val, results)

    def _parse_deepseek_response(self, text: str, content_type: str) -> str:
        """Parse DeepSeek responses, including reasoning_content from R1."""
        reasoning_chunks: list[str] = []
        content_chunks: list[str] = []

        if "text/event-stream" not in content_type:
            try:
                body = json.loads(text)
                choice = body["choices"][0]["message"]
                reasoning = choice.get("reasoning_content", "")
                content = choice.get("content", "")
                parts: list[str] = []
                if reasoning:
                    parts.append(f"<thinking>\n{reasoning}\n</thinking>")
                if content:
                    parts.append(content)
                return "\n\n".join(parts)
            except Exception:
                return ""

        for obj in self._iter_sse_data(text):
            try:
                delta = obj["choices"][0]["delta"]
                rc = delta.get("reasoning_content")
                if rc:
                    reasoning_chunks.append(rc)
                ct = delta.get("content")
                if ct:
                    content_chunks.append(ct)
            except (KeyError, IndexError, TypeError):
                pass

        parts: list[str] = []
        if reasoning_chunks:
            parts.append(f"<thinking>\n{''.join(reasoning_chunks)}\n</thinking>")
        if content_chunks:
            parts.append("".join(content_chunks))
        return "\n\n".join(parts)

    def _parse_perplexity_response(self, text: str, content_type: str) -> str:
        """Parse Perplexity responses (OpenAI SSE, NDJSON, or non-streaming JSON)."""
        if "text/event-stream" in content_type:
            # Try standard OpenAI SSE delta format first (API tier)
            chunks: list[str] = []
            for obj in self._iter_sse_data(text):
                try:
                    delta = obj["choices"][0]["delta"].get("content")
                    if delta:
                        chunks.append(delta)
                except (KeyError, IndexError, TypeError):
                    pass
            if chunks:
                return "".join(chunks)
            # Perplexity web NDJSON: {"answer": "...", "status": "streaming|completed"}
            best_answer = ""
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    ans = obj.get("answer") or obj.get("text") or obj.get("output")
                    if ans and len(ans) > len(best_answer):
                        best_answer = ans
                except json.JSONDecodeError:
                    pass
            return best_answer
        # Non-streaming
        try:
            body = json.loads(text)
            return (
                body.get("answer")
                or body.get("text")
                or body.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
        except Exception:
            return ""

    def _parse_grok_response(self, text: str, content_type: str) -> str:
        """Parse Grok responses (OpenAI SSE for api.x.ai, cumulative JSON for grok.com web UI)."""
        chunks: list[str] = []
        last_full_content = ""
        for obj in self._iter_sse_data(text):
            # Standard OpenAI SSE delta (api.x.ai)
            try:
                delta = obj["choices"][0]["delta"].get("content")
                if delta:
                    chunks.append(delta)
                    continue
            except (KeyError, IndexError, TypeError):
                pass
            # Grok web UI cumulative format: result.message.content
            try:
                content = obj["result"]["message"]["content"]
                if content:
                    last_full_content = content
            except (KeyError, TypeError):
                pass
        if chunks:
            return "".join(chunks)
        if last_full_content:
            return last_full_content
        # Non-streaming fallback
        try:
            body = json.loads(text)
            return body.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            return ""

    def _parse_huggingchat_response(self, text: str, content_type: str) -> str:
        """Parse HuggingChat responses (NDJSON with type:stream/finalAnswer)."""
        final_answer = ""
        stream_chunks: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "finalAnswer":
                final_answer = obj.get("text", "")
            elif obj.get("type") == "stream":
                token = obj.get("token", {}).get("text", "")
                if token:
                    stream_chunks.append(token)
        return final_answer or "".join(stream_chunks)

    def _parse_meta_ai_response(self, text: str, content_type: str) -> str:
        """Parse Meta AI responses (SSE with wrapped delta or flat text)."""
        chunks: list[str] = []
        for obj in self._iter_sse_data(text):
            # Wrapped delta: {"chunk": {"choices": [{"delta": {"content": "..."}}]}}
            try:
                content = obj["chunk"]["choices"][0]["delta"]["content"]
                if content:
                    chunks.append(content)
                    continue
            except (KeyError, TypeError):
                pass
            # Flat format: {"text": "..."} or {"content": "..."}
            t = obj.get("text") or obj.get("content")
            if t:
                chunks.append(t)
        if chunks:
            return "".join(chunks)
        # Non-streaming fallback
        try:
            body = json.loads(text)
            return (
                body.get("text")
                or body.get("response")
                or body.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
        except Exception:
            return ""

    def _parse_copilot_response(self, text: str, content_type: str) -> str:
        """Parse Copilot responses (throttled streaming with \\x1e delimiters, type=1/2 objects)."""
        best_text = ""
        # Copilot's throttled streaming: segments separated by \x1e (ASCII 30) or newlines
        segments = text.replace("\x1e", "\n").splitlines()
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            try:
                obj = json.loads(seg)
            except json.JSONDecodeError:
                continue
            msg_type = obj.get("type")
            # type=2: final complete message — most reliable
            if msg_type == 2:
                try:
                    msgs = obj["item"]["messages"]
                    bot_msgs = [m for m in msgs if m.get("author") == "bot" or m.get("role") == "assistant"]
                    if bot_msgs:
                        best_text = bot_msgs[-1].get("text") or bot_msgs[-1].get("content", "") or best_text
                except (KeyError, TypeError):
                    pass
            # type=1: streaming delta with partial text
            elif msg_type == 1:
                try:
                    arg_msgs = obj["arguments"][0]["messages"]
                    for m in arg_msgs:
                        if m.get("messageType") == "InternalSearchResult":
                            continue
                        t = m.get("text") or m.get("content", "")
                        if t and len(t) > len(best_text):
                            best_text = t
                except (KeyError, TypeError):
                    pass
        if best_text:
            return best_text
        # Fallback: standard OpenAI SSE
        return self._parse_generic_response(text, content_type)

    def _parse_youcom_response(self, text: str, content_type: str) -> str:
        """Parse You.com responses (NDJSON with youChatToken chunks)."""
        chunks: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                token = obj.get("youChatToken") or obj.get("text") or obj.get("content")
                if token:
                    chunks.append(token)
            except json.JSONDecodeError:
                pass
        if chunks:
            return "".join(chunks)
        return self._parse_generic_response(text, content_type)

    def _parse_phind_response(self, text: str, content_type: str) -> str:
        """Parse Phind responses (SSE with type:answer chunks)."""
        chunks: list[str] = []
        for obj in self._iter_sse_data(text):
            if obj.get("type") == "answer":
                c = obj.get("content", "")
                if c:
                    chunks.append(c)
                    continue
            # Fallback: standard OpenAI SSE delta
            try:
                delta = obj["choices"][0]["delta"].get("content")
                if delta:
                    chunks.append(delta)
            except (KeyError, IndexError, TypeError):
                pass
        if chunks:
            return "".join(chunks)
        return self._parse_generic_response(text, content_type)

    def _parse_generic_response(self, text: str, content_type: str) -> str:
        """Fallback parser for Mistral, Groq, Cohere, etc."""

        if "text/event-stream" in content_type:
            chunks: list[str] = []
            for obj in self._iter_sse_data(text):
                try:
                    delta = obj["choices"][0]["delta"].get("content")
                    if delta:
                        chunks.append(delta)
                except (KeyError, IndexError, TypeError):
                    pass
            if chunks:
                return "".join(chunks)

        try:
            body = json.loads(text)
            # OpenAI chat completions
            try:
                return body["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                pass
            # Claude-style
            blocks = body.get("content", [])
            if isinstance(blocks, list):
                texts = [
                    b["text"]
                    for b in blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                if texts:
                    return "\n".join(texts)
        except Exception:
            pass

        return ""

    def _process_chatgpt(self, flow, origin, llm_name="ChatGPT"):
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)

            # ChatGPT Web UI format (POST .../conversation)
            path = urlparse(flow.request.pretty_url).path or ""
            is_webui_send = (
                flow.request.method.upper() == "POST"
                and path.rstrip("/").endswith("/conversation")
                and "messages" in body
            )
            if is_webui_send:
                try:
                    messages = body.get("messages", [])
                    user_msgs = [
                        m
                        for m in messages
                        if m.get("author", {}).get("role") == "user"
                        or m.get("role") == "user"
                    ]
                    if user_msgs:
                        content = user_msgs[-1].get("content", {})
                        if isinstance(content, dict) and content.get("content_type") in ("text", "multimodal_text"):
                            parts = content.get("parts", [])
                            text_parts = [p for p in parts if isinstance(p, str)]
                            attachments = self._extract_attachments_from_chatgpt_parts(parts)
                            prompt_text = " ".join(text_parts) if text_parts else ""
                            # Always log non-string parts (file/image references) so
                            # we can see the actual attachment format in the next test.
                            non_text_parts = [p for p in parts if not isinstance(p, str)]
                            if non_text_parts:
                                att_log = os.path.join(_LOG_DIR, "chatgpt_parts.log")
                                with open(att_log, "a", encoding="utf-8", errors="replace") as _pf:
                                    _pf.write(
                                        f"\n--- {datetime.now().isoformat()} "
                                        f"content_type={content.get('content_type')} ---\n"
                                    )
                                    _pf.write(f"non_text_parts: {json.dumps(non_text_parts[:5])}\n")
                                    _pf.write(f"detected_attachments: {json.dumps(attachments)}\n")
                            if prompt_text or attachments:
                                meta = {
                                    "api_type": "chatgpt_web",
                                    "format": "new",
                                    "parent_message_id": body.get("parent_message_id"),
                                    "messages_count": len(messages),
                                }
                                self._record(
                                    prompt_text=prompt_text,
                                    llm_name="ChatGPT",
                                    model_name=body.get("model", "ChatGPT"),
                                    origin=origin,
                                    url=flow.request.url,
                                    conversation_id=body.get("conversation_id"),
                                    metadata=meta,
                                    flow=flow,
                                    attachments=attachments or None,
                                )
                                return
                except Exception as e:
                    logger.error("Error processing ChatGPT Web format: %s", e)

            # Standard chat completions API
            if "messages" in body:
                user_msgs = [m for m in body["messages"] if m.get("role") == "user"]
                if user_msgs:
                    prompt_text: Any = user_msgs[-1].get("content", "")
                    attachments = None
                    if isinstance(prompt_text, list):
                        attachments = self._extract_attachments_from_content(prompt_text) or None
                        prompt_text = " ".join(
                            item.get("text", "")
                            for item in prompt_text
                            if isinstance(item, dict) and item.get("type") == "text"
                        )
                    self._record(
                        prompt_text=str(prompt_text),
                        llm_name="ChatGPT",
                        model_name=body.get("model", "gpt-unknown"),
                        origin=origin,
                        url=flow.request.url,
                        conversation_id=body.get("conversation_id"),
                        metadata={
                            "api_type": "chat_completions",
                            "temperature": body.get("temperature"),
                            "max_tokens": body.get("max_tokens"),
                            "messages_count": len(body["messages"]),
                        },
                        flow=flow,
                        attachments=attachments,
                    )

            elif "prompt" in body:
                self._record(
                    prompt_text=body["prompt"],
                    llm_name="ChatGPT",
                    model_name=body.get("model", "completions-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    metadata={"api_type": "completions"},
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing ChatGPT request: %s", e)

    def _process_claude(self, flow, origin, llm_name="Claude"):
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)

            if _DEBUG_REQUESTS:
                req_dir = os.path.join(_LOG_DIR, "raw_captures")
                os.makedirs(req_dir, exist_ok=True)
                req_path = os.path.join(req_dir, f"claude_req_{int(time.time()*1000)}.json")
                with open(req_path, "w", encoding="utf-8", errors="replace") as _f:
                    _f.write(f"url: {flow.request.url}\n\n")
                    # Dump body but truncate any base64 blobs to avoid huge files
                    safe = json.loads(text)
                    for key in ("attachments", "files"):
                        if key in safe and isinstance(safe[key], list):
                            for item in safe[key]:
                                if isinstance(item, dict) and "extracted_content" in item:
                                    item["extracted_content"] = f"<{len(item['extracted_content'])} chars truncated>"
                    _f.write(json.dumps(safe, indent=2)[:8192])
                logger.info("DEBUG_REQUESTS: wrote Claude request body to %s", req_path)

            if "prompt" in body:
                # Claude web UI /completion endpoint: extract parent_message_uuid and
                # attachments/files fields that the legacy path was not capturing.
                claude_attachments = self._extract_claude_web_attachments(body)
                # Always log attachment field shapes when present (no debug flag needed)
                raw_atts = body.get("attachments", [])
                raw_files = body.get("files", [])
                if raw_atts or raw_files:
                    att_log = os.path.join(_LOG_DIR, "claude_attachments.log")
                    with open(att_log, "a", encoding="utf-8", errors="replace") as _af:
                        _af.write(f"\n--- {datetime.now().isoformat()} url={flow.request.url} ---\n")
                        # Truncate extracted_content to keep file small
                        safe_a = [
                            {k: (f"<{len(v)} chars>" if k == "extracted_content" and isinstance(v, str) else v)
                             for k, v in a.items()} if isinstance(a, dict) else a
                            for a in raw_atts
                        ]
                        _af.write(f"attachments({len(raw_atts)}): {json.dumps(safe_a)}\n")
                        _af.write(f"files({len(raw_files)}): {json.dumps(raw_files[:5])}\n")
                        _af.write(f"detected_attachments: {json.dumps(claude_attachments)}\n")
                self._record(
                    prompt_text=body["prompt"],
                    llm_name="Claude",
                    model_name=body.get("model", "claude-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    metadata={
                        "api_type": "complete",
                        "parent_message_id": body.get("parent_message_uuid") or body.get("parent_message_id"),
                    },
                    flow=flow,
                    attachments=claude_attachments or None,
                )
            elif "content" in body or "messages" in body:
                messages = body.get("messages", [])
                attachments = None
                if not messages and "content" in body:
                    prompt_text: Any = body["content"]
                    if isinstance(prompt_text, list):
                        attachments = self._extract_attachments_from_content(prompt_text) or None
                        prompt_text = " ".join(
                            item.get("text", "")
                            for item in prompt_text
                            if isinstance(item, dict) and item.get("type") == "text"
                        )
                else:
                    user_msgs = [m for m in messages if m.get("role") == "user"]
                    if not user_msgs:
                        return
                    prompt_text = user_msgs[-1].get("content", "")
                    if isinstance(prompt_text, list):
                        attachments = self._extract_attachments_from_content(prompt_text) or None
                        prompt_text = " ".join(
                            item.get("text", "")
                            for item in prompt_text
                            if isinstance(item, dict) and item.get("type") == "text"
                        )

                self._record(
                    prompt_text=str(prompt_text),
                    llm_name="Claude",
                    model_name=body.get("model", "claude-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    conversation_id=body.get("conversation_id"),
                    metadata={
                        "api_type": "messages",
                        "messages_count": len(messages) or 1,
                        "parent_message_id": body.get("parent_message_uuid") or body.get("parent_message_id"),
                    },
                    flow=flow,
                    attachments=attachments,
                )
        except Exception as e:
            logger.error("Error processing Claude request: %s", e)

    def _process_gemini(self, flow, origin, llm_name="Gemini"):
        """Gemini API (generativelanguage.google... / generateContent)."""
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)

            if "contents" not in body:
                return
            prompt_text = ""
            attachments = []
            for content in body["contents"]:
                parts = content.get("parts", [])
                for part in parts:
                    if "text" in part:
                        prompt_text += part["text"] + " "
                attachments.extend(self._extract_attachments_from_gemini_parts(parts))
            prompt_text = prompt_text.strip()
            if prompt_text or attachments:
                self._record(
                    prompt_text=prompt_text,
                    llm_name="Gemini",
                    model_name=body.get("model", "gemini-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    metadata={"messages_count": len(body.get("contents", []))},
                    flow=flow,
                    attachments=attachments or None,
                )
        except Exception as e:
            logger.error("Error processing Gemini request: %s", e)

    @staticmethod
    def _choose_best_prompt_candidate(strings: list[str], rpcids: list[str] | None = None) -> str:
        def looks_like_internal_token(s: str) -> bool:
            # e.g. ESY5D, PCck7e, aPya6c
            if re.fullmatch(r"[A-Z0-9]{4,10}", s):
                return True
            if re.fullmatch(r"[A-Za-z0-9]{5,10}", s) and "." not in s and " " not in s:
                # short-ish opaque token
                return True
            return False

        def score(s: str) -> tuple[int, int, int]:
            # higher is better
            letters = sum(ch.isalpha() for ch in s)
            digits = sum(ch.isdigit() for ch in s)
            spaces = sum(ch.isspace() for ch in s)

            has_space = 1 if spaces else 0
            has_punct = 1 if any(ch in ".,;:!?()[]{}<>/\\|+-=*~`'\"" for ch in s) else 0
            has_lower = 1 if any(ch.islower() for ch in s) else 0
            token_penalty = 1 if looks_like_internal_token(s) else 0

            # Prefer: human text (spaces/punct), lowercase, more letters; penalize digits + token-like
            return (
                10 * has_space + 3 * has_punct + 2 * has_lower - 20 * token_penalty - digits,
                letters,
                len(s),
            )

        candidates: list[str] = []
        rpcids_set = set(rpcids) if rpcids else set()

        for st in strings:
            if not isinstance(st, str):
                continue
            st = st.strip()
            if not st:
                continue
            
            if st in rpcids_set:
                continue

            # Skip known internal/protocol tokens
            if st.startswith("r_"):
                continue
            if "bard_" in st or "BardChatUi" in st or "boq_" in st:
                continue
            if re.match(r"^https?://", st):
                continue
            if st.startswith("!") and len(st) > 20:
                continue
            if st in ("generic", "en", "en-US", "auto", "chat"):
                continue

            # Skip opaque tokens: long strings with no spaces and only alnum/dash/underscore
            if re.fullmatch(r"[A-Za-z0-9_\-]{20,}", st):
                continue
            if re.fullmatch(r"[0-9a-fA-F]{16,}", st):
                continue
            if len(st) >= 16 and re.fullmatch(r"[A-Za-z0-9_\-]{16,}", st):
                continue
            # Base64 blobs: no spaces, long, contains /+= chars
            if len(st) > 20 and " " not in st and re.search(r"[+/=]", st):
                continue

            # Skip known Gemini internal garbage values seen in practice
            _GEMINI_GARBAGE = {
                "null", "NULL", "none", "NONE", "true", "TRUE", "false", "FALSE",
                "undefined", "UNDEFINED", "show_debug_info", "generic",
                "bard_activity_enabled",
            }
            if st in _GEMINI_GARBAGE:
                continue
            # Pure numeric / symbol strings
            if re.fullmatch(r"[0-9\.\-\s\[\]\(\),:]+", st):
                continue
            # Internal dotted identifiers like person.photo, image_generation_soft:1
            if re.match(r"^[a-z_]+[\.:][a-z_0-9]+$", st):
                continue
            # image_generation* internal keys
            if re.match(r"^image_generation", st, re.IGNORECASE):
                continue

            candidates.append(st)

        if not candidates:
            return ""

        # Pick the "most human" string, not the first one
        return max(candidates, key=score)

    @staticmethod
    def _extract_gemini_conversation_id(flow) -> str | None:
        """Try to find a Gemini conversation ID from available request context.

        Checks (in priority order):
        1. `source-path` URL query param — e.g. ?source-path=/app/ac73b99a0aa3dbe3
        2. Referer header path — e.g. Referer: https://gemini.google.com/app/ac73b99a0aa3dbe3
        3. Request URL path itself (rare but possible for some endpoints)
        Returns None if no conversation-specific ID is found.
        """
        _HEX_ID = re.compile(r"/app/([0-9a-f]{8,})", re.IGNORECASE)

        # 1. source-path query param (most reliable — Gemini includes this on batchexecute)
        source_path = flow.request.query.get("source-path", "")
        if source_path:
            m = _HEX_ID.search(source_path)
            if m:
                return m.group(1)

        # 2. Referer header
        referer = (flow.request.headers.get("referer")
                   or flow.request.headers.get("Referer") or "")
        if referer:
            m = _HEX_ID.search(referer)
            if m:
                return m.group(1)

        # 3. Request URL path (fallback)
        m = _HEX_ID.search(flow.request.pretty_url)
        if m:
            return m.group(1)

        return None

    def _process_bard(self, flow, origin, llm_name="Gemini"):
        """
        Gemini Web UI (legacy Bard endpoints):
          - /_/BardChatUi/data/batchexecute    (often returns reqid r_e...)
          - /_/BardChatUi/data/assistant.l...  (often returns the actual model output)
        """
        try:
            url = flow.request.pretty_url
            path = urlparse(url).path or ""
            rpcids = flow.request.query.get("rpcids", "").split(",")
            referer = (flow.request.headers.get("referer")
                       or flow.request.headers.get("Referer") or "")
            source_path = flow.request.query.get("source-path", "")

            _gemini_logger.debug(
                "bard request: path=%s rpcids=%s referer=%r source-path=%r",
                path, rpcids, referer, source_path,
            )

            # If this is the follow-up call carrying the reqid, DON'T record a prompt.
            # Instead, attach the upcoming response to the original prompt id.
            if "assistant.l" in path:
                reqid = ""
                if flow.request.content:
                    raw = flow.request.get_text(strict=False) or ""
                    reqid = self._find_reqid(raw)
                if not reqid:
                    reqid = self._find_reqid(url)
                if reqid and reqid in self._gemini_reqid_to_prompt:
                    prompt_id = self._gemini_reqid_to_prompt.pop(reqid, None)
                    if prompt_id:
                        self._pending_responses[flow.id] = (prompt_id, "Gemini")
                        logger.info(
                            "Gemini assistant.l correlated reqid %s -> prompt %s",
                            reqid, prompt_id,
                        )
                        return
                # Fall through to best-effort capture if correlation fails

            text = flow.request.get_text(strict=False)
            if not text:
                return

            prompt_text = ""

            # Gemini's URL-encoded RPC format
            if "application/x-www-form-urlencoded" in flow.request.headers.get("Content-Type", ""):
                form_data = flow.request.urlencoded_form
                payload = ""
                for field in ("f.req", "prompt", "message", "q"):
                    if field in form_data:
                        payload = form_data[field]
                        break

                if payload:
                    harvested: list[str] = []
                    try:
                        outer = json.loads(payload)
                        self._collect_leaf_strings(outer, harvested)
                    except Exception:
                        matches = re.findall(r'"((?:[^"\\]|\\.)*)"', payload)
                        for m in matches:
                            try:
                                harvested.append(json.loads(f'"{m}"'))
                            except Exception:
                                harvested.append(m)

                    prompt_text = self._choose_best_prompt_candidate(harvested, rpcids)

                    _gemini_logger.debug(
                        "bard harvested %d strings, chose prompt=%r",
                        len(harvested), prompt_text,
                    )
            else:
                harvested2: list[str] = []
                try:
                    outer2 = json.loads(text)
                    self._collect_leaf_strings(outer2, harvested2)
                except Exception:
                    matches = re.findall(r'"((?:[^"\\]|\\.)*)"', text)
                    for m in matches:
                        try:
                            harvested2.append(json.loads(f'"{m}"'))
                        except Exception:
                            harvested2.append(m)

                prompt_text = self._choose_best_prompt_candidate(harvested2, rpcids)

            # Quality gate: reject single-word / very short candidates that slipped
            # through (e.g. "1", "NULL", "hi" is fine but needs at least 2 chars of
            # actual natural-language content — "hi" passes, "1" or "NULL" don't).
            if prompt_text:
                pt = prompt_text.strip()
                if len(pt) < 2:
                    logger.debug("Gemini bard: rejecting too-short candidate: %r", pt)
                    prompt_text = ""
                elif pt.upper() in ("NULL", "NONE", "TRUE", "FALSE", "UNDEFINED"):
                    logger.debug("Gemini bard: rejecting null-like candidate: %r", pt)
                    prompt_text = ""
                # Reject if it looks like an internal key (underscored, no spaces, has colon/dot)
                elif re.match(r"^[a-z_]+[:\.]", pt) and " " not in pt:
                    logger.debug("Gemini bard: rejecting internal-key candidate: %r", pt)
                    prompt_text = ""

            if _DEBUG_REQUESTS:
                req_dir = os.path.join(_LOG_DIR, "raw_captures")
                os.makedirs(req_dir, exist_ok=True)
                req_path = os.path.join(req_dir, f"gemini_bard_req_{int(time.time()*1000)}.txt")
                with open(req_path, "w", encoding="utf-8", errors="replace") as _f:
                    _f.write(f"url: {flow.request.url}\nprompt_text: {repr(prompt_text)}\n\n")
                    _f.write((text or "")[:4096])
                logger.info("DEBUG_REQUESTS: wrote Gemini bard request body to %s", req_path)

            if prompt_text:
                # Try to get a real conversation ID instead of the generic fallback
                conv_id = self._extract_gemini_conversation_id(flow)
                _gemini_logger.info(
                    "bard recording prompt (len=%d) conv_id=%s source-path=%r referer=%r",
                    len(prompt_text), conv_id, source_path, referer,
                )
                self._record(
                    prompt_text=prompt_text,
                    llm_name="Gemini",
                    model_name="gemini-web",
                    origin=origin,
                    url=flow.request.url,
                    conversation_id=conv_id,  # None → falls back to _extract_conversation_id_from_flow
                    metadata={"api_type": "bard_web", "rpcids": ",".join(rpcids)},
                    flow=flow,
                )

        except Exception as e:
            logger.error("Error processing Gemini request: %s", e)

    def _process_perplexity(self, flow, origin, llm_name="Perplexity"):
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)
            prompt_text = None

            for key in ("text", "prompt", "query"):
                if key in body:
                    prompt_text = body[key]
                    break

            if prompt_text is None and ("message" in body or "messages" in body):
                messages = body.get("messages", [body["message"]] if "message" in body else [])
                user_msgs = [m for m in messages if m.get("role") == "user"]
                if user_msgs:
                    prompt_text = user_msgs[-1].get("content", "")

            if prompt_text:
                mc = len(body.get("messages", body.get("message", [])))
                self._record(
                    prompt_text=prompt_text,
                    llm_name="Perplexity",
                    model_name=body.get("model", "perplexity-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    metadata={"messages_count": mc} if mc else None,
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing Perplexity request: %s", e)

    def _process_openai_compat(self, flow, origin, llm_name="Unknown"):
        """Shared request processor for OpenAI-compatible providers."""
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)
            prompt_text = self._extract_openai_messages(body)
            attachments = self._extract_openai_attachments(body) or None
            if not prompt_text:
                prompt_text = body.get("prompt", "")
            if prompt_text or attachments:
                self._record(
                    prompt_text=prompt_text,
                    llm_name=llm_name,
                    model_name=body.get("model", f"{llm_name.lower()}-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    conversation_id=body.get("conversation_id"),
                    metadata={
                        "api_type": "openai_compat",
                        "temperature": body.get("temperature"),
                        "max_tokens": body.get("max_tokens"),
                        "messages_count": len(body.get("messages", [])),
                    },
                    flow=flow,
                    attachments=attachments,
                )
        except Exception as e:
            logger.error("Error processing %s request: %s", llm_name, e)

    @staticmethod
    def _extract_openai_messages(body: dict) -> str:
        """Extract the last user message from an OpenAI-style messages[] array."""
        messages = body.get("messages", [])
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if not user_msgs:
            return ""
        content = user_msgs[-1].get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
        return str(content) if content else ""

    @staticmethod
    def _extract_attachments_from_content(content):
        """Extract attachment metadata from an OpenAI/Claude-style content array."""
        if not isinstance(content, list):
            return []
        attachments = []
        for item in content:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type", "")
            if item_type == "image_url":
                url = item.get("image_url", {}).get("url", "")
                source = "base64" if url.startswith("data:") else "url"
                media_type = None
                if url.startswith("data:"):
                    media_type = url.split(";")[0].replace("data:", "")
                attachments.append({"type": "image", "media_type": media_type, "source": source})
            elif item_type == "image":
                src = item.get("source", {})
                attachments.append({
                    "type": "image",
                    "media_type": src.get("media_type"),
                    "source": src.get("type", "unknown"),
                })
            elif item_type == "document":
                src = item.get("source", {})
                attachments.append({
                    "type": "document",
                    "media_type": src.get("media_type"),
                    "source": src.get("type", "unknown"),
                    "name": item.get("name"),
                })
        return attachments

    @staticmethod
    def _extract_attachments_from_chatgpt_parts(parts):
        """Extract attachment metadata from ChatGPT Web UI multimodal parts."""
        attachments = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            ct = part.get("content_type", "")
            if ct == "image_asset_pointer":
                attachments.append({
                    "type": "image",
                    "media_type": None,
                    "source": "chatgpt_asset",
                    "asset_id": part.get("asset_pointer", ""),
                })
            elif "file" in ct or "document" in ct:
                attachments.append({
                    "type": "document",
                    "media_type": None,
                    "source": "chatgpt_asset",
                    "name": part.get("name") or part.get("asset_pointer", ""),
                })
        return attachments

    @staticmethod
    def _extract_attachments_from_gemini_parts(parts):
        """Extract attachment metadata from Gemini API parts."""
        attachments = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            if "inline_data" in part:
                data = part["inline_data"]
                mime = data.get("mime_type", "")
                attachments.append({
                    "type": "image" if mime.startswith("image/") else "document",
                    "media_type": mime or None,
                    "source": "inline_base64",
                })
            elif "file_data" in part:
                data = part["file_data"]
                attachments.append({
                    "type": "document",
                    "media_type": data.get("mime_type"),
                    "source": "file_uri",
                    "uri": data.get("file_uri", ""),
                })
        return attachments

    @staticmethod
    def _extract_claude_web_attachments(body):
        """Extract attachments from a Claude web UI /completion request body.

        Claude web UI sends a top-level 'attachments' list (and sometimes 'files')
        with objects like: {file_name, file_type, file_size, extracted_content, id}.
        """
        result = []
        for att in body.get("attachments", []):
            if not isinstance(att, dict):
                continue
            file_type = att.get("file_type", "")
            result.append({
                "type": "image" if file_type.startswith("image/") else "document",
                "media_type": file_type or None,
                "source": "claude_web",
                "name": att.get("file_name"),
                "size": att.get("file_size"),
            })
        for f in body.get("files", []):
            if not isinstance(f, dict):
                continue
            file_type = f.get("file_type", "") or f.get("mime_type", "")
            name = f.get("file_name") or f.get("name")
            if name or file_type:
                result.append({
                    "type": "image" if file_type.startswith("image/") else "document",
                    "media_type": file_type or None,
                    "source": "claude_web",
                    "name": name,
                })
        return result

    @staticmethod
    def _extract_openai_attachments(body):
        """Extract attachment metadata from the last user message in an OpenAI-style body."""
        messages = body.get("messages", [])
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if not user_msgs:
            return []
        content = user_msgs[-1].get("content", "")
        if isinstance(content, list):
            return LLMPromptRecorder._extract_attachments_from_content(content)
        return []

    @staticmethod
    def _extract_conversation_id_from_flow(flow):
        """Extract a stable conversation ID from the Referer header URL.

        Most LLM web UIs include the conversation page URL as the Referer
        header on API requests.  This gives us a stable grouping key even
        when the request body does not contain a conversation_id field.
        """
        if flow is None:
            return None
        referer = flow.request.headers.get("referer") or flow.request.headers.get("Referer")
        if not referer:
            return None
        try:
            parsed = urlparse(referer)
            path = parsed.path or ""
            # ChatGPT: /c/{uuid}
            m = re.search(r"/c/([0-9a-f-]{8,})", path, re.IGNORECASE)
            if m:
                return m.group(1)
            # Claude: /chat/{uuid}
            m = re.search(r"/chat/([0-9a-f-]{8,})", path, re.IGNORECASE)
            if m:
                return m.group(1)
            # Gemini: /app/{id}
            m = re.search(r"/app/([0-9a-f]{8,})", path, re.IGNORECASE)
            if m:
                return m.group(1)
            # Gemini fallback: normalize bare /app or / to a consistent key
            if "gemini.google" in (parsed.netloc or ""):
                return "gemini.google.com/app"
            # Perplexity: /search/{slug}
            m = re.search(r"/search/([A-Za-z0-9_.-]{8,})", path)
            if m:
                return m.group(1)
            # Generic: last path segment if it looks like an ID
            segments = [s for s in path.split("/") if s]
            if segments:
                last = segments[-1]
                if len(last) >= 8 and re.fullmatch(r"[A-Za-z0-9_-]+", last):
                    return last
            # Fallback: use full referer origin+path as a stable grouping key
            return parsed.netloc + path
        except Exception:
            return None

    def _process_meta_ai(self, flow, origin, llm_name="Meta AI"):
        """Request processor for Meta AI (GraphQL-like POST with variables.message)."""
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)
            # GraphQL format: variables.message or variables.query
            variables = body.get("variables", {})
            prompt_text = (
                variables.get("message")
                or variables.get("query")
                or body.get("message")
                or body.get("query")
                or self._extract_openai_messages(body)
            )
            if prompt_text:
                self._record(
                    prompt_text=prompt_text,
                    llm_name="Meta AI",
                    model_name=body.get("model", "meta-ai"),
                    origin=origin,
                    url=flow.request.url,
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing Meta AI request: %s", e)

    def _process_copilot(self, flow, origin, llm_name="Copilot"):
        """Request processor for Microsoft Copilot (arguments[0].messages[-1].text)."""
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)
            # Copilot throttled format: arguments[0].messages[-1].text
            args = body.get("arguments", [{}])
            messages = args[0].get("messages", []) if args else []
            user_msgs = [m for m in messages if m.get("author") == "user" or m.get("role") == "user"]
            prompt_text = ""
            if user_msgs:
                prompt_text = user_msgs[-1].get("text") or user_msgs[-1].get("content", "")
            if not prompt_text:
                prompt_text = self._extract_openai_messages(body)
            if prompt_text:
                self._record(
                    prompt_text=prompt_text,
                    llm_name="Copilot",
                    model_name="copilot",
                    origin=origin,
                    url=flow.request.url,
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing Copilot request: %s", e)

    def _process_generic(self, flow, origin, llm_name=None):
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)

            if llm_name is None:
                llm_name = "Unknown LLM"
                for domain, name in _DOMAIN_NAMES.items():
                    if domain in origin:
                        llm_name = name
                        break

            prompt_text = None
            if "prompt" in body:
                prompt_text = body["prompt"]
            elif "messages" in body:
                user_msgs = [m for m in body["messages"] if m.get("role") == "user"]
                if user_msgs:
                    prompt_text = user_msgs[-1].get("content", "")
            elif "inputs" in body:
                prompt_text = body["inputs"]
            elif "query" in body:
                prompt_text = body["query"]

            if prompt_text:
                self._record(
                    prompt_text=prompt_text,
                    llm_name=llm_name,
                    model_name=body.get("model", "unknown"),
                    origin=origin,
                    url=flow.request.url,
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing generic LLM request: %s", e)

    def _record(
        self,
        prompt_text,
        llm_name,
        origin,
        url,
        model_name=None,
        conversation_id=None,
        metadata=None,
        flow=None,
        attachments=None,
    ):
        if attachments:
            if metadata is None:
                metadata = {}
            metadata["attachments"] = attachments
        prompt_id = self.db.add_prompt(
            prompt_text=prompt_text,
            llm_name=llm_name,
            source="Proxy Recorder",
            model_name=model_name,
            description=f"{llm_name} prompt via {origin}",
            url=url,
            conversation_id=conversation_id or self._extract_conversation_id_from_flow(flow) or f"{llm_name.lower()}-{(model_name or 'unknown').lower()}-api",
            metadata=metadata,
            associated_files=self.active_files,
        )
        self._latest_chatgpt_prompt_id = prompt_id
        logger.info("Recorded %s prompt: %s", llm_name, prompt_id)
        # Track flow for response pairing — store llm_name so the response parser can use format-specific extraction.
        if flow is not None:
            self._pending_responses[flow.id] = (prompt_id, llm_name)

    def set_active_files(self, files):
        self.active_files = files
        logger.info("Set %d active files for auto-association", len(files))

    def clear_active_files(self):
        self.active_files = []
        logger.info("Cleared active files")


_CHATGPT_PATTERNS = [
    # OpenAI API
    r"api\.openai\.com/v1/chat/completions(?:\?.*)?$",
    r"api\.openai\.com/v1/engines/[^/]+/completions(?:\?.*)?$",
    r"api\.openai\.com/v1/completions(?:\?.*)?$",

    # ChatGPT Web UI (send endpoint; anchored so it won't match /prepare)
    r"chat\.openai\.com/backend-api/f/conversation/?(?:\?.*)?$",
    r"chatgpt\.com/backend-api/f/conversation/?(?:\?.*)?$",
    r"chatgpt\.com/backend-api/f/conversation(?!/)",  # allow query params but not extra path segments

    # (Optional) older/alternate domains/paths, also anchored
    r"chat\.openai\.com/backend-api/conversation/?(?:\?.*)?$",
    r"chatgpt\.com/backend-api/conversation/?(?:\?.*)?$",
]

_CLAUDE_PATTERNS = [
    r"api\.anthropic\.com/v1/messages",
    r"api\.anthropic\.com/v1/complete",
    r"claude\.ai/api/.*?/messages",
    r"claude\.ai/api/.*?/completion",
    r"claude\.ai/api/append_message",
]

_GEMINI_PATTERNS = [
    r"generativelanguage\.googleapis\.com",
    r"gemini\.google\.com/api",
    r"generativeai\.google\.com/api",
    r"generativeai\.googleapis\.com",
]

_BARD_PATTERNS = [
    r"bard\.google\.com/api",
    r"bard\.google\.com/_/BardChatUi/data",
    r"gemini\.google\.com/_/BardChatUi/data",
    r"gemini\.google\.com/api/client/",  # newer Gemini web UI endpoint
]

_PERPLEXITY_PATTERNS = [
    r"api\.perplexity\.ai",
    r"perplexity\.ai/api",
]

_GENERIC_PATTERNS = [
    r"api\.mistral\.ai",
    r"api\.cohere\.ai",
    r"api\.together\.xyz",
    r"api\.groq\.com",
    r"api\.deepinfra\.com",
]

_GROK_PATTERNS = [
    r"api\.x\.ai/v1/chat/completions",
    r"api\.x\.ai/v1/completions",
    r"grok\.com/rest/app-chat/conversations",
]

_DEEPSEEK_PATTERNS = [
    r"api\.deepseek\.com/v1/chat/completions",
    r"api\.deepseek\.com/v1/completions",
    r"chat\.deepseek\.com/api/",
]

_OPENROUTER_PATTERNS = [
    r"openrouter\.ai/api/v1/chat/completions",
    r"openrouter\.ai/api/v1/completions",
]

_LECHAT_PATTERNS = [
    r"chat\.mistral\.ai/api/chat",
]

_HUGGINGCHAT_PATTERNS = [
    r"huggingface\.co/chat/conversation",
]

_META_AI_PATTERNS = [
    r"meta\.ai/api",
    r"www\.meta\.ai/api",
]

_COPILOT_PATTERNS = [
    r"copilot\.microsoft\.com/c/api",
    r"copilot\.microsoft\.com/api",
    r"sydney\.bing\.com/sydney",
]

_YOUCOM_PATTERNS = [
    r"you\.com/api/streamingSearch",
    r"you\.com/api/chat",
]

_PHIND_PATTERNS = [
    r"phind\.com/api",
    r"www\.phind\.com/api",
]

_DOMAIN_NAMES = {
    "mistral.ai": "Mistral AI",
    "cohere.ai": "Cohere",
    "together.xyz": "Together AI",
    "groq.com": "Groq",
    "deepinfra.com": "DeepInfra",
    "x.ai": "Grok",
    "grok.com": "Grok",
    "deepseek.com": "DeepSeek",
    "openrouter.ai": "OpenRouter",
    "chat.mistral.ai": "Le Chat",
    "huggingface.co": "HuggingChat",
    "meta.ai": "Meta AI",
    "copilot.microsoft.com": "Copilot",
    "sydney.bing.com": "Copilot",
    "you.com": "You.com",
    "phind.com": "Phind",
}

# Table-driven request dispatch: (patterns, method_name, llm_name)
# Order matters — more specific patterns first.
# llm_name=None means _process_generic will do domain lookup.
_REQUEST_DISPATCH = [
    (_CHATGPT_PATTERNS, "_process_chatgpt", "ChatGPT"),
    (_CLAUDE_PATTERNS, "_process_claude", "Claude"),
    (_GEMINI_PATTERNS, "_process_gemini", "Gemini"),
    (_BARD_PATTERNS, "_process_bard", "Gemini"),
    (_PERPLEXITY_PATTERNS, "_process_perplexity", "Perplexity"),
    (_GROK_PATTERNS, "_process_openai_compat", "Grok"),
    (_DEEPSEEK_PATTERNS, "_process_openai_compat", "DeepSeek"),
    (_OPENROUTER_PATTERNS, "_process_openai_compat", "OpenRouter"),
    (_LECHAT_PATTERNS, "_process_openai_compat", "Le Chat"),
    (_HUGGINGCHAT_PATTERNS, "_process_openai_compat", "HuggingChat"),
    (_META_AI_PATTERNS, "_process_meta_ai", "Meta AI"),
    (_COPILOT_PATTERNS, "_process_copilot", "Copilot"),
    (_YOUCOM_PATTERNS, "_process_generic", "You.com"),
    (_PHIND_PATTERNS, "_process_generic", "Phind"),
    (_GENERIC_PATTERNS, "_process_generic", None),
]

# Response parser routing: llm_name -> parser method.
# Missing keys fall through to _parse_generic_response.
_RESPONSE_PARSER = {
    "ChatGPT": "_parse_chatgpt_response",
    "Claude": "_parse_claude_response",
    "Gemini": "_parse_gemini_response",
    "DeepSeek": "_parse_deepseek_response",
    # Dedicated parsers for providers with non-standard streaming formats
    "Perplexity": "_parse_perplexity_response",
    "Grok": "_parse_grok_response",
    "HuggingChat": "_parse_huggingchat_response",
    "Meta AI": "_parse_meta_ai_response",
    "Copilot": "_parse_copilot_response",
    "You.com": "_parse_youcom_response",
    "Phind": "_parse_phind_response",
    # OpenAI-compatible providers (standard SSE delta format)
    "OpenRouter": "_parse_chatgpt_response",
    "Le Chat": "_parse_chatgpt_response",
}

recorder = LLMPromptRecorder()
addons = [recorder]


def set_active_files(files):
    recorder.set_active_files(files)


def clear_active_files():
    recorder.clear_active_files()

@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\recorders\proxy_runner.py

#!/usr/bin/env python3
"""Programmatic mitmproxy entry point for LLM Buddy.

Replaces the ``mitmdump -s proxy_recorder.py`` pattern so the proxy
can run inside a PyInstaller-frozen .exe (where addon paths and
external executables don't work).

Usage:
    python -m llm_buddy.recorders.proxy_runner [--port 8080]
    llm-buddy-proxy.exe --port 8080          (frozen)
"""

import argparse
import asyncio
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Buddy Proxy Recorder")
    parser.add_argument("--port", type=int, default=8080,
                        help="Proxy listen port (default: 8080)")
    args = parser.parse_args()

    # Import mitmproxy lazily so import errors give a clear message
    try:
        from mitmproxy.options import Options
        from mitmproxy.tools.dump import DumpMaster
    except ImportError:
        print("mitmproxy is not installed. Install with: "
              "pip install mitmproxy", file=sys.stderr)
        sys.exit(1)

    from llm_buddy.recorders.proxy_recorder import LLMPromptRecorder

    async def run_proxy():
        opts = Options(listen_port=args.port, mode=["regular"])
        master = DumpMaster(opts)
        master.addons.add(LLMPromptRecorder())
        try:
            await master.run()
        except KeyboardInterrupt:
            master.shutdown()

    asyncio.run(run_proxy())


if __name__ == "__main__":
    main()


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\recorders\__init__.py



@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\scripts\configure_claude.py

"""Configure Claude Desktop to use LLM Buddy's MCP recorder."""

import os
import sys
import json
import shutil
import platform
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("configure")


def find_claude_config():
    """Find Claude Desktop configuration file in common locations."""
    system = platform.system()
    possible_paths = []

    if system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            possible_paths.append(
                os.path.join(appdata, "Claude", "claude_desktop_config.json"))
            possible_paths.append(
                os.path.join(appdata, "Claude", "config.json"))
        localappdata = os.getenv("LOCALAPPDATA")
        if localappdata:
            possible_paths.append(
                os.path.join(localappdata, "Claude", "claude_desktop_config.json"))
            possible_paths.append(
                os.path.join(localappdata, "Claude", "config.json"))

    elif system == "Darwin":
        home = os.path.expanduser("~")
        possible_paths.append(os.path.join(
            home, "Library", "Application Support",
            "Claude", "claude_desktop_config.json"))
        possible_paths.append(os.path.join(
            home, "Library", "Application Support",
            "Claude", "config.json"))

    elif system == "Linux":
        home = os.path.expanduser("~")
        possible_paths.append(os.path.join(
            home, ".config", "Claude", "claude_desktop_config.json"))
        possible_paths.append(os.path.join(
            home, ".config", "Claude", "config.json"))

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def update_claude_config():
    """Update Claude Desktop configuration to use the MCP recorder."""
    logger.info("Updating Claude Desktop configuration")

    config_file = find_claude_config()
    if not config_file:
        logger.warning("Could not find Claude Desktop configuration file.")
        config_file = input(
            "Please enter the path to the Claude Desktop config file: ").strip()
        if not config_file or not os.path.exists(config_file):
            logger.error(f"File not found: {config_file}")
            return

    logger.info(f"Found config: {config_file}")

    # Create backup
    backup_file = f"{config_file}.backup"
    shutil.copy2(config_file, backup_file)
    logger.info(f"Backup created: {backup_file}")

    # Load
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return

    # Locate the MCP recorder file without importing it (which would
    # fail if the 'mcp' package isn't installed).
    import importlib.util
    spec = importlib.util.find_spec("llm_buddy.recorders.mcp_recorder")
    if spec is None or spec.origin is None:
        logger.error("Could not locate mcp_recorder.py in the package.")
        return
    mcp_recorder_path = spec.origin

    # Update
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    python_cmd = "python" if platform.system() == "Windows" else "python3"
    config["mcpServers"]["prompt-recorder"] = {
        "command": python_cmd,
        "args": [mcp_recorder_path],
    }
    logger.info(f"MCP recorder path: {mcp_recorder_path}")

    # Save
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved successfully.")
        logger.info("Please restart Claude Desktop for changes to take effect.")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        logger.info(f"Restore backup from: {backup_file}")


if __name__ == "__main__":
    update_claude_config()
    print("\nConfiguration update complete. Press Enter to exit...")
    input()


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\scripts\__init__.py



@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\services\analytics_service.py

"""Analytics data computation — no GUI imports.

Extracted from ``gui.mixin_analytics._compute_analytics_data``.
"""

import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Token counting — same logic as the original mixin
try:
    import tiktoken
    _ENC = tiktoken.encoding_for_model("gpt-4")

    def _count_tokens(text: str) -> int:
        return len(_ENC.encode(text)) if text else 0
except Exception:
    _ENC = None

    def _count_tokens(text: str) -> int:  # type: ignore[misc]
        return len(text) // 4 if text else 0


def compute_analytics_data(
    prompts: list,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db=None,
) -> Dict[str, Any]:
    """Aggregate prompt data for the analytics dashboard.

    Parameters
    ----------
    prompts : list
        Iterable of PromptRecord objects (must have ``.timestamp``,
        ``.llm_used``, ``.prompt_text``, and optionally ``.response_text``).
    start_date, end_date : datetime | None
        Optional date-range filter.

    Returns
    -------
    dict
        Keys: prompts_by_date, llm_distribution, tokens_by_date,
        timeline_events, total_prompts, total_tokens, unique_llms,
        active_days, start_date, end_date.
    """
    filtered = list(prompts)
    if start_date:
        filtered = [p for p in filtered if p.timestamp >= start_date]
    if end_date:
        filtered = [p for p in filtered if p.timestamp <= end_date]

    # Prompts per day (bar chart)
    date_counter: Counter = Counter()
    for p in filtered:
        date_counter[p.timestamp.strftime("%Y-%m-%d")] += 1
    sorted_dates = sorted(date_counter.keys())
    prompts_by_date = [(d, date_counter[d]) for d in sorted_dates]

    # LLM distribution (pie chart)
    llm_counter: Counter = Counter()
    for p in filtered:
        llm_counter[p.llm_used] += 1
    llm_distribution = list(llm_counter.most_common())

    # Token usage by day (line chart)
    token_day: Counter = Counter()
    total_tokens = 0
    for p in filtered:
        tok = _count_tokens(p.prompt_text)
        tok += _count_tokens(getattr(p, "response_text", "") or "")
        total_tokens += tok
        token_day[p.timestamp.strftime("%Y-%m-%d")] += tok
    sorted_tok_dates = sorted(token_day.keys())
    tokens_by_date = [(d, token_day[d]) for d in sorted_tok_dates]

    # Activity timeline
    timeline_events: List[Dict[str, Any]] = []
    for p in filtered:
        label = p.description or p.llm_used or "Prompt"
        if len(label) > 50:
            label = label[:47] + "\u2026"
        timeline_events.append({
            "time": p.timestamp,
            "type": "prompt",
            "label": label,
        })

    # eADR notes on the timeline
    try:
        notes = db.get_eadr_notes() if db is not None else []
        for n in notes:
            try:
                ts = datetime.strptime(n.timestamp, "%Y-%m-%d %H:%M:%S")
                if start_date and ts < start_date:
                    continue
                if end_date and ts > end_date:
                    continue
                label = n.note or "Note"
                if len(label) > 50:
                    label = label[:47] + "\u2026"
                timeline_events.append({
                    "time": ts,
                    "type": "note",
                    "label": label,
                })
            except (ValueError, KeyError):
                pass
    except Exception:
        pass

    timeline_events.sort(key=lambda e: e["time"])

    # Summary stats
    unique_dates = set(p.timestamp.date() for p in filtered)
    unique_llms = len(set(p.llm_used for p in filtered))

    return {
        "prompts_by_date": prompts_by_date,
        "llm_distribution": llm_distribution,
        "tokens_by_date": tokens_by_date,
        "timeline_events": timeline_events,
        "total_prompts": len(filtered),
        "total_tokens": total_tokens,
        "unique_llms": unique_llms,
        "active_days": len(unique_dates),
        "start_date": start_date,
        "end_date": end_date,
    }


def parse_date(s: str) -> Optional[datetime]:
    """Parse a ``YYYY-MM-DD`` string into a datetime, or *None*."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None


def fmt_tokens(n: int) -> str:
    """Format a token count with thousand separators."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n:,.0f}"
    return str(n)


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\services\backup_service.py

"""Backup business logic — no GUI imports.

Extracted from ``gui.mixin_backup``.
"""

import fnmatch
import os
from datetime import datetime
from typing import List, Tuple

from llm_buddy.core.tokens import (
    build_combined_text,
    count_tokens,
    count_tokens_in_file,
)
from llm_buddy.paths import get_backup_dir


def create_auto_backup(
    changed_files: List[Tuple[str, int]],
    monitor_files: List[str],
    active_prompt,
    prompt_database,
    output_dir: str = None,
) -> Tuple[bool, str]:
    """Create an auto-backup file.

    Returns ``(success, output_file_path)``.
    """
    if output_dir is None:
        output_dir = get_backup_dir()
    active_prompt_info = ""
    if active_prompt:
        for fp, tc in changed_files:
            if fp not in active_prompt.associated_files:
                active_prompt.associated_files.append(fp)
                active_prompt.file_changes[fp] = tc
        prompt_database.save()
        active_prompt_info = (
            f"\nActive Prompt: "
            f"{active_prompt.description or 'Untitled'} "
            f"({active_prompt.llm_used})")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_changes = sum(c for _, c in changed_files)
    backup_name = (
        f"auto_backup_{ts}_{len(changed_files)}files_"
        f"{total_changes}tokens.md")

    files_to_backup = [fp for fp, _ in changed_files]
    for fp in monitor_files:
        if fp not in files_to_backup and os.path.isfile(fp):
            files_to_backup.append(fp)

    header = (
        f"Auto-Backup generated on "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"\nChanged files: {len(changed_files)}, "
        f"Total token changes: {total_changes}"
        f"{active_prompt_info}")
    if active_prompt:
        header += "\n\nPrompt Text:\n" + active_prompt.prompt_text

    combined_text = build_combined_text(
        files_to_backup, header, "End of Auto-Backup")
    total_tokens = count_tokens(combined_text)

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, backup_name)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_text)

    return True, output_file


def build_backup_eadr_note(
    backup_name: str,
    changed_files: List[Tuple[str, int]],
    total_tokens: int,
    active_prompt=None,
) -> str:
    """Build the eADR note text for an auto-backup event."""
    note = (
        f"Auto-Backup Created: {backup_name}\n\n"
        f"Total files: {len(changed_files)}\n"
        f"Total tokens: {total_tokens:,}\n\n")
    if active_prompt:
        note += (
            f"Active Prompt: "
            f"{active_prompt.description or 'Untitled'}\n"
            f"LLM Used: {active_prompt.llm_used}\n\n"
            f"Prompt Text:\n{active_prompt.prompt_text}\n\n")
    note += "Changed files:\n"
    for fp, tc in changed_files:
        note += f"- {fp} ({tc:+,} tokens)\n"
    return note


def collect_force_backup_files(
    monitor_files: List[str],
    monitor_folders: List[str],
    ignored_patterns: List[str],
) -> List[Tuple[str, int]]:
    """Enumerate all monitored files with their token counts.

    Used by the "Force Backup Now" action.
    """
    files_to_backup: List[str] = []
    for fp in monitor_files:
        if os.path.isfile(fp):
            files_to_backup.append(fp)
    for folder in monitor_folders:
        if os.path.isdir(folder):
            for root, _, files in os.walk(folder):
                for fn in files:
                    skip = any(
                        fnmatch.fnmatch(fn, pat) for pat in ignored_patterns)
                    if not skip:
                        files_to_backup.append(os.path.join(root, fn))
    return [(fp, count_tokens_in_file(fp)) for fp in files_to_backup]


def prune_old_auto_backups(backup_dir: str, max_backups: int) -> List[str]:
    """Remove the oldest auto-backups beyond *max_backups*.

    Returns a list of deleted file paths.
    """
    if not os.path.exists(backup_dir):
        return []
    auto_backups = []
    for fn in os.listdir(backup_dir):
        if fn.startswith("auto_backup_") and fn.endswith(".md"):
            fp = os.path.join(backup_dir, fn)
            auto_backups.append((fp, os.path.getmtime(fp)))
    auto_backups.sort(key=lambda x: x[1], reverse=True)

    deleted = []
    for fp, _ in auto_backups[max_backups:]:
        try:
            os.remove(fp)
            deleted.append(fp)
        except Exception:
            pass
    return deleted


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\services\file_service.py

"""File scanning, filtering, and token computation — no GUI imports."""

import os
from typing import List, Tuple

from llm_buddy.core.tokens import count_tokens_in_file


def scan_folder(
    folder: str,
    allowed_extensions: List[str],
    ignored_folders: List[str],
) -> List[str]:
    """Walk *folder* and return paths matching the extension/ignore filters.

    Parameters
    ----------
    folder : str
        Root directory to scan.
    allowed_extensions : list[str]
        Lowercase extensions including the dot (e.g. ``[".py", ".js"]``).
        An empty list means "accept all extensions".
    ignored_folders : list[str]
        Folder names to skip (e.g. ``["node_modules", "__pycache__"]``).

    Returns
    -------
    list[str]
        Absolute file paths found under *folder*.
    """
    found: List[str] = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if allowed_extensions and ext not in allowed_extensions:
                continue
            found.append(os.path.join(root, f))
    return found


def filter_files(
    all_files: List[str],
    allowed_extensions: List[str],
    min_tokens: int,
) -> List[Tuple[str, int]]:
    """Filter *all_files* by extension and minimum token count.

    Returns a list of ``(path, token_count)`` tuples for files that pass.
    """
    result: List[Tuple[str, int]] = []
    for filepath in all_files:
        ext = os.path.splitext(filepath)[1].lower()
        if allowed_extensions and ext not in allowed_extensions:
            continue
        tokens = count_tokens_in_file(filepath)
        if tokens < min_tokens:
            continue
        result.append((filepath, tokens))
    return result


def compute_folder_tokens(
    folder: str,
    allowed_extensions: List[str],
    ignored_folders: List[str],
    min_tokens: int = 0,
) -> int:
    """Return the total token count of qualifying files under *folder*."""
    total = 0
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if allowed_extensions and ext not in allowed_extensions:
                continue
            filepath = os.path.join(root, f)
            tokens = count_tokens_in_file(filepath)
            if tokens < min_tokens:
                continue
            total += tokens
    return total


def parse_extensions(raw: str) -> List[str]:
    """Parse a comma-separated extensions string into a normalised list.

    Example: ``".py, .js , .ts"`` → ``[".py", ".js", ".ts"]``
    """
    return [ext.strip().lower() for ext in raw.split(",") if ext.strip()]


def parse_ignored_folders(raw: str) -> List[str]:
    """Parse a comma-separated ignored-folders string into a list."""
    return [name.strip() for name in raw.split(",") if name.strip()]


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\services\preview_service.py

"""Preview / combine-scripts logic — no GUI imports.

Extracted from ``gui.mixin_preview.combine_scripts`` (the eADR-note
construction part).
"""

import os
from typing import List


def build_combine_eadr_note(
    folders: List[str],
    filtered_files: List[str],
    allowed_extensions: str,
    min_tokens: int,
    ignored_folders: str,
    output_file: str,
    total_tokens: int,
    user_note: str = "",
) -> str:
    """Build the eADR note text for a combine-scripts operation.

    Returns the full note string (caller is responsible for calling
    ``save_eadr_note``).
    """
    if user_note:
        note_text = (
            f"{user_note}\n\n"
            "--- Automatic Script Combination Information ---\n\n"
        )
    else:
        note_text = ""

    filename_only = os.path.basename(output_file)
    note_text += f"Created combined file: '{filename_only}'\n"
    note_text += f"Total tokens: {total_tokens:,}\n\n"

    note_text += f"Folders used ({len(folders)}):\n"
    if folders:
        for folder in folders:
            note_text += f"- {folder}\n"
    else:
        note_text += "- No folders were directly selected\n"

    note_text += f"\nFilter settings:\n"
    note_text += f"- Extensions: {allowed_extensions}\n"
    note_text += f"- Min tokens: {min_tokens}\n"
    note_text += f"- Ignored folders: {ignored_folders}\n"

    note_text += f"\nFiles included ({len(filtered_files)}):\n"
    for f in filtered_files:
        note_text += f"- {f}\n"

    return note_text


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\services\prompt_service.py

"""Prompt business logic — no GUI imports.

Extracted from ``gui.mixin_prompts``.
"""

import os
from datetime import datetime
from typing import List, Optional, Tuple



def infer_source(prompt) -> str:
    """Heuristic to determine a prompt's origin.

    Parameters
    ----------
    prompt : PromptRecord
        Must have ``.description``, ``.llm_used``, and optionally
        ``.source`` attributes.
    """
    if hasattr(prompt, "source") and prompt.source:
        return prompt.source

    desc = (prompt.description or "").lower()
    llm = prompt.llm_used or ""

    if "auto-recorded from claude desktop" in desc:
        return "Claude Desktop"
    if "browser extension" in desc or "captured" in desc:
        return "Browser Extension"
    if "proxy" in desc:
        return "Proxy"
    if llm == "Claude" and any(
        k in desc for k in ("mcp", "auto-recorded", "claude desktop")
    ):
        return "Claude Desktop"
    if any(k in desc for k in ("web", "browser", "via", "claude.ai")):
        return "Browser Extension"
    if "ChatGPT" in llm or "Gemini" in llm or "Perplexity" in llm:
        return "Browser Extension"
    return "Manual"


def export_prompt_history(prompt_database, output_dir: str = "prompts") -> str:
    """Export prompt history to a markdown file.

    Returns the path to the written file.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"prompt_history_{ts}.md")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(
            f"# Prompt History Export\nGenerated: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        sorted_prompts = sorted(
            prompt_database.prompts,
            key=lambda p: p.timestamp, reverse=True)
        for i, prompt in enumerate(sorted_prompts, 1):
            f.write(
                f"## {i}. {prompt.description or 'Untitled Prompt'}\n\n")
            f.write(
                f"- **Date & Time:** "
                f"{prompt.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **LLM Used:** {prompt.llm_used}\n")
            f.write(f"- **ID:** {prompt.id}\n\n")
            f.write("### Prompt Text (Input)\n\n```\n")
            f.write(prompt.prompt_text)
            f.write("\n```\n\n")
            response = getattr(prompt, "response_text", "") or ""
            if response:
                f.write("### Response (Output)\n\n```\n")
                f.write(response)
                f.write("\n```\n\n")
            f.write("### Associated Files\n\n")
            if prompt.associated_files:
                for fp in prompt.associated_files:
                    change = prompt.file_changes.get(fp, "Unknown")
                    f.write(f"- `{fp}` (Token change: {change})\n")
            else:
                f.write("No files associated with this prompt.\n")
            if (hasattr(prompt, "retroactive_notes")
                    and prompt.retroactive_notes):
                f.write("\n### Retroactive Associations\n\n")
                for rts, nd in prompt.retroactive_notes.items():
                    f.write(
                        f"**{rts}**\n\n"
                        f"- Token Change: {nd['token_change']}\n")
                    f.write(f"- Notes: {nd['notes']}\n- Files:\n")
                    for rf in nd["files"]:
                        f.write(f"  - `{rf}`\n")
            f.write("\n---\n\n")

    return output_file


def perform_retroactive_association(
    prompt_database,
    prompt_index: int,
    selected_files: List[str],
    token_option: str,
    custom_token: int,
    notes: str,
    project: str = "Origin",
) -> Tuple[int, int]:
    """Associate files retroactively with a prompt.

    Returns ``(newly_added, already_associated)`` counts.
    """
    if prompt_index < 0 or prompt_index >= len(prompt_database.prompts):
        raise IndexError("Invalid prompt index")

    prompt = prompt_database.prompts[prompt_index]

    token_map = {
        "Auto": 100,
        "Minor (<50)": 25,
        "Moderate (50-200)": 100,
        "Major (>200)": 300,
        "Custom": custom_token,
    }
    token_change = token_map.get(token_option, 100)

    newly_added = 0
    for fp in selected_files:
        if fp not in prompt.associated_files:
            prompt.associated_files.append(fp)
            prompt.file_changes[fp] = token_change
            newly_added += 1
    prompt_database.save()

    if notes:
        if not hasattr(prompt, "retroactive_notes"):
            prompt.retroactive_notes = {}
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt.retroactive_notes[ts] = {
            "files": selected_files,
            "token_change": token_change,
            "notes": notes,
        }
        prompt_database.save()

        note_text = (
            f"Retroactive Prompt Association\n\n"
            f"Prompt: {prompt.description or 'Untitled'}\n"
            f"Date: {ts}\nFiles associated: {len(selected_files)}\n\n"
            f"User Notes:\n{notes}\n\nFiles:\n")
        for fp in selected_files:
            note_text += f"- {fp}\n"
        prompt_database.add_eadr_note(note_text, project)

    already = len(selected_files) - newly_added
    return newly_added, already


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\services\subprocess_manager.py

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



def is_port_in_use(port: int) -> bool:
    """Return *True* if something is listening on *port*."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except (ConnectionRefusedError, OSError):
        return False



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


@§A_4a26e87a@ C:/LLM Buddy\src\llm_buddy\services\__init__.py

"""Business logic services for LLM Buddy, decoupled from any GUI framework."""


@§A_4a26e87a@ C:/LLM Buddy\tests\test_proxy_parsers.py

"""Tests for proxy_recorder.py response parsers.

The *_parse_* methods are pure text-in/text-out — they do not touch the
database.  We instantiate LLMPromptRecorder via __new__ to skip __init__
(which would open the DB) so tests run with no external dependencies.
"""
import json
import pytest

from llm_buddy.recorders.proxy_recorder import LLMPromptRecorder


@pytest.fixture(scope="module")
def rec():
    """Bare recorder instance — only parser methods available."""
    return LLMPromptRecorder.__new__(LLMPromptRecorder)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse(*objects):
    """Build a fake SSE body from a list of dicts."""
    lines = []
    for obj in objects:
        lines.append(f"data: {json.dumps(obj)}")
    lines.append("data: [DONE]")
    return "\n".join(lines)


def _ndjson(*objects):
    """Build a newline-delimited JSON body."""
    return "\n".join(json.dumps(o) for o in objects)


# ---------------------------------------------------------------------------
# Perplexity
# ---------------------------------------------------------------------------

class TestPerplexityParser:
    def test_openai_sse(self, rec):
        body = _sse(
            {"choices": [{"delta": {"content": "Hello "}}]},
            {"choices": [{"delta": {"content": "world"}}]},
        )
        assert rec._parse_perplexity_response(body, "text/event-stream") == "Hello world"

    def test_ndjson_streaming(self, rec):
        body = _ndjson(
            {"answer": "Partial", "status": "streaming"},
            {"answer": "Partial answer here.", "status": "completed"},
        )
        result = rec._parse_perplexity_response(body, "text/event-stream")
        assert "Partial answer here." in result

    def test_non_streaming_json(self, rec):
        body = json.dumps({"answer": "Final answer."})
        assert rec._parse_perplexity_response(body, "application/json") == "Final answer."

    def test_non_streaming_openai_format(self, rec):
        body = json.dumps({"choices": [{"message": {"content": "OpenAI-compat answer."}}]})
        assert rec._parse_perplexity_response(body, "application/json") == "OpenAI-compat answer."

    def test_empty_returns_empty(self, rec):
        assert rec._parse_perplexity_response("", "text/event-stream") == ""


# ---------------------------------------------------------------------------
# Grok
# ---------------------------------------------------------------------------

class TestGrokParser:
    def test_openai_api_sse(self, rec):
        body = _sse(
            {"choices": [{"delta": {"content": "Grok "}}]},
            {"choices": [{"delta": {"content": "response"}}]},
        )
        assert rec._parse_grok_response(body, "text/event-stream") == "Grok response"

    def test_web_ui_cumulative(self, rec):
        # Grok web UI sends the FULL accumulated content in each chunk
        body = _sse(
            {"result": {"message": {"content": "Hello"}}},
            {"result": {"message": {"content": "Hello world"}}},
            {"result": {"message": {"content": "Hello world!"}}},
        )
        assert rec._parse_grok_response(body, "text/event-stream") == "Hello world!"

    def test_non_streaming_fallback(self, rec):
        body = json.dumps({"choices": [{"message": {"content": "Static response."}}]})
        assert rec._parse_grok_response(body, "application/json") == "Static response."

    def test_empty_returns_empty(self, rec):
        assert rec._parse_grok_response("", "text/event-stream") == ""


# ---------------------------------------------------------------------------
# HuggingChat
# ---------------------------------------------------------------------------

class TestHuggingChatParser:
    def test_stream_tokens_then_final_answer(self, rec):
        body = _ndjson(
            {"type": "stream", "token": {"text": "chunk1 "}},
            {"type": "stream", "token": {"text": "chunk2"}},
            {"type": "finalAnswer", "text": "The complete answer."},
        )
        # finalAnswer takes priority over stream tokens
        assert rec._parse_huggingchat_response(body, "text/event-stream") == "The complete answer."

    def test_stream_tokens_only(self, rec):
        body = _ndjson(
            {"type": "stream", "token": {"text": "Part one "}},
            {"type": "stream", "token": {"text": "part two."}},
        )
        assert rec._parse_huggingchat_response(body, "text/event-stream") == "Part one part two."

    def test_final_answer_only(self, rec):
        body = _ndjson({"type": "finalAnswer", "text": "Only final."})
        assert rec._parse_huggingchat_response(body, "text/event-stream") == "Only final."

    def test_empty_returns_empty(self, rec):
        assert rec._parse_huggingchat_response("", "text/event-stream") == ""

    def test_malformed_lines_skipped(self, rec):
        body = "not json\n" + json.dumps({"type": "finalAnswer", "text": "OK"})
        assert rec._parse_huggingchat_response(body, "text/event-stream") == "OK"


# ---------------------------------------------------------------------------
# Meta AI
# ---------------------------------------------------------------------------

class TestMetaAiParser:
    def test_wrapped_delta_format(self, rec):
        body = _sse(
            {"chunk": {"choices": [{"delta": {"content": "Hello "}}]}},
            {"chunk": {"choices": [{"delta": {"content": "Meta"}}]}},
        )
        assert rec._parse_meta_ai_response(body, "text/event-stream") == "Hello Meta"

    def test_flat_text_format(self, rec):
        body = _sse({"text": "Flat "}, {"text": "response"})
        assert rec._parse_meta_ai_response(body, "text/event-stream") == "Flat response"

    def test_non_streaming_fallback(self, rec):
        body = json.dumps({"text": "Non-streaming Meta AI."})
        assert rec._parse_meta_ai_response(body, "application/json") == "Non-streaming Meta AI."

    def test_empty_returns_empty(self, rec):
        assert rec._parse_meta_ai_response("", "text/event-stream") == ""


# ---------------------------------------------------------------------------
# Copilot
# ---------------------------------------------------------------------------

class TestCopilotParser:
    def test_type2_final_message(self, rec):
        obj = {
            "type": 2,
            "item": {
                "messages": [
                    {"author": "user", "text": "Hi"},
                    {"author": "bot", "text": "Hello from Copilot!"},
                ]
            },
        }
        body = json.dumps(obj)
        assert rec._parse_copilot_response(body, "application/json") == "Hello from Copilot!"

    def test_type1_streaming_partial(self, rec):
        obj = {
            "type": 1,
            "arguments": [{"messages": [{"text": "Partial Copilot response"}]}],
        }
        body = json.dumps(obj)
        result = rec._parse_copilot_response(body, "application/json")
        assert "Partial Copilot response" in result

    def test_type2_beats_type1(self, rec):
        type1 = json.dumps({
            "type": 1,
            "arguments": [{"messages": [{"text": "Partial"}]}],
        })
        type2 = json.dumps({
            "type": 2,
            "item": {"messages": [{"author": "bot", "text": "Complete answer."}]},
        })
        body = "\n".join([type1, type2])
        assert rec._parse_copilot_response(body, "application/json") == "Complete answer."

    def test_xie_delimiter(self, rec):
        """Copilot uses \\x1e as segment delimiter."""
        obj = {"type": 2, "item": {"messages": [{"author": "bot", "text": "Delimited."}]}}
        body = "\x1e" + json.dumps(obj)
        assert rec._parse_copilot_response(body, "application/json") == "Delimited."

    def test_internal_search_result_skipped(self, rec):
        """InternalSearchResult messages should be ignored."""
        obj = {
            "type": 1,
            "arguments": [{
                "messages": [
                    {"messageType": "InternalSearchResult", "text": "Search noise"},
                    {"text": "Real response"},
                ]
            }],
        }
        body = json.dumps(obj)
        assert rec._parse_copilot_response(body, "application/json") == "Real response"

    def test_empty_returns_empty(self, rec):
        assert rec._parse_copilot_response("", "application/json") == ""


# ---------------------------------------------------------------------------
# You.com
# ---------------------------------------------------------------------------

class TestYouComParser:
    def test_youChatToken_chunks(self, rec):
        body = _ndjson(
            {"youChatToken": "You "},
            {"youChatToken": "are "},
            {"youChatToken": "welcome."},
        )
        assert rec._parse_youcom_response(body, "text/event-stream") == "You are welcome."

    def test_sse_wrapped_tokens(self, rec):
        body = "\n".join([
            f"data: {json.dumps({'youChatToken': 'SSE '})}",
            f"data: {json.dumps({'youChatToken': 'token'})}",
        ])
        assert rec._parse_youcom_response(body, "text/event-stream") == "SSE token"

    def test_fallback_to_generic(self, rec):
        body = _sse({"choices": [{"delta": {"content": "Generic fallback"}}]})
        assert rec._parse_youcom_response(body, "text/event-stream") == "Generic fallback"

    def test_empty_returns_empty(self, rec):
        assert rec._parse_youcom_response("", "text/event-stream") == ""


# ---------------------------------------------------------------------------
# Phind
# ---------------------------------------------------------------------------

class TestPhindParser:
    def test_answer_type_chunks(self, rec):
        body = _sse(
            {"type": "answer", "content": "Phind "},
            {"type": "answer", "content": "says hi."},
        )
        assert rec._parse_phind_response(body, "text/event-stream") == "Phind says hi."

    def test_ignores_non_answer_types(self, rec):
        body = _sse(
            {"type": "metadata", "content": "ignore this"},
            {"type": "answer", "content": "Keep this."},
        )
        assert rec._parse_phind_response(body, "text/event-stream") == "Keep this."

    def test_openai_delta_fallback(self, rec):
        body = _sse({"choices": [{"delta": {"content": "OpenAI delta"}}]})
        assert rec._parse_phind_response(body, "text/event-stream") == "OpenAI delta"

    def test_empty_returns_empty(self, rec):
        assert rec._parse_phind_response("", "text/event-stream") == ""


# ---------------------------------------------------------------------------
# Gemini RPC extractor — ordering and filtering fixes
# ---------------------------------------------------------------------------

class TestGeminiRpcExtractor:
    def test_preserves_insertion_order(self, rec):
        """Paragraphs should appear in the order Gemini returned them, not by length."""
        # Simulate two paragraphs: short one first, longer one second
        short = "Short answer."
        long_text = "This is a much longer paragraph that contains more information."
        # Build a fake nested structure
        raw = json.dumps([[short], [long_text]])
        result = rec._extract_gemini_rpc_text(raw)
        # Short paragraph should appear BEFORE the long one
        assert result.index(short) < result.index(long_text)

    def test_short_answers_not_filtered(self, rec):
        """Answers under 40 chars ending with punctuation should pass through."""
        short = "Yes."
        raw = json.dumps([[short]])
        result = rec._extract_gemini_rpc_text(raw)
        assert short in result

    def test_numbered_list_items_not_filtered(self, rec):
        """Strings ending with digits (numbered list items) should pass through."""
        item = "Step 1"
        raw = json.dumps([[item]])
        result = rec._extract_gemini_rpc_text(raw)
        assert item in result

    def test_hashes_filtered(self, rec):
        """Long hex strings (content hashes, IDs) should be filtered out."""
        hash_str = "a" * 24  # 24-char lowercase hex-like string
        raw = json.dumps([[hash_str]])
        result = rec._extract_gemini_rpc_text(raw)
        assert hash_str not in result

    def test_internal_tokens_filtered(self, rec):
        """Known Gemini internal tokens should be filtered."""
        raw = json.dumps([["af.httprm", "di", "en", "US"]])
        result = rec._extract_gemini_rpc_text(raw)
        assert result.strip() == ""


# ---------------------------------------------------------------------------
# Gemini bard prompt candidate filtering
# ---------------------------------------------------------------------------

class TestGeminiPromptCandidateFilter:
    """Verify _choose_best_prompt_candidate rejects the garbage seen in the user test DB."""

    def test_rejects_null(self, rec):
        assert rec._choose_best_prompt_candidate(["NULL"]) == ""

    def test_rejects_none(self, rec):
        assert rec._choose_best_prompt_candidate(["NONE"]) == ""

    def test_rejects_single_digit(self, rec):
        assert rec._choose_best_prompt_candidate(["1"]) == ""

    def test_rejects_show_debug_info(self, rec):
        assert rec._choose_best_prompt_candidate(["show_debug_info"]) == ""

    def test_rejects_dotted_identifier(self, rec):
        # e.g. person.photo
        assert rec._choose_best_prompt_candidate(["person.photo"]) == ""

    def test_rejects_image_generation_key(self, rec):
        assert rec._choose_best_prompt_candidate(["image_generation_soft:1"]) == ""

    def test_rejects_base64_blob(self, rec):
        # Observed in user test: base64 string with / chars
        blob = "tCs0BAQF6TcE8nRKP7mep/5VZl1RxfR2yRile0JXxbajUB8nvg"
        assert rec._choose_best_prompt_candidate([blob]) == ""

    def test_accepts_real_prompt_hi(self, rec):
        # Short but valid human text
        assert rec._choose_best_prompt_candidate(["hi"]) == "hi"

    def test_accepts_real_prompt_sentence(self, rec):
        result = rec._choose_best_prompt_candidate(["Tell me something interesting."])
        assert result == "Tell me something interesting."

    def test_picks_best_from_mixed(self, rec):
        # Given garbage + real text, should pick the real text
        candidates = ["NULL", "show_debug_info", "Tell me something interesting.", "1"]
        assert rec._choose_best_prompt_candidate(candidates) == "Tell me something interesting."


@§A_4a26e87a@ C:/LLM Buddy\tests\__init__.py


