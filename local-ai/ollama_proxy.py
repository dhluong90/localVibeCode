"""Tool-call repair proxy between an agent (OpenCode) and Ollama's OpenAI-compatible API.

Why: with Qwen3 "thinking" on, every agent step costs ~2k output tokens (~2.5 min at 13 tok/s on an
M5); with thinking off (`reasoning_effort: none`) the model double-escapes newlines in edit/write
tool arguments inside OpenCode ("def a():\\n    ..."), producing broken files. This proxy:
  1. sets `reasoning_effort: none` for models listed in NO_THINK_MODELS (unless the client set it),
  2. calls Ollama without streaming, repairs tool-call string arguments that are multi-line code
     written with literal "\\n" escapes and no real newline, and
  3. replays the answer to streaming clients as SSE chunks.
It also appends one JSON line per request to a log (latency, tokens, repairs) for measurement.

Run:  python3 local-ai/ollama_proxy.py --port 11435 --upstream http://localhost:11434
Then point the agent's baseURL at http://localhost:11435/v1 . Zero dependencies (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple

NO_THINK_MODELS = ("qwen3",)
UPSTREAM = "http://localhost:11434"
LOG_PATH = os.path.expanduser("~/.local/share/local-ai/proxy.jsonl")


CODE_ARGUMENTS = ("oldString", "newString", "content", "old_string", "new_string", "patch")


def repair_string(value: str) -> Tuple[str, bool]:
    """Turns literal \\n / \\t written *outside* string literals into real newlines / tabs.

    Escapes inside quotes ("a\\nb") are code and stay untouched; quote state resets at each real newline.
    """
    if "\\n" not in value and "\\t" not in value:
        return value, False
    out = []
    quote = ""
    i = 0
    changed = False
    while i < len(value):
        ch = value[i]
        nxt = value[i + 1] if i + 1 < len(value) else ""
        if ch == "\n":
            quote = ""
            out.append(ch)
        elif ch == "\\" and quote:
            out.append(ch + nxt)  # escape inside a string literal: keep as written
            i += 1
        elif ch == "\\" and nxt in ("n", "t") and not quote:
            out.append("\n" if nxt == "n" else "\t")
            changed = True
            i += 1
            if nxt == "n":
                quote = ""
        else:
            if ch in ("'", '"'):
                quote = "" if quote == ch else (quote or ch)
            out.append(ch)
        i += 1
    return ("".join(out), True) if changed else (value, False)


def _indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def anchor_edit(data: Dict[str, Any]) -> bool:
    """Fuzzy-anchors an edit whose oldString is not an exact substring of the file (small models drift on
    whitespace/indentation). If exactly one window of file lines matches oldString ignoring surrounding
    whitespace, oldString becomes the file's exact text and newString is re-indented by the same offset."""
    path, old, new = data.get("filePath"), data.get("oldString"), data.get("newString")
    if not (isinstance(path, str) and isinstance(old, str) and isinstance(new, str) and old.strip()):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return False
    if old in content:
        return False
    old_lines = [l for l in old.split("\n")]
    while old_lines and not old_lines[0].strip():
        old_lines.pop(0)
    while old_lines and not old_lines[-1].strip():
        old_lines.pop()
    if not old_lines:
        return False
    file_lines = content.split("\n")
    want = [l.strip() for l in old_lines]
    matches = [i for i in range(len(file_lines) - len(want) + 1)
               if [l.strip() for l in file_lines[i:i + len(want)]] == want]
    if len(matches) != 1:
        return False
    start = matches[0]
    exact = "\n".join(file_lines[start:start + len(want)])
    file_indent, model_indent = _indent(file_lines[start]), _indent(old_lines[0])
    if file_indent != model_indent:
        fixed = []
        for line in new.split("\n"):
            if line.startswith(model_indent):
                fixed.append(file_indent + line[len(model_indent):])
            else:
                fixed.append(line)
        new = "\n".join(fixed)
    data["oldString"], data["newString"] = exact, new
    return True


