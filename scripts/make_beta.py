"""Build the beta zip for users: only what the app needs to run, plus a short READ ME FIRST.

    python scripts/make_beta.py          -> dist/CSV-Plot-Studio-<version>-beta.zip

Left out: tests, docs, scripts, .git, .venv, caches and editor folders. The zip is checked after it is written.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plotstudio import __version__  # noqa: E402

FILES = ["main.py", "plot_recommender.py", "requirements.txt", "requirements-import.txt", "run_windows.bat",
         "run_linux.sh", "install_linux_shortcut.sh", "README.md"]
FOLDERS = ["plotstudio", "samples"]
SKIP = {"__pycache__", ".pytest_cache", ".mypy_cache"}
NEEDED = ["main.py", "run_windows.bat", "plotstudio/app.py", "plotstudio/notebook_page.py",
          "plotstudio/assets/notebook/Walpole_All_Chapters_Solutions.md",
          "plotstudio/assets/notebook/Lind_Chapters_8_to_12_Solutions.md", "plotstudio/assets/katex/katex.min.js",
          "READ ME FIRST.txt"]

READ_ME = f"""CSV Plot Studio {__version__} (beta)

1. Extract this zip to a folder (right-click > Extract All). Don't start it from inside the zip.
2. Double-click run_windows.bat.

The first start sets everything up by itself. It needs an internet connection and about 10 GB of free
disk space, and can take 15-45 minutes depending on your connection:
  - Python 3.12, if this PC doesn't have it (from python.org, about 26 MB)
  - the app's Python packages (about 400 MB)
  - Ollama, the local engine that reads pictures of problems (about 1.6 GB)
  - the reading model, qwen3-vl:8b-instruct (about 5 GB)
  - Tesseract OCR, for importing tables from pictures (Windows may ask once for permission)

You can use the app while the picture reader downloads: the Notebook shows the progress, and typed
problems work right away. Later starts take a few seconds and need no internet.
Everything runs on this computer; nothing is sent anywhere.

Problems or questions: send the file .csv_plot_studio.log from your user folder (C:\\Users\\<you>).
"""


def files():
    for name in FILES:
        yield ROOT / name
    for folder in FOLDERS:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and not SKIP & set(path.relative_to(ROOT).parts) and path.suffix != ".pyc":
                yield path


def main():
    out = ROOT / "dist" / f"CSV-Plot-Studio-{__version__}-beta.zip"
    out.parent.mkdir(exist_ok=True)
    top = f"CSV Plot Studio {__version__} beta"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files():
            zf.write(path, f"{top}/{path.relative_to(ROOT).as_posix()}")
        zf.writestr(f"{top}/READ ME FIRST.txt", READ_ME.replace("\n", "\r\n"))
    with zipfile.ZipFile(out) as zf:                        # self-check: what the app needs, nothing it doesn't
        names = {n.split("/", 1)[1] for n in zf.namelist()}
        missing = [n for n in NEEDED if n not in names]
        unwanted = [n for n in names if n.split("/")[0] in {"tests", ".git", ".venv", "docs", "scripts", ".claude"}
                    or "__pycache__" in n or n.endswith(".pyc")]
        assert not missing and not unwanted, (missing, unwanted[:10])
    print(f"{out}  {out.stat().st_size / 1e6:.1f} MB, {len(names)} files")


if __name__ == "__main__":
    main()
