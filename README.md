# LLM Buddy

A Computer-Aided Method Engineering (CAME) tool for documenting LLM-augmented research through prompt-centric auditable development.

[![DOI](http://img.shields.io/badge/DOI-10.5281/zenodo.1135937826-1073c8?labelColor=000000)](https://doi.org/10.5281/zenodo.18274813)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-3.0.0-green)](https://github.com/avigi25/LLM-Buddy/releases)

## Research Context

**This tool was developed as part of doctoral research at the University of South Florida's Muma College of Business.**

LLM Buddy was created to address methodological challenges in conducting rigorous research with Large Language Models. It was used to document 1,555 prompts across multiple Elaborated Action Design Research (eADR) cycles, enabling the discovery of the "Conversational Forking" methodology and providing unprecedented documentation of AI-augmented development processes.

A prototype paper, *"LLM Buddy: An AI-Augmented Research Environment for Auditable Design Science,"* was submitted to the [DESRIST 2026](https://desrist2026.org/) Prototypes Track.

**Note**: The original research prompt corpus remains proprietary. This repository provides the tool and representative examples to enable replication of the methodology.

## Demo

https://github.com/user-attachments/assets/784748b0-12cc-47bb-b325-5cfb57190743

Link to download the video demonstration of LLM Buddy is available here: [Demo Video](demo/LLM_Buddy_Demo.mp4)

## Overview

LLM Buddy is a desktop application for capturing, organizing, and analyzing prompts and responses from all major LLM services. It combines proxy-based recording, a Chrome extension, MCP integration, and a modern Qt GUI to help researchers and developers maintain a complete, auditable record of their AI interactions.

### Key Features

- **Universal Prompt + Response Capture** — Records both prompts and LLM responses from ChatGPT, Claude, Gemini, Perplexity, and more via four independent capture methods.
- **Chrome Extension** — Automatic DOM-based capture from web LLM interfaces with zero configuration. Detects when streaming completes and sends both sides of the conversation to the local database.
- **HTTPS Proxy Recorder** — Intercepts API-level traffic via mitmproxy for programmatic LLM calls.
- **Claude Desktop MCP Integration** — Native Model Context Protocol server for automatic recording from Claude Desktop.
- **Modern Qt GUI** — Professional PySide6/Qt 6 interface with Light, Dark, and Blue Accent themes, keyboard shortcuts, and a live status bar.
- **Analytics Dashboard** — Charts showing prompt frequency over time, LLM platform distribution, token usage trends, and an activity timeline with date-range filtering.
- **Research Sessions** — Named sessions to group work into bounded periods, with auto-generated summaries and markdown export for research documentation.
- **Auto-Backup & Rollback** — Monitor project files for changes and automatically create timestamped backups. Restore any file from a previous backup with a diff preview.
- **eADR Notes** — Timestamped project notes that serve as an audit trail for AI-assisted development decisions.
- **Profiles** — Save and load named configurations (selected folders, filters, headers) for switching between projects.
- **File & Token Management** — Select files and folders, filter by extension, and see real-time token counts. Combine files into a single prompt-ready text block.
- **Unified Database** — SQLite + JSON dual storage for reliability and compatibility. All data stored locally.

## Installation

Requires **Python 3.9+**.

### Windows

```bash
git clone https://github.com/avigi25/LLM-Buddy.git
cd LLM-Buddy
install.bat
```

The installer creates a virtual environment, installs dependencies, places an **LLM Buddy** shortcut on your Desktop, and optionally configures Claude Desktop MCP integration.

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

Optional dependency groups: `proxy` (mitmproxy), `server` (Flask), `mcp` (Claude Desktop), `all`.

## Usage

```
llm-buddy                  # Launch the GUI (default)
llm-buddy gui              # Launch the Qt GUI explicitly
llm-buddy server           # Start the Flask API server (port 5000)
llm-buddy proxy            # Start the HTTPS proxy recorder (port 8080)
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
    |           (SQLite + JSON dual storage)                |
    +---------------------------+---------------------------+
                                |
                                v
                     +----------+----------+
                     |    GUI Application   |
                     |   (PySide6 / Qt 6)   |
                     +---------------------+
```

All capture methods write to the same `prompts.db` database. The GUI auto-refreshes when a capture source is active.

## Prompt Capture Methods

Both the user's prompt (input) and the LLM's response (output) are captured and stored together.

### 1. Chrome Extension (Easiest)

Best for capturing from web-based LLM chat interfaces.

1. In the **Prompt Tracking** tab, find the **Capture Sources** section and click **Start Server**.
2. In Chrome, go to `chrome://extensions`, enable **Developer mode**, click **Load unpacked**, and select the `extension/` folder.
3. Use ChatGPT, Claude, Gemini, or Perplexity as normal. Prompts and responses are captured automatically.

The extension watches the DOM for the assistant's reply after each prompt submission, waits for the response to finish streaming, and sends both to the API server.

### 2. Claude Desktop (MCP)

Best if you primarily use the Claude Desktop app.

```bash
llm-buddy configure
```

This registers LLM Buddy's MCP server with Claude Desktop. Restart Claude Desktop and all prompts are recorded automatically.

### 3. HTTPS Proxy (Advanced)

Best for capturing API-level traffic including programmatic LLM calls.

In the **Prompt Tracking** tab, click **Start Proxy** in the Capture Sources section. This starts a mitmproxy instance on port 8080 and configures the system proxy. Both requests and responses are parsed and recorded. The proxy is automatically disabled when you stop it or close the app.

Supported services: OpenAI, Anthropic, Google Gemini, Perplexity, Mistral, Cohere, Together AI, Groq, DeepInfra, and any OpenAI-compatible API.

### 4. Manual Entry

In the **Prompt Tracking** tab, use the **New Prompt** form to type or paste a prompt, select the LLM used, and click **Record Prompt**.

## GUI Tabs

| Tab | Purpose |
|-----|---------|
| **eADR Notes** | Timestamped project notes for tracking decisions and progress |
| **Preview** | Live preview of combined file text with dual token counts |
| **Logs** | Real-time application event log |
| **Prompt Tracking** | Unified prompt/response history, capture source controls, file associations |
| **Auto-Backup** | Configure and monitor automatic file backups |
| **Rollback** | Browse backups, preview diffs, restore files |
| **Analytics** | Charts for prompt frequency, LLM distribution, token usage, and activity timeline |
| **Sessions** | Named research sessions with auto-generated summaries and markdown export |
| **Help** | Built-in usage instructions and keyboard shortcuts |
| **About** | Version and dependency info |

## Project Structure

```
LLM-Buddy/
├── src/llm_buddy/
│   ├── cli.py                    # CLI entry point
│   ├── core/
│   │   ├── backup.py             # Auto-backup logic
│   │   ├── database.py           # Unified prompt database (SQLite + JSON)
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
│   │   ├── prompt_service.py     # Prompt CRUD operations
│   │   └── subprocess_manager.py # Background process management
│   ├── qt/                       # PySide6 GUI (v3.0)
│   │   ├── app.py                # QApplication bootstrap
│   │   ├── main_window.py        # Main window, signals, menus, status bar
│   │   ├── theme.py              # Light, Dark, Blue Accent themes
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
│   │   └── proxy_recorder.py     # mitmproxy-based HTTPS recorder
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

LLM Buddy is designed as a single-user desktop tool. All data is stored in a local SQLite database (`prompts.db`) with no concurrent-access locking beyond SQLite's default file-level locks. Running multiple instances of the GUI simultaneously against the same database may result in "database locked" errors. There is no multi-user collaboration, cloud sync, or remote access capability.

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

Prompt history and file backups are maintained independently from any version control system. There is no automatic linking between prompts and Git commits, branches, or diffs. Correlating prompt activity with code changes currently requires manual cross-referencing by timestamp.

### Converging IDE-Integrated LLM Features

The LLM provider landscape is rapidly evolving in ways that overlap with LLM Buddy's feature set. Anthropic's Claude Code extension for VS Code now offers built-in conversation history, checkpoints, and the ability to fork conversations — capabilities that closely parallel LLM Buddy's session management and conversational forking features. Meanwhile, VS Code's February 2026 release (v1.110) introduced native chat session forking, context compaction, and third-party agent support for both Claude and OpenAI Codex directly through GitHub Copilot. Chat histories from Claude Code sessions are even syncing into GitHub Copilot's history panel automatically. As these IDE-native integrations mature, the standalone capture and session management value of a tool like LLM Buddy may diminish for developers already working within these ecosystems. However, LLM Buddy's cross-platform, provider-agnostic approach — capturing from any LLM service into a single unified database — and its research-oriented features (eADR notes, analytics, file-to-prompt association) remain differentiated from any single vendor's IDE integration.

### Evaluation Scope

The current evaluation is based on a single-researcher longitudinal study (1,555 prompts across six eADR iterations). Broader validation with multiple research teams across different DSR projects is needed to assess generalizability of the tool and methodology.

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
  version = {3.0.0}
}
```
## Disclaimer

This software is provided **for educational and research purposes only**. LLM Buddy interacts with third-party services (including ChatGPT, Claude, Gemini, and others) by intercepting web traffic and DOM content. These techniques may conflict with the terms of service of individual LLM providers. Users are solely responsible for ensuring their use of this tool complies with all applicable terms of service, laws, and regulations.

This software is provided "as is" without warranty of any kind, express or implied. The authors assume no responsibility or liability for any consequences arising from the use of this tool. Features that depend on third-party website structures or APIs may break at any time without notice due to changes made by those providers.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

Anthony Vigil — anthony.vigil@usf.edu

**Version**: 3.0.0
**Last Updated**: March 2026
