@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   LLM Buddy - Windows Installer
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.9+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during install!
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Found Python %PYVER%
echo.

:: Save install directory
set "INSTALL_DIR=%~dp0"

:: Clear any stale proxy left over from a previous proxy recorder session
:: (A leftover proxy breaks pip because it tries to connect to 127.0.0.1:8080)
for /f "tokens=3" %%v in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2^>nul ^| findstr ProxyEnable') do (
    if "%%v"=="0x1" (
        echo NOTE: Clearing stale system proxy before install...
        reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul 2>nul
    )
)

:: Create virtual environment
if not exist "%INSTALL_DIR%.venv" (
    echo [1/4] Creating virtual environment...
    python -m venv "%INSTALL_DIR%.venv"
) else (
    echo [1/4] Virtual environment already exists.
)

:: Activate and install
echo [2/4] Installing LLM Buddy...
call "%INSTALL_DIR%.venv\Scripts\activate.bat"
pip install -e "%INSTALL_DIR%." --quiet 2>nul
if errorlevel 1 (
    pip install -e "%INSTALL_DIR%."
)

:: Install all optional extras by default (easier for end users)
echo [3/4] Installing optional components...
pip install -e "%INSTALL_DIR%.[all]" --quiet 2>nul
if errorlevel 1 (
    echo          Some optional components could not be installed.
    echo          The core application will still work fine.
)

:: Create the launcher batch file
echo [4/4] Creating launcher...
(
echo @echo off
echo cd /d "%%~dp0"
echo if exist ".venv\Scripts\activate.bat" (
echo     call ".venv\Scripts\activate.bat"
echo     start "" pythonw -m llm_buddy
echo ^) else (
echo     start "" python -m llm_buddy
echo ^)
) > "%INSTALL_DIR%LLM Buddy.bat"

:: Create Desktop shortcut via temp VBScript
:: Use Shell.Application to find the real Desktop (works with OneDrive too)
set "TARGET=%INSTALL_DIR%LLM Buddy.bat"
echo Creating desktop shortcut...
set "VBSTMP=%TEMP%\make_shortcut.vbs"
> "%VBSTMP%" echo Set shell = CreateObject("Shell.Application")
>>"%VBSTMP%" echo desktopPath = shell.Namespace(0).Self.Path
>>"%VBSTMP%" echo Set ws = CreateObject("WScript.Shell")
>>"%VBSTMP%" echo Set sc = ws.CreateShortcut(desktopPath ^& "\LLM Buddy.lnk")
>>"%VBSTMP%" echo sc.TargetPath = "%TARGET%"
>>"%VBSTMP%" echo sc.WorkingDirectory = "%INSTALL_DIR%"
>>"%VBSTMP%" echo sc.Description = "LLM Buddy - Prompt Recording and Management"
>>"%VBSTMP%" echo sc.IconLocation = "%INSTALL_DIR%icon.ico"
>>"%VBSTMP%" echo sc.Save
>>"%VBSTMP%" echo WScript.Echo desktopPath ^& "\LLM Buddy.lnk"
for /f "delims=" %%p in ('cscript //nologo "%VBSTMP%" 2^>nul') do set "SHORTCUT=%%p"
del "%VBSTMP%" 2>nul

if defined SHORTCUT (
    if exist "%SHORTCUT%" (
        echo Desktop shortcut created!
    ) else (
        echo Could not create desktop shortcut, but you can double-click:
        echo   %TARGET%
    )
) else (
    echo Could not create desktop shortcut, but you can double-click:
    echo   %TARGET%
)

echo.
echo ================================================
echo   Installation Complete!
echo ================================================
echo.
echo   To launch LLM Buddy:
echo     - Double-click "LLM Buddy" on your Desktop
echo     - Or double-click "LLM Buddy.bat" in this folder
echo.

:: Ask about Claude Desktop configuration
set /p CLAUDE="Configure Claude Desktop MCP integration? [y/n]: "
if /i "%CLAUDE%"=="y" (
    llm-buddy configure
)

:: Launch the app
echo.
echo Launching LLM Buddy...
start "" "%INSTALL_DIR%.venv\Scripts\pythonw.exe" -m llm_buddy
echo.
echo You can close this window now.
pause
