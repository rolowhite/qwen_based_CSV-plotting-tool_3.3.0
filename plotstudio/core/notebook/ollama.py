"""A small client for a local Ollama server (http://localhost:11434), standard library only.

Models are chosen by what /api/show says they can do ("vision", "tools", "thinking"), never by name. A chat
streams its reply as JSON lines; `Chat.cancel()` closes the connection from another thread, which ends a
read that is blocked waiting for the model.
"""
from __future__ import annotations

import base64
import http.client
import io
import json
import socket
import threading
from typing import Iterator, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

DEFAULT_URL = "http://localhost:11434"
LONG_SIDE_MAX = 2000      # px: bigger pictures only cost time
LONG_SIDE_MIN = 1200      # px: small screenshots are scaled up so small print stays readable
PULL_HINT = "ollama pull qwen3-vl:8b"


class OllamaError(RuntimeError):
    """Ollama isn't running, the model is missing, or the reply was not what we asked for."""


class Cancelled(Exception):
    """The user pressed Stop."""


def _connection(url: str, timeout: float) -> http.client.HTTPConnection:
    parts = urlsplit(url if "//" in url else f"http://{url}")
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise OllamaError(f"'{url}' is not an Ollama address (for example {DEFAULT_URL}).")
    kind = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    return kind(parts.hostname, parts.port or (443 if parts.scheme == "https" else 11434), timeout=timeout)


def _not_running(url: str, exc: BaseException) -> OllamaError:
    return OllamaError(f"Ollama isn't running at {url} ({exc}). Start the Ollama app, or install it from "
                       f"https://ollama.com and run: {PULL_HINT}")


def _error_text(body: bytes) -> str:
    try:
        return str(json.loads(body).get("error") or body[:200].decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return body[:200].decode("utf-8", "replace")


def _request(url: str, method: str, path: str, payload=None, timeout: float = 10.0) -> dict:
    conn = _connection(url, timeout)
    try:
        conn.request(method, path, body=None if payload is None else json.dumps(payload),
                     headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        body = response.read()
    except (OSError, http.client.HTTPException) as exc:
        raise _not_running(url, exc) from exc
    finally:
        conn.close()
    if response.status != 200:
        raise OllamaError(f"Ollama answered {response.status} to {path}: {_error_text(body)}")
    try:
        return json.loads(body)
    except ValueError as exc:
        raise OllamaError(f"Ollama sent a reply to {path} that isn't JSON.") from exc


def models(url: str = DEFAULT_URL) -> List[Tuple[str, Tuple[str, ...]]]:
    """Every installed model and its capabilities, in Ollama's order (most recently changed first)."""
    tags = _request(url, "GET", "/api/tags")
    out = []
    for entry in tags.get("models") or []:
        name = (entry.get("model") or entry.get("name")) if isinstance(entry, dict) else None
        if not isinstance(name, str):
            continue
        caps = _request(url, "POST", "/api/show", {"model": name}).get("capabilities") or []
        out.append((name, tuple(c for c in caps if isinstance(c, str))))
    return out


def pick(found: Sequence[Tuple[str, Sequence[str]]], need: str, wanted: str = "") -> Optional[str]:
    """The `wanted` model if it is installed and can do `need`, otherwise the first one that can."""
    able = [name for name, caps in found if need in caps]
    return wanted if wanted in able else (able[0] if able else None)


def sent_size(long_side: int) -> int:
    """The long side, in pixels, a picture is sent with."""
    return min(max(long_side, LONG_SIDE_MIN), LONG_SIDE_MAX)


def prepare_image(image, long_side: Optional[int] = None) -> str:
    """A PIL image as base64 PNG, its long side scaled to `long_side` (default: into LONG_SIDE_MIN..MAX)."""
    from PIL import Image

    image = image.convert("RGB")
    k = (long_side or sent_size(max(image.size))) / max(image.size)
    if k != 1.0:
        image = image.resize((max(1, round(image.width * k)), max(1, round(image.height * k))), Image.LANCZOS)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class Chat:
    """One streamed /api/chat call at a time; `cancel()` may be called from any thread."""

    def __init__(self, url: str = DEFAULT_URL, timeout: float = 300.0):
        self.url = url
        self.timeout = timeout
        self._conn = None
        self._cancelled = threading.Event()
        self._lock = threading.Lock()

    def cancel(self):
        self._cancelled.set()
        with self._lock:
            conn = self._conn
        if conn is not None and conn.sock is not None:
            try:
                conn.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass        # already closed: the reading thread sees the cancel flag either way

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def stream(self, model: str, messages: list, format=None, think: Optional[bool] = None,
               options: Optional[dict] = None) -> Iterator[dict]:
        """The reply's JSON chunks ({"message": {"content": ...}, "done": ...}) as they arrive."""
        if self.cancelled:
            raise Cancelled()
        payload = {"model": model, "messages": messages, "stream": True,
                   "options": options if options is not None else {"temperature": 0}}
        if format is not None:
            payload["format"] = format
        if think is not None:
            payload["think"] = think
        conn = _connection(self.url, self.timeout)
        with self._lock:
            self._conn = conn
        try:
            try:
                conn.request("POST", "/api/chat", body=json.dumps(payload), headers={"Content-Type": "application/json"})
                response = conn.getresponse()
                if response.status != 200:
                    text = _error_text(response.read())
                    if response.status == 404:
                        raise OllamaError(f"The model {model} isn't installed in Ollama ({text}). "
                                          f"Run: ollama pull {model}")
                    raise OllamaError(f"Ollama answered {response.status}: {text}")
                for line in response:
                    if self.cancelled:
                        raise Cancelled()
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except ValueError as exc:
                        raise OllamaError("Ollama sent a line that isn't JSON.") from exc
                    if not isinstance(chunk, dict):
                        raise OllamaError("Ollama sent a reply in an unexpected shape.")
                    if chunk.get("error"):
                        raise OllamaError(f"Ollama: {chunk['error']}")
                    yield chunk
                    if chunk.get("done"):
                        return
            except (OSError, http.client.HTTPException) as exc:
                if self.cancelled:
                    raise Cancelled() from exc
                raise _not_running(self.url, exc) from exc
            if self.cancelled:
                raise Cancelled()
            raise OllamaError("Ollama stopped before the reply was finished.")
        finally:
            with self._lock:
                self._conn = None
            conn.close()

    def text(self, model: str, messages: list, **kw) -> str:
        """The whole reply's text (the streamed pieces joined)."""
        return "".join((c.get("message") or {}).get("content") or "" for c in self.stream(model, messages, **kw))
