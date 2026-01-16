@echo off
echo Starting LLM Buddy Proxy and MCP Recorders...
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
pip install -r requirements.txt

:: Start both MCP and proxy in separate windows
echo.
echo Starting services...
echo.

:: Start MCP recorder
start cmd /k "call venv\Scripts\activate.bat && python mcp_recorder.py"

:: Wait a moment for MCP to initialize
timeout /t 2 > nul

:: Start proxy recorder
start cmd /k "call venv\Scripts\activate.bat && mitmdump -s proxy_recorder.py --listen-port 8080"

echo.
echo Services started!
echo.
echo IMPORTANT PROXY INSTRUCTIONS:
echo   - Configure your browser to use proxy:
echo   - Host: 127.0.0.1
echo   - Port: 8080
echo.
echo If this is your first time, you will need to accept the MITM certificate in your browser
echo.
echo Press any key to exit this window...
pause > nul


