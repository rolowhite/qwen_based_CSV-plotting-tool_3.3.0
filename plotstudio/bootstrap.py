"""Install missing runtime dependencies before the graphical app is imported.

This module intentionally uses only Python's standard library so it can run
before pandas, matplotlib, OpenCV, or the other application packages exist.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "requirements.txt"
IMPORT_REQUIREMENTS = ROOT / "requirements-import.txt"
REQUIRED_MODULES = {
    "pandas": "pandas",
    "numpy": "numpy",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "scikit-learn": "sklearn",
    "Pillow": "PIL",
    "markdown-it-py": "markdown_it",
    "mdit-py-plugins": "mdit_py_plugins",
}
IMPORT_MODULES = {          # PDF and image table import (optional; the app tells how to add them)
    "pypdfium2": "pypdfium2",
    "camelot-py": "camelot",
    "pypdf": "pypdf",
    "pytesseract": "pytesseract",
    "opencv-python-headless": "cv2",
}


def missing_requirements(modules=None) -> list[str]:
    """Return pip requirements whose import modules aren't available yet."""
    missing = []
    for package, module in (modules or REQUIRED_MODULES).items():
        try:
            available = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            available = False
        if not available:
            missing.append(package)
    return missing


def _private_environment() -> bool:
    """True inside a virtual environment (the launchers make .venv for the app); elsewhere we ask first."""
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _allowed(question: str) -> bool:
    if _private_environment():
        return True
    if not sys.stdin or not sys.stdin.isatty():
        return False
    try:
        return input(question + " [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _install_python_requirements(requirements=REQUIREMENTS, modules=None) -> bool:
    if not requirements.is_file():
        print(f"Setup file not found: {requirements}", file=sys.stderr)
        return False
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        try:
            subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"Python's package installer couldn't be started: {exc}", file=sys.stderr)
            return False

    print("First start (or a new feature): downloading and setting up the required components. "
          "This can take a few minutes…", flush=True)
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements)
    ])
    if result.returncode:
        print("Automatic setup couldn't finish. Check your internet connection and run the app again. "
              "If this computer uses a managed network, its administrator may need to allow Python package downloads.",
              file=sys.stderr)
        return False
    return not missing_requirements(modules)


def _tesseract_candidates() -> list[Path]:
    candidates = []
    if sys.platform == "win32":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates.extend([
            Path(program_files) / "Tesseract-OCR" / "tesseract.exe",
            Path(local_app_data) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        ])
    return candidates


def _add_tesseract_to_path() -> bool:
    found = shutil.which("tesseract")
    executable = Path(found) if found else next((path for path in _tesseract_candidates() if path.is_file()), None)
    if executable is None:
        return False
    os.environ["PATH"] = str(executable.parent) + os.pathsep + os.environ.get("PATH", "")
    return True


def install_tesseract() -> str:
    """Install the Tesseract OCR program with winget on Windows if it's missing (its installer may show Windows'
    administrator prompt). Meant for a background thread after the window opens; returns what happened."""
    if _add_tesseract_to_path():
        return "Tesseract OCR is installed."
    if sys.platform != "win32" or os.environ.get("CSV_PLOT_STUDIO_NO_SETUP") or not shutil.which("winget"):
        return "Tesseract OCR isn't installed (automatic setup is Windows-only and needs winget)."
    out = subprocess.run(["winget", "install", "--id", "UB-Mannheim.TesseractOCR", "--exact", "--silent",
                          "--accept-package-agreements", "--accept-source-agreements"],
                         capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if _add_tesseract_to_path():
        return "Tesseract OCR was installed."
    return f"Tesseract OCR couldn't be installed (winget exit {out.returncode}): {(out.stdout or out.stderr)[-300:]}"


def prepare_runtime() -> bool:
    """Install missing Python packages (in the app's own environment, or after asking), and say how to add the
    OCR program. On Windows the app installs Tesseract and Ollama itself after its window opens
    (install_tesseract, core/notebook/setup.py)."""
    missing = missing_requirements()
    if missing:
        if not _allowed(f"CSV Plot Studio needs {', '.join(missing)}. Install them now with pip?"):
            print(f"Missing packages: {', '.join(missing)}. Install them with:\n"
                  f"    {sys.executable} -m pip install -r {REQUIREMENTS}", file=sys.stderr)
            return False
        if not _install_python_requirements():
            return False
    extra = missing_requirements(IMPORT_MODULES)
    if extra and sys.version_info >= (3, 10) and _allowed(
            "Add PDF and image table import (" + ", ".join(extra) + ")?"):
        _install_python_requirements(IMPORT_REQUIREMENTS, IMPORT_MODULES)       # optional: plotting works without
    if not _add_tesseract_to_path() and sys.platform != "win32":       # Windows: installed in the background
        print("Tesseract OCR isn't installed: CSV files and text PDFs work; screenshots and scanned PDFs need it "
              "(Windows: winget install UB-Mannheim.TesseractOCR, Linux: sudo apt install tesseract-ocr, "
              "macOS: brew install tesseract).", file=sys.stderr)
    return True
