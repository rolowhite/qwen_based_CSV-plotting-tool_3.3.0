"""Set up the picture reader by itself on Windows: Ollama and its vision model, with no questions.

ensure() installs Ollama when it is missing (with winget, or else the installer from ollama.com, run only when
its code signature is Ollama Inc.'s), starts it, and downloads ollama.READER_MODEL (about 6 GB) with progress.
Standard library only; it runs in a worker thread and reports through progress(text, fraction or None).
Set CSV_PLOT_STUDIO_NO_SETUP=1 to switch it off (the test suite does).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from . import ollama

INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"
SIGNER = "CN=Ollama Inc."
MODEL_GB = 6.5            # free space the model needs (5.0 GB of files plus room to unpack)
START_TIMEOUT = 120       # s for a freshly started Ollama to answer
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

Progress = Callable[[str, Optional[float]], None]


def enabled() -> bool:
    return sys.platform == "win32" and not os.environ.get("CSV_PLOT_STUDIO_NO_SETUP")


def find_ollama() -> Optional[Path]:
    found = shutil.which("ollama")
    candidates = ([Path(found)] if found else []) + [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"]
    return next((p for p in candidates if p.is_file()), None)


def running(url: str) -> bool:
    try:
        ollama._request(url, "GET", "/api/version", timeout=3)
        return True
    except ollama.OllamaError:
        return False


def models_folder() -> Path:
    return Path(os.environ.get("OLLAMA_MODELS") or Path.home() / ".ollama" / "models")


def _signed_by_ollama(path: Path) -> bool:
    """Windows' own check of the file's code signature (PowerShell's Get-AuthenticodeSignature)."""
    script = (f"$s = Get-AuthenticodeSignature -LiteralPath '{path}'; "
              "if ($s.Status -eq 'Valid') { $s.SignerCertificate.Subject }")
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True,
                         text=True, timeout=60, creationflags=NO_WINDOW)
    return out.stdout.strip().startswith(SIGNER)


def _download(url: str, target: Path, progress: Progress, cancelled: Callable[[], bool]):
    with urllib.request.urlopen(url, timeout=60) as response, target.open("wb") as fh:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            if cancelled():
                raise ollama.Cancelled()
            block = response.read(1 << 20)
            if not block:
                break
            fh.write(block)
            done += len(block)
            progress(f"Downloading Ollama: {done / 1e9:.1f} of {total / 1e9:.1f} GB", done / total if total else None)


def install(progress: Progress, cancelled: Callable[[], bool] = lambda: False) -> Path:
    """Install Ollama for this Windows user (no administrator rights needed) and return ollama.exe."""
    notes = []
    if shutil.which("winget"):
        progress("Installing Ollama, the local engine that reads pictures…", None)
        out = subprocess.run(["winget", "install", "--id", "Ollama.Ollama", "--exact", "--silent",
                              "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"],
                             capture_output=True, text=True, creationflags=NO_WINDOW)
        if find_ollama():
            return find_ollama()
        notes.append(f"winget: {(out.stdout or out.stderr).strip()[-300:]}")
    with tempfile.TemporaryDirectory() as tmp:
        setup = Path(tmp) / "OllamaSetup.exe"
        try:
            _download(INSTALLER_URL, setup, progress, cancelled)
        except OSError as exc:
            raise ollama.OllamaError(f"Ollama couldn't be downloaded ({exc}). Check the internet connection and "
                                     "try again.") from exc
        if not _signed_by_ollama(setup):
            raise ollama.OllamaError("The downloaded Ollama installer isn't signed by Ollama Inc., so it was not run.")
        progress("Installing Ollama…", None)
        subprocess.run([str(setup), "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"], creationflags=NO_WINDOW)
    exe = find_ollama()
    if exe is None:
        raise ollama.OllamaError("Ollama couldn't be installed. " + " ".join(notes) +
                                 " You can install it from https://ollama.com instead.")
    return exe


def start(url: str, exe: Path, progress: Progress):
    """Start Ollama (its tray app, which runs the server) and wait until it answers."""
    progress("Starting Ollama…", None)
    app = exe.with_name("ollama app.exe")
    command = [str(app)] if app.is_file() else [str(exe), "serve"]
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(command, creationflags=flags, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True)
    end = time.time() + START_TIMEOUT
    while time.time() < end:
        if running(url):
            return
        time.sleep(1)
    raise ollama.OllamaError("Ollama was started but doesn't answer yet. Restart the computer and open the app again.")


def pull(chat: "ollama.Chat", model: str, progress: Progress):
    """Download `model`, reporting the bytes of all its parts together."""
    folder = models_folder()
    while not folder.exists() and folder != folder.parent:      # it may not exist yet: measure where it will be
        folder = folder.parent
    free = shutil.disk_usage(folder).free / 1e9                 # follows a junction to another drive
    if free < MODEL_GB:
        raise ollama.OllamaError(f"The reading model needs about {MODEL_GB:.0f} GB of free disk space; the drive "
                                 f"of {folder} has {free:.1f} GB. Free some space and try again.")
    parts = {}
    progress("Downloading the reading model…", 0.0)
    for chunk in chat.pull(model):
        if chunk.get("digest") and chunk.get("total"):
            parts[chunk["digest"]] = (int(chunk.get("completed") or 0), int(chunk["total"]))
        done, total = sum(c for c, _ in parts.values()), sum(t for _, t in parts.values())
        if total:
            progress(f"Downloading the reading model: {done / 1e9:.1f} of {total / 1e9:.1f} GB", done / total)
        elif chunk.get("status"):
            progress(f"Preparing the reading model ({chunk['status']})…", None)


def ensure(url: str = ollama.DEFAULT_URL, progress: Progress = lambda text, fraction: None,
           chat: Optional["ollama.Chat"] = None) -> str:
    """Make the picture reader ready: Ollama installed and running, ollama.READER_MODEL downloaded. Returns the
    model's name. Cancel with chat.cancel()."""
    chat = chat or ollama.Chat(url, timeout=600)
    if not running(url):
        exe = find_ollama() or install(progress, lambda: chat.cancelled)
        start(url, exe, progress)
    if ollama.READER_MODEL not in {name for name, _ in ollama.models(url)}:
        pull(chat, ollama.READER_MODEL, progress)
    progress("The picture reader is ready.", 1.0)
    return ollama.READER_MODEL
