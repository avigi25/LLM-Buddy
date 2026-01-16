@echo off
echo Starting LLM Proxy Recorder...
echo.

:: Check if Python is installed
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install dependencies
echo Installing dependencies...
pip install mitmproxy

:: Start the proxy recorder
echo.
echo Starting proxy on port 8080...
echo.
echo IMPORTANT: You need to configure your browser to use this proxy:
echo   - Host: 127.0.0.1
echo   - Port: 8080
echo.
echo Press Ctrl+C to stop the proxy recorder
echo.

:: Start the mitmproxy with our script
mitmdump -s proxy_recorder.py --listen-port 8080

pause


