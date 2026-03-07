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
