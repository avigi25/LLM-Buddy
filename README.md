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