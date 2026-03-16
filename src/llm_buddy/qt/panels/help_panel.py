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
