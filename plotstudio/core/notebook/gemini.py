"""A small client for Google's Gemini API (generateContent), standard library only.

Used only when the user has added their own free key. The key travels in the x-goog-api-key header, never in
the URL, so it can't end up in an error message or a log. `cancel()` closes the connection from another
thread. Errors are GeminiError with a plain message and a kind (key, quota, model, region, busy, network).
"""
from __future__ import annotations

import http.client
import json
import socket
import threading
from typing import List, Optional
from urllib.parse import urlsplit

BASE_URL = "https://generativelanguage.googleapis.com"
# the free-tier models, best first (Google's pricing page, 2026-10-27); a model Google retires falls through
MODELS = ("gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite")
KEY_PAGE = "https://aistudio.google.com/apikey"


class GeminiError(RuntimeError):
    def __init__(self, message: str, kind: str = "other", retry_after: Optional[float] = None):
        super().__init__(message)
        self.kind = kind
        self.retry_after = retry_after          # s Google asks to wait (a per-minute limit)


class Cancelled(Exception):
    """The user pressed Stop."""


def _error(status: int, body: bytes, model: str = "") -> GeminiError:
    try:
        err = json.loads(body).get("error") or {}
    except (ValueError, AttributeError):
        err = {}
    text = str(err.get("message") or body[:200].decode("utf-8", "replace")).strip()
    details = [d for d in err.get("details") or [] if isinstance(d, dict)]
    reasons = " ".join(str(d.get("reason", "")) for d in details)
    if status == 429:
        quota_ids = " ".join(str(v.get("quotaId", "")) for d in details for v in d.get("violations") or []
                             if isinstance(v, dict))
        delay = next((d.get("retryDelay") for d in details if str(d.get("@type", "")).endswith("RetryInfo")), None)
        try:
            wait = float(str(delay).rstrip("s")) if delay else None
        except ValueError:
            wait = None
        if "PerDay" in quota_ids or (wait is None and "PerMinute" not in quota_ids):
            return GeminiError(f"Gemini's free quota for {model or 'this model'} is used up for today.", "quota")
        return GeminiError("Gemini's free per-minute limit was reached; it lets you try again in "
                           f"{wait or 60:.0f} s.", "rate", wait or 60.0)
    if "API_KEY_INVALID" in reasons or "API key not valid" in text or status in (401, 403):
        return GeminiError(f"Gemini didn't accept the key ({text}). Check it at {KEY_PAGE}.", "key")
    if "location is not supported" in text.lower():
        return GeminiError("Gemini's free tier isn't offered in your region.", "region")
    if status == 404:
        return GeminiError(f"The Gemini model {model or ''} isn't available ({text}).".replace("  ", " "), "model")
    if status >= 500:
        return GeminiError(f"Gemini is busy right now (HTTP {status}: {text[:120]})", "busy")
    return GeminiError(f"Gemini answered {status}: {text}", "other")


class Gemini:
    """One call at a time; `cancel()` may be called from any thread."""

    def __init__(self, key: str, base: str = BASE_URL, timeout: float = 60.0):
        if not key or not key.strip():
            raise GeminiError("No Gemini key is set.", "key")
        self._key = key.strip()
        self.base = base
        self.timeout = timeout
        self._conn = None
        self._cancelled = threading.Event()
        self._lock = threading.Lock()

    def __repr__(self):                 # never show the key
        return f"Gemini(base={self.base!r})"

    def cancel(self):
        self._cancelled.set()
        with self._lock:
            conn = self._conn
        if conn is not None and conn.sock is not None:
            try:
                conn.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass        # already closed: the calling thread sees the cancel flag either way

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def _call(self, method: str, path: str, payload=None, model: str = "") -> dict:
        if self.cancelled:
            raise Cancelled()
        parts = urlsplit(self.base)
        kind = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        conn = kind(parts.hostname, parts.port, timeout=self.timeout)
        with self._lock:
            self._conn = conn
        try:
            conn.request(method, path, body=None if payload is None else json.dumps(payload),
                         headers={"x-goog-api-key": self._key, "Content-Type": "application/json"})
            response = conn.getresponse()
            body = response.read()
        except (OSError, http.client.HTTPException) as exc:
            if self.cancelled:
                raise Cancelled() from exc
            if isinstance(exc, TimeoutError):           # a model in high demand sometimes accepts and then stalls
                raise GeminiError(f"Gemini didn't answer within {self.timeout:.0f} s (busy).", "busy") from exc
            raise GeminiError(f"No connection to Gemini ({type(exc).__name__}). Is the internet on?",
                              "network") from exc
        finally:
            with self._lock:
                self._conn = None
            conn.close()
        if self.cancelled:
            raise Cancelled()
        if response.status != 200:
            raise _error(response.status, body, model)
        try:
            return json.loads(body)
        except ValueError as exc:
            raise GeminiError("Gemini sent a reply that isn't JSON.") from exc

    def models(self) -> List[str]:
        """The models this key may use for generateContent (also a check that the key works)."""
        data = self._call("GET", "/v1beta/models?pageSize=1000")
        return [m["name"].split("/", 1)[-1] for m in data.get("models") or []
                if isinstance(m, dict) and "generateContent" in (m.get("supportedGenerationMethods") or [])]

    def generate(self, model: str, body: dict) -> dict:
        return self._call("POST", f"/v1beta/models/{model}:generateContent", body, model)


def pick(available: List[str], wanted: str = "") -> Optional[str]:
    """The wanted model if this key has it, otherwise the first free-tier model it has."""
    for name in ([wanted] if wanted else []) + list(MODELS):
        if name in available:
            return name
    return None
