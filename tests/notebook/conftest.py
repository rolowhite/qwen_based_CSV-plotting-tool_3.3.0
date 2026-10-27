"""Notebook tests: Gemini models one test found busy or out of quota mustn't be skipped in the next test."""
import pytest

from plotstudio.core.notebook import solver


@pytest.fixture(autouse=True)
def _forget_busy_gemini_models():
    solver.GeminiBackend.busy_until.clear()
    yield
    solver.GeminiBackend.busy_until.clear()