def repair_arguments(arguments: str, tool_name: str = "") -> Tuple[str, int]:
    try:
        data = json.loads(arguments)
    except ValueError:
        return arguments, 0
    if not isinstance(data, dict):
        return arguments, 0
    repairs = 0
    for key, value in list(data.items()):
        if isinstance(value, str) and key in CODE_ARGUMENTS:
            fixed, changed = repair_string(value)
            if changed:
                data[key] = fixed
                repairs += 1
    if tool_name in ("edit", "") and anchor_edit(data):
        repairs += 1
    return (json.dumps(data, ensure_ascii=False) if repairs else arguments), repairs


def sse_chunks(response: Dict[str, Any]):
    """Replays a non-streaming chat completion as OpenAI SSE chunks."""
    base = {"id": response.get("id", "chatcmpl-proxy"), "object": "chat.completion.chunk",
            "created": response.get("created", int(time.time())), "model": response.get("model", "")}
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    delta: Dict[str, Any] = {"role": "assistant"}
    if message.get("content"):
        delta["content"] = message["content"]
    if message.get("tool_calls"):
        delta["tool_calls"] = [dict(tc, index=i) for i, tc in enumerate(message["tool_calls"])]
    yield {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
    yield {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": choice.get("finish_reason", "stop")}],
           "usage": response.get("usage")}


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: Any) -> None:  # keep stdout quiet
        pass

    def _forward_raw(self, method: str, body: bytes = b"") -> None:
        req = urllib.request.Request(UPSTREAM + self.path, data=body or None, method=method,
                                     headers={"Content-Type": self.headers.get("Content-Type", "application/json")})
        try:
            with urllib.request.urlopen(req, timeout=3600) as resp:
                payload, status = resp.read(), resp.status
        except urllib.error.HTTPError as exc:
            payload, status = exc.read(), exc.code
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        self._forward_raw("GET")

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self._forward_raw("POST", body)
            return
        request = json.loads(body or b"{}")
        wants_stream = bool(request.get("stream"))
        model = str(request.get("model", ""))
        if any(model.startswith(m) for m in NO_THINK_MODELS) and "reasoning_effort" not in request:
            request["reasoning_effort"] = "none"
        request["stream"] = False
        request.pop("stream_options", None)
        t0 = time.time()
        req = urllib.request.Request(UPSTREAM + self.path, data=json.dumps(request).encode("utf-8"),
                                     method="POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3600) as resp:
                response = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        repairs = 0
        for choice in response.get("choices") or []:
            for tc in (choice.get("message") or {}).get("tool_calls") or []:
                fn = tc.get("function") or {}
                fn["arguments"], n = repair_arguments(fn.get("arguments", ""), fn.get("name", ""))
                repairs += n
        self._log(model, time.time() - t0, response.get("usage") or {}, repairs)
        if not wants_stream:
            payload = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        chunks = b"".join(f"data: {json.dumps(c)}\n\n".encode("utf-8") for c in sse_chunks(response))
        chunks += b"data: [DONE]\n\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(chunks)))
        self.end_headers()
        self.wfile.write(chunks)

    @staticmethod
    def _log(model: str, seconds: float, usage: Dict[str, Any], repairs: int) -> None:
        try:
            os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model,
                                    "seconds": round(seconds, 2), "prompt_tokens": usage.get("prompt_tokens"),
                                    "completion_tokens": usage.get("completion_tokens"),
                                    "repairs": repairs}) + "\n")
        except OSError:
            pass


def main() -> None:
    global UPSTREAM, LOG_PATH
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11435)
    parser.add_argument("--upstream", default=UPSTREAM)
    parser.add_argument("--log", default=LOG_PATH)
    args = parser.parse_args()
    UPSTREAM, LOG_PATH = args.upstream.rstrip("/"), args.log
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ProxyHandler)
    print(f"local-ai proxy on http://127.0.0.1:{args.port} -> {UPSTREAM}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
