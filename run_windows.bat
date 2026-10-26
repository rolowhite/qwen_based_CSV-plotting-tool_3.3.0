@echo off
setlocal
rem Double-click this file to start CSV Plot Studio. The private environment
rem keeps automatic package setup separate from any other Python installation.
cd /d "%~dp0"

set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY where python >nul 2>&1 && set "PY=python"
if defined PY (
    "%PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,9) else 1)" >nul 2>&1
    if errorlevel 1 set "PY="
)

if not defined PY (
    where winget >nul 2>&1
    if errorlevel 1 (
        echo Python is not installed, and Windows Package Manager is unavailable.
        echo Ask your administrator to install Python 3.12, then double-click this file again.
        pause
        exit /b 1
    )
    echo Setting up Python for CSV Plot Studio. This is only needed once...
    winget install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo Python could not be installed automatically. Ask your administrator for help.
        pause
        exit /b 1
    )
    set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    if not exist "%PY%" (
        echo Python was installed, but its launcher could not be located. Restart Windows and try again.
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Preparing CSV Plot Studio's private environment...
    "%PY%" -m venv .venv
    if errorlevel 1 (
        echo The Python environment could not be prepared. Check that Python includes venv and Tkinter.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" main.py %*
if errorlevel 1 pause
endlocal
