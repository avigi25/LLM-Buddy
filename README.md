# LLM Buddy - Universal Prompt Recording & Management System

A comprehensive solution for capturing, organizing, and analyzing prompts from all major LLM services. LLM Buddy combines proxy-based recording, MCP integration, and a powerful GUI to help you track your AI interactions across ChatGPT, Claude, Gemini, and other platforms.

## 🌟 Overview

LLM Buddy is designed for developers, researchers, and power users who want to maintain a complete record of their LLM interactions. Whether you're building AI applications, conducting research, or simply want to track your conversations, LLM Buddy provides a unified system for prompt capture and management.

### Key Features

- **🔍 Universal Prompt Capture**: Records prompts from any LLM service (ChatGPT, Claude, Gemini, Perplexity, and more)
- **🌐 Proxy-Based Recording**: Intercepts HTTP/HTTPS traffic without relying on UI selectors
- **🖥️ Claude Desktop Integration**: Native MCP (Model Context Protocol) server for Claude Desktop
- **📊 Unified Database**: SQLite + JSON dual storage for reliability and compatibility
- **📁 File Association**: Link prompts to project files for contextual tracking
- **🎯 Powerful GUI**: Feature-rich Tkinter application for prompt management and analysis
- **🔄 Real-time Sync**: Automatic updates when new prompts are captured
- **🔒 Privacy-Focused**: All data stored locally on your machine

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        LLM Buddy System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │  Proxy Server   │  │  MCP Server      │  │ Flask API  │ │
│  │  (mitmproxy)    │  │  (Claude Desktop)│  │ (Browser)  │ │
│  │                 │  │                  │  │            │ │
│  │ • Web LLMs      │  │ • Auto Record    │  │ • REST API │ │
│  │ • API Calls     │  │ • File Tracking  │  │ • CORS     │ │
│  │ • ChatGPT       │  │ • Resources      │  │ Enabled    │ │
│  │ • Claude Web    │  │ • Tools          │  │            │ │
│  │ • Gemini        │  │                  │  │            │ │
│  │ • Perplexity    │  │                  │  │            │ │
│  └────────┬────────┘  └────────┬─────────┘  └─────┬──────┘ │
│           │                    │                   │        │
│           └────────────────────┼───────────────────┘        │
│                                │                            │
│                     ┌──────────▼──────────┐                 │
│                     │  Prompt Database    │                 │
│                     │  ┌────────────────┐ │                 │
│                     │  │ SQLite (Main)  │ │                 │
│                     │  └────────────────┘ │                 │
│                     │  ┌────────────────┐ │                 │
│                     │  │ JSON (Backup)  │ │                 │
│                     │  └────────────────┘ │                 │
│                     └──────────┬──────────┘                 │
│                                │                            │
│                     ┌──────────▼──────────┐                 │
│                     │   GUI Application   │                 │
│                     │   (combiner2.py)    │                 │
│                     │                     │                 │
│                     │ • Prompt Viewer     │                 │
│                     │ • File Manager      │                 │
│                     │ • Search & Filter   │                 │
│                     │ • Token Analysis    │                 │
│                     │ • eADR Notes        │                 │
│                     │ • Code Combiner     │                 │
│                     └─────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

### System Requirements

- **Operating System**: Windows, macOS, or Linux
- **Python**: 3.8 or higher
- **RAM**: 2GB minimum (4GB recommended)
- **Disk Space**: 500MB for installation + storage for your prompts

### Required Python Packages

Core dependencies:
- `mitmproxy>=9.0.1` - HTTP/HTTPS proxy for web LLM recording
- `mcp>=0.31.0` - Model Context Protocol for Claude Desktop
- `flask>=2.3.3` - REST API server
- `flask-cors>=4.0.0` - Cross-origin resource sharing
- `tiktoken` - Token counting
- `watchdog` - File system monitoring

Optional but recommended:
- `tkinter` - GUI application (usually included with Python)
- `sqlite3` - Database (included with Python)

---

## 🚀 Installation

### Quick Start

#### Windows

1. **Clone or download this repository**
   ```batch
   git clone <repository-url>
   cd llm-buddy
   ```

2. **Run the automated setup**
   ```batch
   start_all.bat
   ```

   This will:
   - Create a virtual environment
   - Install all dependencies
   - Start the proxy server on port 8080
   - Start the MCP server (if configured)

