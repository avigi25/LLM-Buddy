#!/bin/bash
echo "Starting LLM Buddy Proxy and MCP Recorders..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python not found. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start both services using tmux if available, or in background
echo
echo "Starting services..."
echo

if command -v tmux &> /dev/null; then
    # Use tmux to start both services in separate windows
    
    # Create a new session for MCP
    tmux new-session -d -s llm-buddy -n mcp "source venv/bin/activate && python3 mcp_recorder.py"
    
    # Create a new window for proxy
    tmux new-window -t llm-buddy -n proxy "source venv/bin/activate && mitmdump -s proxy_recorder.py --listen-port 8080"
    
    echo "Services started in tmux session 'llm-buddy'"
    echo "To attach to the session, run: tmux attach -t llm-buddy"
else
    # Start in background if tmux not available
    echo "Starting MCP recorder in background..."
    source venv/bin/activate && python3 mcp_recorder.py > mcp_recorder.log 2>&1 &
    MCP_PID=$!
    
    echo "Starting proxy recorder in background..."
    source venv/bin/activate && mitmdump -s proxy_recorder.py --listen-port 8080 > proxy_recorder.log 2>&1 &
    PROXY_PID=$!
    
    echo "Services started in background"
    echo "MCP PID: $MCP_PID"
    echo "Proxy PID: $PROXY_PID"
    echo "Check log files for output"
fi

echo
echo "IMPORTANT PROXY INSTRUCTIONS:"
echo "  - Configure your browser to use proxy:"
echo "  - Host: 127.0.0.1"
echo "  - Port: 8080"
echo
echo "If this is your first time, you will need to accept the MITM certificate in your browser"
echo


