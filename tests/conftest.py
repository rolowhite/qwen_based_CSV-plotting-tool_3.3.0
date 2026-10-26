"""Shared pytest setup: imports from the repo, off-screen drawing, a temporary log file,
seaborn's Titanic and tips data, and a bridge for the older script-style tests."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CSV_PLOT_STUDIO_LOG", str(Path(tempfile.gettempdir()) / "csv_plot_studio_tests.log"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def _script_checks(request):
    """The older test files collect problems in a module-level `failures` list (so they also run
    as plain scripts); under pytest any new entry fails the test that added it."""
    failures = getattr(request.module, "failures", None)
    before = len(failures) if isinstance(failures, list) else None
    yield
    if before is not None and len(failures) > before:
        pytest.fail("; ".join(failures[before:]))


def _seaborn_data(name: str):
    sns = pytest.importorskip("seaborn")
    try:
        return sns.load_dataset(name)
    except Exception as exc:  # noqa: BLE001 - offline machines skip the integration tests
        pytest.skip(f"seaborn could not load '{name}' (offline?): {exc}")


@pytest.fixture(scope="session")
def titanic():
    """seaborn's Titanic: 891 rows, target 'survived', 'alive' leaks it, 'deck' 77% missing."""
    return _seaborn_data("titanic")


KAGGLE_TITANIC = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"


@pytest.fixture(scope="session")
def kaggle_titanic():
    """Kaggle's Titanic train.csv (891 rows, with Name, Ticket and Cabin), downloaded once into
    tests/.data (or $CSV_PLOT_STUDIO_TEST_DATA). Skipped when offline."""
    folder = Path(os.environ.get("CSV_PLOT_STUDIO_TEST_DATA", ROOT / "tests" / ".data"))
    path = folder / "kaggle_titanic_train.csv"
    if not path.exists():
        import urllib.request
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(KAGGLE_TITANIC, timeout=30) as response:
                data = response.read()
            if not data.startswith(b"PassengerId"):
                raise ValueError("unexpected content")
            path.write_bytes(data)
        except Exception as exc:  # noqa: BLE001 - offline machines skip the integration test
            pytest.skip(f"Kaggle's Titanic could not be downloaded (offline?): {exc}")
    return path


@pytest.fixture(scope="session")
def tips():
    """seaborn's tips: 244 restaurant bills, a clean file (target 'tip')."""
    return _seaborn_data("tips")
