# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for LLM Buddy — three executables, shared runtime."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect tiktoken encoding data files
tiktoken_datas = collect_data_files("tiktoken_ext") + collect_data_files("tiktoken")

# Common hidden imports shared across all three targets
_common_hidden = [
    "llm_buddy.paths",
    "llm_buddy.core.database",
    "llm_buddy.core.eadr",
    "llm_buddy.core.profiles",
    "llm_buddy.core.sessions",
    "llm_buddy.core.forking",
    "llm_buddy.core.backup",
    "llm_buddy.core.tokens",
    "llm_buddy.core.rollback",
    "sqlite3",
    "requests", "urllib3", "certifi", "charset_normalizer", "idna",
    "dotenv",
]

# ── Analysis A: Main GUI ───────────────────────────────────────────
a_gui = Analysis(
    ["src/llm_buddy/qt/app.py"],
    pathex=["src"],
    datas=[
        ("extension", "extension"),
        ("icon.ico", "."),
    ] + tiktoken_datas,
    hiddenimports=_common_hidden + [
        # Qt / GUI
        "llm_buddy.qt.theme",
        "llm_buddy.qt.main_window",
        "llm_buddy.qt.panels.control_panel",
        "llm_buddy.qt.panels.eadr_panel",
        "llm_buddy.qt.panels.preview_panel",
        "llm_buddy.qt.panels.log_panel",
        "llm_buddy.qt.panels.help_panel",
        "llm_buddy.qt.panels.rollback_panel",
        "llm_buddy.qt.panels.compare_panel",
        "llm_buddy.qt.panels.backup_panel",
        "llm_buddy.qt.panels.capture_widgets",
        "llm_buddy.qt.panels.prompts_panel",
        "llm_buddy.qt.panels.analytics_panel",
        "llm_buddy.qt.panels.sessions_panel",
        "llm_buddy.qt.panels.forking_panel",
        # Services
        "llm_buddy.services.file_service",
        "llm_buddy.services.analytics_service",
        "llm_buddy.services.prompt_service",
        "llm_buddy.services.preview_service",
        "llm_buddy.services.backup_service",
        "llm_buddy.services.subprocess_manager",
        # Flask (extension server runs in-thread)
        "flask", "flask_cors", "flask.json",
        "jinja2", "markupsafe", "werkzeug", "click", "itsdangerous",
        "llm_buddy.recorders.api_server",
        # tiktoken
        "tiktoken", "tiktoken_ext", "tiktoken_ext.openai_public",
        # watchdog
        "watchdog", "watchdog.observers", "watchdog.events",
    ],
    excludes=["tkinter", "unittest", "test", "pytest"],
    cipher=block_cipher,
)

# ── Analysis B: MCP Recorder ──────────────────────────────────────
a_mcp = Analysis(
    ["src/llm_buddy/recorders/mcp_recorder.py"],
    pathex=["src"],
    hiddenimports=_common_hidden + [
        "mcp", "mcp.server", "mcp.server.fastmcp",
        "mcp.server.fastmcp.prompts", "mcp.server.fastmcp.prompts.base",
        "mcp.server.lowlevel", "mcp.server.lowlevel.server",
    ] + collect_submodules("mcp"),
    excludes=["tkinter", "unittest", "test", "pytest",
              "PySide6", "mitmproxy"],
    cipher=block_cipher,
)

# ── Analysis C: Proxy Recorder ────────────────────────────────────
a_proxy = Analysis(
    ["src/llm_buddy/recorders/proxy_runner.py"],
    pathex=["src"],
    hiddenimports=_common_hidden + [
        "llm_buddy.recorders.proxy_recorder",
    ] + collect_submodules("mitmproxy"),
    excludes=["tkinter", "unittest", "test", "pytest", "PySide6"],
    cipher=block_cipher,
)

# ── Merge all three analyses to share _internal/ ──────────────────
MERGE(
    (a_gui, "LLM Buddy", "LLM Buddy"),
    (a_mcp, "llm-buddy-mcp", "llm-buddy-mcp"),
    (a_proxy, "llm-buddy-proxy", "llm-buddy-proxy"),
)

# ── PYZ (compressed Python modules) ──────────────────────────────
pyz_gui = PYZ(a_gui.pure, a_gui.zipped_data, cipher=block_cipher)
pyz_mcp = PYZ(a_mcp.pure, a_mcp.zipped_data, cipher=block_cipher)
pyz_proxy = PYZ(a_proxy.pure, a_proxy.zipped_data, cipher=block_cipher)

# ── EXE targets ──────────────────────────────────────────────────
exe_gui = EXE(
    pyz_gui, a_gui.scripts, [],
    exclude_binaries=True,
    name="LLM Buddy",
    icon="icon.ico",
    console=False,   # Windowed — no console
    debug=False,
    strip=False,
    upx=True,
)

exe_mcp = EXE(
    pyz_mcp, a_mcp.scripts, [],
    exclude_binaries=True,
    name="llm-buddy-mcp",
    icon="icon.ico",
    console=True,    # stdio for Claude Desktop
    debug=False,
    strip=False,
    upx=True,
)

exe_proxy = EXE(
    pyz_proxy, a_proxy.scripts, [],
    exclude_binaries=True,
    name="llm-buddy-proxy",
    icon="icon.ico",
    console=True,    # stderr logging
    debug=False,
    strip=False,
    upx=True,
)

# ── COLLECT into a single output directory ────────────────────────
coll = COLLECT(
    exe_gui, a_gui.binaries, a_gui.zipfiles, a_gui.datas,
    exe_mcp, a_mcp.binaries, a_mcp.zipfiles, a_mcp.datas,
    exe_proxy, a_proxy.binaries, a_proxy.zipfiles, a_proxy.datas,
    strip=False,
    upx=True,
    name="LLM Buddy",
)