#### macOS/Linux

1. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd llm-buddy
   ```

2. **Make scripts executable**
   ```bash
   chmod +x start_all.sh start_proxy.sh run_server.sh
   ```

3. **Run the automated setup**
   ```bash
   ./start_all.sh
   ```

### Manual Installation

If you prefer manual setup:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### 1. Configure Claude Desktop (Optional)

If you use Claude Desktop, configure it to use the MCP server:

```bash
# Windows
python configure_claude_desktop.py

# macOS/Linux
python3 configure_claude_desktop.py
```

This script will:
- Locate your Claude Desktop configuration file
- Create a backup
- Add the MCP server configuration
- Provide instructions for restart

**Manual Configuration:**

Find your Claude Desktop config file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Add the MCP server:

```json
{
  "mcpServers": {
    "prompt-recorder": {
      "command": "python",
      "args": ["<path-to-llm-buddy>/auto_claude_recorder.py"]
    }
  }
}
```

**Important**: Use the full absolute path to `auto_claude_recorder.py`.

### 2. Configure Proxy for Web Browsers

To capture prompts from web-based LLMs (ChatGPT, Claude, Gemini, etc.), configure your browser to use the proxy:

**Browser Proxy Settings:**
- **Host/Address**: `127.0.0.1`
- **Port**: `8080`
- **Protocol**: HTTP/HTTPS

**Chrome/Edge** (via extension):
- Install a proxy extension like "Proxy SwitchyOmega"
- Create profile with settings above
- Enable for LLM sites only (recommended)

**Firefox**:
- Settings → Network Settings → Manual proxy configuration
- HTTP Proxy: `127.0.0.1`, Port: `8080`
- ☑️ Also use this proxy for HTTPS

**System-Wide Proxy** (affects all applications):
- **Windows**: Settings → Network & Internet → Proxy
- **macOS**: System Preferences → Network → Advanced → Proxies
- **Linux**: Settings → Network → Network Proxy

### 3. Accept MITM Certificate

**First time only**: When you visit an HTTPS site through the proxy:

1. You'll see a certificate warning
2. Navigate to `http://mitm.it` through the proxy
3. Download and install the certificate for your OS
4. Restart your browser

**Certificate locations**:
- **Windows**: Double-click `.cer` file → Install Certificate → Place in "Trusted Root Certification Authorities"
- **macOS**: Double-click `.pem` file → Add to Keychain → Always Trust
- **Linux**: Copy to `/usr/local/share/ca-certificates/` → Run `sudo update-ca-certificates`

---

## 📖 Usage

### Starting the Services

#### Start Everything (Recommended)

**Windows:**
```batch
start_all.bat
```

**macOS/Linux:**
```bash
./start_all.sh
```

This starts:
1. **Proxy Server** (port 8080) - Records web LLM prompts
2. **MCP Server** - Integrates with Claude Desktop
3. **Flask API** (optional, port 5000) - REST API for browser extensions

#### Start Components Individually

**Proxy Server Only:**
```batch
# Windows
start_proxy.bat

# macOS/Linux
./start_proxy.sh
```

**Flask API Server:**
```batch
# Windows
cd prompt_server
run_server.bat

# macOS/Linux
cd prompt_server
./run_server.sh
```

**MCP Server:**
```bash
# This runs automatically when Claude Desktop starts
# if configured in claude_desktop_config.json
```

### Using the GUI Application

Launch the main application:

```bash
python combiner2.py
```

The GUI provides comprehensive functionality:

#### 📁 File Management Tab
- **Add Folders**: Recursively scan for code files
- **Add Files**: Select individual files
- **Filters**: 
  - File extensions (`.py`, `.js`, `.md`, etc.)
  - Minimum token count
  - Ignore patterns (e.g., `node_modules`, `.git`)
- **Token Analysis**: View token counts per file
- **Combine Files**: Merge selected files with headers/footers

#### 💬 Prompt History Tab
- **View All Prompts**: Chronological list of recorded prompts
- **Filter Options**:
  - By LLM (ChatGPT, Claude, Gemini, etc.)
  - By source (Proxy, MCP, Browser Extension)
  - By date range
  - By file associations
  - Text search in prompt content
- **Associate Files**: Link prompts to project files retroactively
- **Export**: Save prompts to various formats
- **Conversation Tracking**: Group prompts by conversation ID

