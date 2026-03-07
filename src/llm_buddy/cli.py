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
