"""A stand-in for the Ollama server: /api/version, /api/tags, /api/show, a streamed /api/chat from scripted
replies, and /api/pull (a 3 GB download in three steps, after which the model is installed).

    with FakeOllama({"vl:8b": ["completion", "vision"]}, replies=['{"problems": []}']) as fake:
        ollama.models(fake.url)

A reply is the text the model "writes" (sent in a few chunks), or a dict {"status": 500, "error": "..."},
or {"text": ..., "delay": 0.2} to send it slowly, or {"text": ..., "calls": ["comb(10, 3)"]} for calculate
tool calls. Every /api/chat request body is kept in `fake.requests`.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeOllama:
    def __init__(self, models=None, replies=()):
        self.models = dict(models or {})
        self.replies = list(replies)
        self.requests = []
        self.pulls = []             # models asked for with /api/pull (each is then installed)
        self.pull_delay = 0.0
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

            def do_GET(self):
                if self.path == "/api/version":
                    self._json(200, {"version": "0.0-fake"})
                elif self.path == "/api/tags":
                    self._json(200, {"models": [{"name": n, "model": n} for n in fake.models]})
                else:
                    self._json(404, {"error": "not found"})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                if self.path == "/api/show":
                    if body.get("model") not in fake.models:
                        self._json(404, {"error": f"model '{body.get('model')}' not found"})
                    else:
                        self._json(200, {"capabilities": fake.models[body["model"]]})
                    return
                if self.path == "/api/pull":
                    fake.pulls.append(body.get("model"))
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-ndjson")
                    self.end_headers()
                    for done in (0, 1_000_000_000, 3_000_000_000):         # a 3 GB model in steps
                        self.wfile.write(json.dumps({"status": "pulling", "digest": "sha256:1",
                                                     "total": 3_000_000_000, "completed": done}).encode() + b"\n")
                        self.wfile.flush()
                        time.sleep(fake.pull_delay)
                    fake.models[body.get("model")] = ["completion", "vision"]
                    self.wfile.write(b'{"status": "success"}\n')
                    return
                if self.path != "/api/chat":
                    self._json(404, {"error": "not found"})
                    return
                fake.requests.append(body)
                if body.get("model") not in fake.models:
                    self._json(404, {"error": f"model '{body.get('model')}' not found, try pulling it first"})
                    return
                reply = fake.replies.pop(0) if fake.replies else ""
                reply = reply if isinstance(reply, dict) else {"text": reply}
                if "error" in reply:
                    self._json(reply.get("status", 500), {"error": reply["error"]})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                text, delay = reply.get("text", ""), reply.get("delay", 0)
                step = max(1, len(text) // 4)
                try:
                    for i in range(0, len(text), step):
                        time.sleep(delay)
                        self.wfile.write(json.dumps({"message": {"role": "assistant", "content": text[i:i + step]},
                                                     "done": False}).encode() + b"\n")
                        self.wfile.flush()
                    if reply.get("calls"):      # {"text": ..., "calls": ["comb(10, 3)", ...]}: tool calls
                        calls = [{"id": f"call_{n}", "function": {"index": n, "name": "calculate",
                                                                   "arguments": {"expression": e}}}
                                 for n, e in enumerate(reply["calls"])]
                        self.wfile.write(json.dumps({"message": {"role": "assistant", "content": "",
                                                                 "tool_calls": calls}, "done": False}).encode() + b"\n")
                    self.wfile.write(json.dumps({"message": {"role": "assistant", "content": ""}, "done": True,
                                                 "done_reason": reply.get("done_reason", "stop")}).encode() + b"\n")
                except OSError:
                    pass        # the client hung up (Stop)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