#### 📝 eADR Notes Tab
- **Create Notes**: Document project decisions and context
- **Project Organization**: Tag notes by project
- **Timeline View**: Chronological project history
- **Auto-Notes**: Automatically created when combining files
- **Search & Filter**: Find notes by content or project

#### 🔄 Real-time Updates
- Auto-refresh when new prompts are captured
- File system monitoring
- Live token count updates

### Recording Prompts

#### From Claude Desktop (MCP)

Once configured, prompts are recorded automatically:

1. Open Claude Desktop
2. Start a conversation
3. Prompts are saved automatically to `claude_prompts.json`

**Optional**: Use MCP tools within Claude Desktop:
- `auto_record_prompt` - Manually record a prompt
- `register_active_files` - Associate files with future prompts
- `list_prompts` - View recent prompts
- `toggle_auto_recording` - Enable/disable recording

#### From Web Browsers (Proxy)

With the proxy configured:

1. Start the proxy server (`start_proxy.bat` or `./start_proxy.sh`)
2. Configure your browser proxy settings (see Configuration section)
3. Navigate to any LLM website:
   - ChatGPT (chat.openai.com, chatgpt.com)
   - Claude (claude.ai)
   - Gemini (gemini.google.com)
   - Perplexity (perplexity.ai)
   - And others
4. Send prompts normally
5. Prompts are captured and saved automatically

**Supported LLM Services:**
- ✅ ChatGPT (OpenAI)
- ✅ Claude (Anthropic)
- ✅ Gemini (Google)
- ✅ Bard (Google)
- ✅ Perplexity AI
- ✅ Mistral AI
- ✅ Cohere
- ✅ Together AI
- ✅ Groq
- ✅ DeepInfra
- ✅ Any OpenAI-compatible API

#### Using the REST API

If you have a browser extension or custom integration:

**Record a Prompt:**
```bash
POST http://localhost:5000/record_prompt
Content-Type: application/json

{
  "promptText": "Your prompt here",
  "llmName": "ChatGPT",
  "modelName": "gpt-4",
  "pageTitle": "Optional page title",
  "url": "https://example.com"
}
```

**Retrieve Prompts:**
```bash
GET http://localhost:5000/prompts
```

**Associate Files:**
```bash
POST http://localhost:5000/associate_prompt
Content-Type: application/json

{
  "prompt_id": "uuid-here",
  "file_path": "/path/to/file.py"
}
```

---

## 💾 Database Schema

### SQLite Database (prompts.db)

**Table: `prompts`**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Unique UUID for each prompt |
| timestamp | TEXT | ISO format timestamp |
| source | TEXT | Origin: "proxy", "mcp", "browser_extension", "Claude Desktop", "Web Browser" |
| llm_name | TEXT | LLM service name (ChatGPT, Claude, etc.) |
| model_name | TEXT | Specific model (gpt-4, claude-3-opus, etc.) |
| prompt_text | TEXT | The actual prompt content |
| description | TEXT | Optional description/summary |
| url | TEXT | URL where prompt was sent (if applicable) |
| conversation_id | TEXT | For grouping related prompts |
| metadata | TEXT | JSON string with additional data |

**Table: `file_associations`**
| Column | Type | Description |
|--------|------|-------------|
| prompt_id | TEXT | Foreign key to prompts.id |
| file_path | TEXT | Full path to associated file |
| token_change | INTEGER | Token difference after prompt (optional) |

### JSON Database (claude_prompts.json)

Backup format for compatibility:

```json
[
  {
    "id": "uuid",
    "timestamp": "2025-01-16T10:30:00",
    "prompt_text": "Your prompt",
    "description": "Prompt description",
    "model": "ChatGPT",
    "files": ["/path/to/file1.py", "/path/to/file2.js"],
    "source": "Web Browser"
  }
]
```

---

## 🔧 Advanced Configuration

### Active File Registration

Automatically associate prompts with files you're working on:

**Via MCP (Claude Desktop):**
```python
# Claude will call this automatically if files are mentioned
register_active_files([
    "/project/src/main.py",
    "/project/src/utils.py"
])
```

**Via Proxy (programmatic):**
```python
from proxy_recorder import set_active_files

set_active_files([
    "/project/src/main.py",
    "/project/src/utils.py"
])
```

### Custom Ignored Folders

