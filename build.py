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
