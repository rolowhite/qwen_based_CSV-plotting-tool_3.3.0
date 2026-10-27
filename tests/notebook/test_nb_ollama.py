"""The Ollama client against a fake server: models by capability, streamed chats, clear errors and Stop."""
import threading
import time

import pytest

from fake_ollama import FakeOllama
from plotstudio.core.notebook import ollama

MODELS = {"llama3:8b": ["completion", "tools"], "qwen3-vl:8b": ["completion", "vision", "tools", "thinking"],
          "qwen2.5vl:7b": ["completion", "vision"]}


def test_models_and_pick_by_capability():
    with FakeOllama(MODELS) as fake:
        found = ollama.models(fake.url)
    assert [name for name, _ in found] == list(MODELS)
    assert ollama.pick(found, "vision") == "qwen3-vl:8b"
    assert ollama.pick(found, "vision", wanted="qwen2.5vl:7b") == "qwen2.5vl:7b"
    assert ollama.pick(found, "vision", wanted="llama3:8b") == "qwen3-vl:8b"      # can't see: not used
    assert ollama.pick(found, "audio") is None


def test_chat_streams_the_reply_and_sends_the_options():
    with FakeOllama(MODELS, replies=['{"problems": []}']) as fake:
        text = ollama.Chat(fake.url).text("qwen3-vl:8b", [{"role": "user", "content": "hi"}],
                                          format={"type": "object"}, think=False)
        sent = fake.requests[0]
    assert text == '{"problems": []}'
    assert sent["stream"] is True and sent["options"] == {"temperature": 0}
    assert sent["format"] == {"type": "object"} and sent["think"] is False


def test_not_running_and_missing_model_say_what_to_do():
    with FakeOllama(MODELS) as fake:
        url = fake.url
        with pytest.raises(ollama.OllamaError, match="isn't installed.*ollama pull nope"):
            ollama.Chat(url).text("nope", [])
    with pytest.raises(ollama.OllamaError, match="isn't running"):      # the server is gone now
        ollama.models(url)
    with pytest.raises(ollama.OllamaError, match="not an Ollama address"):
        ollama.models("ftp://x")


def test_a_server_error_is_reported():
    with FakeOllama(MODELS, replies=[{"status": 500, "error": "out of memory"}]) as fake:
        with pytest.raises(ollama.OllamaError, match="out of memory"):
            ollama.Chat(fake.url).text("qwen3-vl:8b", [])


def test_cancel_ends_a_slow_reply():
    with FakeOllama(MODELS, replies=[{"text": "x" * 400, "delay": 0.5}]) as fake:
        chat = ollama.Chat(fake.url)
        threading.Timer(0.3, chat.cancel).start()
        start = time.time()
        with pytest.raises(ollama.Cancelled):
            chat.text("qwen3-vl:8b", [])
    assert time.time() - start < 1.5


def test_images_are_scaled_into_range():
    import base64
    import io
    from PIL import Image

    def size(img):
        return Image.open(io.BytesIO(base64.b64decode(ollama.prepare_image(img)))).size

    assert size(Image.new("RGB", (400, 100))) == (1200, 300)
    assert size(Image.new("RGBA", (5000, 1000))) == (2000, 400)
    assert size(Image.new("L", (1500, 900))) == (1500, 900)
