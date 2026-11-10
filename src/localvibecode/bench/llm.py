"""Minimal Ollama chat client for the B0 / Oracle configurations (records every call)."""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Dict, List, Optional


class RecordingOllama:
    def __init__(self, base_url: str, model: str, keep_alive: str, calls: List[Dict[str, Any]]) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.keep_alive = keep_alive
        self.calls = calls

    def chat(
        self,
        phase: str,
        system: str,
        user: str,
        schema: Optional[Dict[str, Any]] = None,
        num_ctx: int = 16384,
        num_predict: int = 8192,
        temperature: float = 0.2,
        timeout: int = 900,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": temperature, "num_ctx": num_ctx, "num_predict": num_predict},
        }
        if schema is not None:
            payload["format"] = schema
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.time()
        record: Dict[str, Any] = {
            "phase": phase,
            "prompt_chars": len(system) + len(user),
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        }
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            record.update({"error": f"{type(exc).__name__}: {exc}", "elapsed_sec": round(time.time() - t0, 2)})
            self.calls.append(record)
            raise
        content = raw.get("message", {}).get("content", "")
        record.update(
            {
                "prompt_tokens": int(raw.get("prompt_eval_count", 0)),
                "completion_tokens": int(raw.get("eval_count", 0)),
                "done_reason": raw.get("done_reason"),
                "elapsed_sec": round(time.time() - t0, 2),
                "response_chars": len(content),
            }
        )
        self.calls.append(record)
        return content
