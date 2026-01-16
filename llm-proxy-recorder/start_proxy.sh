#!/bin/bash
echo "Starting LLM Proxy Recorder..."
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
pip install mitmproxy

# Start the proxy recorder
echo
echo "Starting proxy on port 8080..."
echo
echo "IMPORTANT: You need to configure your browser to use this proxy:"
echo "  - Host: 127.0.0.1"
echo "  - Port: 8080"
echo
echo "Press Ctrl+C to stop the proxy recorder"
echo

# Start mitmproxy with our script
mitmdump -s proxy_recorder.py --listen-port 8080

