@echo off
setlocal
rem Double-click this file to start CSV Plot Studio. The first start sets everything up by itself:
rem Python (if needed), the app's packages in a private environment, and then, inside the app, the picture
rem reader (Ollama and its model) and Tesseract. Later starts take a few seconds.
cd /d "%~dp0"

set "PY="
set "OWN_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
where py >nul 2>&1 && set "PY=py"
if not defined PY where python >nul 2>&1 && set "PY=python"
if defined PY (
    "%PY%" -c "import sys, tkinter; raise SystemExit(0 if sys.version_info >= (3,9) else 1)" >nul 2>&1
    if errorlevel 1 set "PY="
)
if not defined PY if exist "%OWN_PY%" set "PY=%OWN_PY%"

if not defined PY (
    echo Setting up Python for CSV Plot Studio. This is only needed once...
    where winget >nul 2>&1
    if not errorlevel 1 winget install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
    if not exist "%OWN_PY%" (
        echo Downloading Python from python.org...
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; $f=Join-Path $env:TEMP 'python-3.12.10-amd64.exe'; Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $f; $s=Get-AuthenticodeSignature -LiteralPath $f; if ($s.Status -ne 'Valid' -or -not $s.SignerCertificate.Subject.StartsWith('CN=Python Software Foundation')) { Remove-Item $f; throw 'The downloaded Python installer is not signed by the Python Software Foundation, so it was not run.' }; $p=Start-Process -FilePath $f -ArgumentList '/quiet','InstallAllUsers=0','PrependPath=0','Include_test=0' -Wait -PassThru; Remove-Item $f; exit $p.ExitCode"
    )
    if not exist "%OWN_PY%" (
        echo Python could not be installed automatically. Check the internet connection and try again,
        echo or install Python 3.12 from python.org, then double-click this file again.
        pause
        exit /b 1
    )
    set "PY=%OWN_PY%"
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
