#!/usr/bin/env bash
# Start CSV Plot Studio on Linux: ./run_linux.sh [optional: file.csv]
cd "$(dirname "$0")" || exit 1

SYSTEM_PYTHON="${PYTHON:-python3}"
if ! command -v "$SYSTEM_PYTHON" >/dev/null 2>&1; then
    echo "Python 3 is not installed. Install Python 3 and Tk support, then run this file again."
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Preparing CSV Plot Studio's private environment..."
    "$SYSTEM_PYTHON" -m venv .venv || {
        echo "Python's virtual-environment support is missing. On Ubuntu or Mint, run: sudo apt install python3-venv"
        exit 1
    }
fi
PY=".venv/bin/python"

if ! "$PY" -c "import tkinter" 2>/dev/null; then
    if [ "$(id -u)" -eq 0 ] && command -v apt-get >/dev/null 2>&1; then
        apt-get install -y python3-tk || exit 1
    else
        echo "The window toolkit is missing. On Ubuntu or Mint, run: sudo apt install python3-tk"
        exit 1
    fi
fi

exec "$PY" main.py "$@"
