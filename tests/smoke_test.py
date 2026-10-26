"""Draw every graph type with the sample CSVs and check that the exported
scripts also run on their own.

    python tests/smoke_test.py            # quick check, prints OK / FAIL per graph
    python tests/smoke_test.py --save     # also saves every plot as PNG in tests/output/
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from plotstudio.data import RowSettings, load_csv  # noqa: E402
from plotstudio.engine import LabelSettings, StyleSettings, make_plot  # noqa: E402
from plotstudio.graphs import GRAPHS, suggest  # noqa: E402

SAMPLES = ROOT / "samples"
SAMPLE_FOR = {
    "line": "training_log.csv", "area": "training_log.csv",
    "confusion": "model_predictions.csv", "roc": "model_predictions.csv",
    "images": "digits_8x8.csv",
    "contour": "surface_xyz.csv", "surface3d": "surface_xyz.csv", "scatter3d": "surface_xyz.csv",
}


def main() -> int:
    save = "--save" in sys.argv
    out_dir = ROOT / "tests" / "output"
    if save:
        out_dir.mkdir(parents=True, exist_ok=True)
    datasets = {}
    failures = 0
    for graph in GRAPHS:
        name = SAMPLE_FOR.get(graph.id, "airline_demo.csv")
        ds = datasets.get(name) or datasets.setdefault(name, load_csv(SAMPLES / name))
        sel = suggest(graph, ds)
        started = time.perf_counter()
        try:
            result = make_plot(graph, ds, sel, {}, RowSettings(), StyleSettings(), LabelSettings())
            if save:
                result.figure.savefig(out_dir / f"{graph.id}.png", dpi=80)
            script_ok, err = run_script(result.script)
            status = "OK  " if script_ok else "FAIL"
            if not script_ok:
                failures += 1
            print(f"{status} {graph.id:<12} {time.perf_counter() - started:5.2f}s  {name}"
                  + ("" if script_ok else f"\n     exported script failed:\n{err}"))
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {graph.id:<12} {type(exc).__name__}: {exc}")
    print(f"\n{len(GRAPHS) - failures}/{len(GRAPHS)} graph types passed.")
    return 1 if failures else 0


def run_script(script: str):
    """Run an exported script in a fresh Python process (no window)."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(script)
        path = fh.name
    try:
        env = {**os.environ, "MPLBACKEND": "Agg", "PYTHONWARNINGS": "ignore"}
        proc = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=180, env=env)
        return proc.returncode == 0, proc.stderr[-2000:]
    finally:
        os.unlink(path)


if __name__ == "__main__":
    sys.exit(main())