In the GUI, set custom ignore patterns:
```
node_modules, .git, __pycache__, venv, .venv, dist, build
```

### Token Counting

LLM Buddy uses tiktoken with `cl100k_base` encoding (GPT-4 standard). This provides accurate token counts for:
- Individual files
- Combined outputs
- Prompt texts
- Entire projects

---

## 🐛 Troubleshooting

### Proxy Server Issues

**Problem**: "Connection refused" or "Proxy not responding"

**Solutions**:
1. Verify proxy server is running:
   ```bash
   # Check if port 8080 is in use
   # Windows:
   netstat -an | findstr 8080
   # macOS/Linux:
   lsof -i :8080
   ```

2. Check proxy logs:
   ```bash
   # View proxy_recorder.log
   tail -f proxy_recorder.log
   ```

3. Restart the proxy server

**Problem**: "SSL Certificate Error"

**Solutions**:
1. Install MITM certificate (see Configuration section)
2. Navigate to `http://mitm.it` while proxy is active
3. Restart browser after installing certificate

### MCP Server Issues

**Problem**: Claude Desktop doesn't show MCP tools

**Solutions**:
1. Verify configuration in `claude_desktop_config.json`
2. Use absolute paths (not relative)
3. Check Python is in PATH
4. Restart Claude Desktop completely
5. Check MCP server logs:
   ```bash
   # View auto_recorder.log
   tail -f auto_recorder.log
   ```

**Problem**: Prompts not being recorded

**Solutions**:
1. Check if auto-recording is enabled:
   ```python
   # In Claude Desktop, ask:
   "Check if auto-recording is enabled"
   ```
2. Test database write:
   ```python
   # In Claude Desktop, ask:
   "Test the database write functionality"
   ```

### Database Issues

**Problem**: "Database locked" error

**Solutions**:
1. Close all instances of the GUI application
2. Check for orphaned processes:
   ```bash
   # Windows:
   tasklist | findstr python
   # macOS/Linux:
   ps aux | grep python
   ```
3. Delete lock file if exists:
   ```bash
   rm prompts.db-journal
   ```

**Problem**: Corrupted database

**Solutions**:
1. JSON backup is always available: `claude_prompts.json`
2. Import from JSON:
   ```python
   from prompt_database import PromptDatabase
   db = PromptDatabase()
   count = db.import_from_json()
   print(f"Imported {count} prompts")
   ```

### GUI Application Issues

**Problem**: GUI not starting

**Solutions**:
1. Check tkinter is installed:
   ```python
   python -c "import tkinter"
   ```
2. Install tkinter:
   ```bash
   # Ubuntu/Debian:
   sudo apt-get install python3-tk
   # macOS (via Homebrew):
   brew install python-tk
   ```

**Problem**: "File not found" errors

**Solutions**:
1. Ensure working directory is correct
2. Use absolute paths in configurations
3. Check file permissions

### General Issues

**Problem**: High memory usage

**Solutions**:
1. Reduce the number of watched files
2. Clear old prompts from database periodically
3. Increase `check_interval` in PromptFileWatcher (default: 2.0s)

**Problem**: Slow performance

**Solutions**:
1. Reduce file tree depth in GUI
2. Use more specific file filters
3. Index the SQLite database:
   ```sql
   CREATE INDEX idx_timestamp ON prompts(timestamp);
   CREATE INDEX idx_source ON prompts(source);
   CREATE INDEX idx_llm ON prompts(llm_name);
   ```

---

## 📊 Use Cases

### For Developers

**Code Review Tracking:**
- Record all LLM interactions during code review
- Associate prompts with specific files
- Track token usage per project
- Maintain audit trail of AI assistance

**Project Documentation:**
- Generate eADR notes from LLM discussions
- Link conversations to implementation
- Export conversation history per feature

### For Researchers

**LLM Behavior Analysis:**
- Capture prompts across multiple LLM services
- Compare responses to identical prompts
- Track conversation flows
- Export data for analysis

**Dataset Creation:**
- Build custom prompt-response datasets
- Tag and categorize interactions
- Filter by LLM, model, date range
- Export to various formats

### For Power Users

**Conversation History:**
- Never lose important conversations
- Search across all LLM interactions
- Export specific conversations
- Track monthly usage patterns

