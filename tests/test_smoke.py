"""pytest entry for the smoke test (every graph type draws, every exported script runs)."""
import pytest

import smoke_test


@pytest.mark.slow
def test_every_graph_and_exported_script():
    assert smoke_test.main() == 0
