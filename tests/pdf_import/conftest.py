"""The PDF fixtures (pdf_fixtures.py) are built once per test run, into a temporary folder."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(scope="session")
def pdfs(tmp_path_factory):
    pytest.importorskip("reportlab")
    pytest.importorskip("pypdfium2")
    import pdf_fixtures

    return pdf_fixtures.build(tmp_path_factory.mktemp("pdfs"))
