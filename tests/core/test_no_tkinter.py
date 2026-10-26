"""plotstudio.core must work without tkinter (UI and logic stay apart)."""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "plotstudio" / "core"


def test_no_tkinter_import_statement():
    for path in CORE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            assert not any(n.split(".")[0] in ("tkinter", "_tkinter") for n in names), f"{path} imports tkinter"


def test_core_imports_with_tkinter_blocked():
    code = ("import sys; sys.modules['tkinter'] = None; sys.modules['_tkinter'] = None\n"
            f"sys.path.insert(0, {str(ROOT)!r})\n"
            "import pkgutil, importlib, plotstudio.core as core\n"
            "for m in pkgutil.walk_packages(core.__path__, 'plotstudio.core.'):\n"
            "    if not m.name.endswith('__main__'):\n"
            "        importlib.import_module(m.name)\n"
            "print('ok')")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr[-800:]