**Multi-LLM Workflow:**
- Use different LLMs for different tasks
- Maintain unified history
- Compare LLM performance
- Switch contexts seamlessly

---

## 🔐 Privacy & Security

### Data Storage

- **100% Local**: All data stored on your computer
- **No Cloud Sync**: No data sent to external servers
- **No Telemetry**: No usage tracking or analytics
- **Open Source**: Audit the code yourself

### Proxy Security

The MITM proxy can intercept HTTPS traffic. Important notes:

- ⚠️ **Only use the proxy for LLM services you own accounts for**
- ⚠️ **Don't use for sensitive sites** (banking, email, etc.)
- ⚠️ **Use browser profiles** or extensions to enable proxy only for LLM sites
- ✅ **Certificate is self-signed** and only valid on your machine
- ✅ **No data leaves your computer** except to the intended LLM service

### Recommended Setup

**Browser Proxy Extensions** (preferred):
- Use "Proxy SwitchyOmega" or similar
- Create rules for LLM domains only:
  - `*.openai.com`
  - `*.anthropic.com`
  - `*.claude.ai`
  - `*.google.com` (if using Gemini/Bard)
  - etc.

**System-Wide Proxy** (not recommended):
- Affects all applications
- Harder to control scope
- Can cause issues with other software

---

## 🔄 Updates & Maintenance

### Updating LLM Buddy

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
./start_all.sh  # or start_all.bat on Windows
```

### Database Maintenance

**Backup Database:**
```bash
# SQLite
cp prompts.db prompts.db.backup

# JSON (always available)
cp claude_prompts.json claude_prompts.json.backup
```

**Cleanup Old Prompts:**
```sql
-- Delete prompts older than 6 months
DELETE FROM prompts 
WHERE timestamp < date('now', '-6 months');

-- Vacuum to reclaim space
VACUUM;
```

**Export to CSV:**
```python
import sqlite3
import csv

conn = sqlite3.connect('prompts.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM prompts')

with open('prompts_export.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([desc[0] for desc in cursor.description])
    writer.writerows(cursor.fetchall())
```

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Support for additional LLM services
- UI/UX enhancements
- Performance optimizations
- Documentation improvements
- Bug fixes

### Adding Support for New LLM Services

To add a new LLM service to the proxy recorder:

1. Open `proxy_recorder.py`
2. Add detection pattern:
   ```python
   def _is_newllm_request(self, url):
       patterns = [r'api\.newllm\.com/v1/messages']
       return any(re.search(pattern, url) for pattern in patterns)
   ```
3. Add processing function:
   ```python
   def _process_newllm(self, flow, origin):
       # Extract prompt from request
       # Record to database
       pass
   ```
4. Add to request handler:
   ```python
   elif self._is_newllm_request(url):
       self._process_newllm(flow, origin)
   ```

---

## 📚 Additional Resources

### File Descriptions

- **`auto_claude_recorder.py`**: MCP server for Claude Desktop integration
- **`proxy_recorder.py`**: mitmproxy addon for web LLM recording
- **`prompt_database.py`**: Unified database interface (SQLite + JSON)
- **`combiner2.py`**: Main GUI application
- **`configure_claude_desktop.py`**: Claude Desktop configuration helper
- **`app.py`**: Flask REST API server
- **`start_all.*`**: Scripts to start all services
- **`start_proxy.*`**: Scripts to start proxy only

### Port Usage

- **8080**: Proxy server (mitmproxy)
- **5000**: Flask API server (optional)
- MCP uses stdio communication (no ports)

### Log Files

- **`proxy_recorder.log`**: Proxy server activity and errors
- **`auto_recorder.log`**: MCP server activity and errors
- **`prompt_server.log`**: Flask API server logs

---

## 📄 License

MIT License

---

## 💬 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review troubleshooting section above

---

## 🎯 Roadmap

Future enhancements under consideration:

- [ ] Web UI dashboard
- [ ] Multi-user support
- [ ] Cloud sync option (optional, encrypted)
- [ ] Advanced analytics and visualizations
- [ ] Plugin system for custom integrations
- [ ] Mobile app for viewing history
- [ ] AI-powered prompt search and recommendations
- [ ] Integration with more LLM services
- [ ] Conversation branching visualization
- [ ] Automated prompt optimization suggestions

---

**Version**: 1.0.0  
**Last Updated**: January 2025  
**Created by**: Anthony Vigil
