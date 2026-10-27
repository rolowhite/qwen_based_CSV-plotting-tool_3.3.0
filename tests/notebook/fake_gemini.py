"""A stand-in for Google's Gemini API: GET /v1beta/models and POST .../models/<m>:generateContent.

    with FakeGemini(key="k", replies=[text("**Answer:** 4"), call("2+2"), ...]) as fake:
        Gemini("k", base=fake.url).models()

A reply is a generateContent response (see text() and call()) or {"status": 429, "message": "..."}. A request
without the right x-goog-api-key gets Google's 400 "API key not valid". Requests are kept in `fake.requests`
as (path, headers, body).
"""
import json
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]


def text(t, signature=None):
    part = {"text": t, **({"thoughtSignature": signature} if signature else {})}
    return {"candidates": [{"content": {"role": "model", "parts": [part]}, "finishReason": "STOP"}]}


def call(*expressions, signature="sig-1"):
    parts = [{"functionCall": {"name": "calculate", "args": {"expression": e}}, "thoughtSignature": signature}
             for e in expressions]
    return {"candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": "STOP"}]}


class FakeGemini:
    def __init__(self, key="test-key", replies=(), models=MODELS, busy=(), out_of_quota=(), rate_limited=(),
                 slow=None):
        self.key, self.replies, self.models, self.requests = key, list(replies), list(models), []
        self.slow = dict(slow or {})            # model -> seconds it stalls before answering
        self.busy = set(busy)                   # models that answer 503 "high demand"
        self.out_of_quota = set(out_of_quota)   # 429, the free requests per day are used up
        self.rate_limited = set(rate_limited)   # 429 once, per minute, "retry in 1s" (then answer)
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _json(self, status, payload):
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _key_ok(self, body):
                fake.requests.append((self.path, dict(self.headers), body))
                if self.headers.get("x-goog-api-key") != fake.key:
                    self._json(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT",
                                               "message": "API key not valid. Please pass a valid API key.",
                                               "details": [{"reason": "API_KEY_INVALID"}]}})
                    return False
                return True

            def do_GET(self):
                if self._key_ok(None) and self.path.startswith("/v1beta/models"):
                    self._json(200, {"models": [{"name": f"models/{m}", "supportedGenerationMethods":
                                                 ["generateContent", "countTokens"]} for m in fake.models]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                if not self._key_ok(body):
                    return
                model = self.path.split("/models/")[-1].split(":")[0]
                if model not in fake.models:
                    self._json(404, {"error": {"code": 404, "message": f"models/{model} is not found"}})
                    return
                if model in fake.slow:
                    time.sleep(fake.slow[model])
                if model in fake.out_of_quota or model in fake.rate_limited:
                    per_day = model in fake.out_of_quota
                    fake.rate_limited.discard(model)
                    details = [{"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{
                        "quotaId": "GenerateRequestsPer" + ("Day" if per_day else "Minute") + "PerProjectPerModel-FreeTier"}]}]
                    if not per_day:
                        details.append({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "1s"})
                    self._json(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": details,
                                               "message": "You exceeded your current quota."}})
                    return
                if model in fake.busy:
                    self._json(503, {"error": {"code": 503, "status": "UNAVAILABLE", "message":
                                               "This model is currently experiencing high demand."}})
                    return
                reply = fake.replies.pop(0) if fake.replies else text("**Answer:** (no scripted reply)")
                if "status" in reply:
                    self._json(reply["status"], {"error": {"code": reply["status"], "message": reply["message"]}})
                else:
                    self._json(200, reply)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def bodies(self):
        return [b for path, _, b in self.requests if b is not None]

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
