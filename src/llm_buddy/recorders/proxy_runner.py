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
