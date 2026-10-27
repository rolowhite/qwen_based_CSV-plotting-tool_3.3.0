"""The picture reader sets itself up: Ollama installed and started when missing, the model downloaded with
progress, a downloaded installer run only when Ollama signed it, and a clear stop when the disk is full.
Nothing here installs anything for real (the installer, winget and the start are replaced)."""
import sys
from pathlib import Path

import pytest

from fake_ollama import FakeOllama
from plotstudio.core.notebook import ollama, setup

MODEL = ollama.READER_MODEL


def _progress():
    seen = []
    return seen, lambda text, part: seen.append((text, part))


def test_ready_already_means_nothing_to_do():
    with FakeOllama({MODEL: ["completion", "vision"]}) as fake:
        seen, progress = _progress()
        assert setup.ensure(fake.url, progress) == MODEL
        assert fake.pulls == [] and seen == [("The picture reader is ready.", 1.0)]


def test_a_missing_model_is_downloaded_with_progress():
    with FakeOllama({"other": ["completion"]}) as fake:
        seen, progress = _progress()
        setup.ensure(fake.url, progress)
        assert fake.pulls == [MODEL] and MODEL in fake.models
    parts = [p for _, p in seen if p is not None]
    assert parts[0] == 0.0 and 1 / 3 in parts and parts[-1] == 1.0 and parts == sorted(parts)    # only goes up
    assert any("1.0 of 3.0 GB" in text for text, _ in seen)


def test_missing_ollama_is_installed_then_started(monkeypatch, tmp_path):
    exe = tmp_path / "ollama.exe"
    calls = []
    with FakeOllama({MODEL: ["completion", "vision"]}) as fake:
        up = {"now": False}
        monkeypatch.setattr(setup, "running", lambda url: up["now"])
        monkeypatch.setattr(setup, "find_ollama", lambda: None)
        monkeypatch.setattr(setup, "install", lambda progress, cancelled: calls.append("install") or exe)

        def start(url, path, progress):
            calls.append(("start", path))
            up["now"] = True
        monkeypatch.setattr(setup, "start", start)
        assert setup.ensure(fake.url) == MODEL
    assert calls == ["install", ("start", exe)]


def test_a_downloaded_installer_not_signed_by_ollama_is_never_run(monkeypatch):
    ran = []
    monkeypatch.setattr(setup.shutil, "which", lambda name: None)          # no winget: download instead
    monkeypatch.setattr(setup, "_download", lambda url, target, progress, cancelled: target.write_bytes(b"MZ"))
    monkeypatch.setattr(setup, "_signed_by_ollama", lambda path: False)
    monkeypatch.setattr(setup.subprocess, "run", lambda *a, **k: ran.append(a))
    with pytest.raises(ollama.OllamaError, match="isn't signed by Ollama"):
        setup.install(lambda text, part: None)
    assert ran == []


@pytest.mark.skipif(sys.platform != "win32", reason="Windows code signatures")
def test_the_signature_check_tells_ollama_from_anything_else(tmp_path):
    unsigned = tmp_path / "x.exe"
    unsigned.write_bytes(b"MZ not a program")
    assert setup._signed_by_ollama(unsigned) is False
    assert setup._signed_by_ollama(Path(sys.executable)) is False                # signed, but not by Ollama
    installed = setup.find_ollama()
    if installed is not None:
        assert setup._signed_by_ollama(installed) is True


def test_too_little_disk_space_stops_before_downloading(monkeypatch):
    monkeypatch.setattr(setup.shutil, "disk_usage", lambda path: type("U", (), {"free": 2e9})())
    with FakeOllama({}) as fake:
        with pytest.raises(ollama.OllamaError, match="free disk space"):
            setup.ensure(fake.url)
        assert fake.pulls == []


def test_switched_off_for_the_tests_and_off_windows(monkeypatch):
    assert setup.enabled() is False                                  # conftest sets CSV_PLOT_STUDIO_NO_SETUP
    monkeypatch.delenv("CSV_PLOT_STUDIO_NO_SETUP")
    assert setup.enabled() is (sys.platform == "win32")
