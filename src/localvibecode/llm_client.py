"""Single Base Model Ollama Client with Memory Pinning & Constrained Decoding.

Enforces the core Local AISDLC principle:
- Only 1 Base Model stays pinned in Unified Memory/VRAM (`keep_alive: -1m`).
- Every PEV step gets a completely FRESH context (stateless call) to avoid
  'Lost in the Middle' and KV-cache bloat.
- Supports JSON Schema Constrained Decoding (`format` field in Ollama API)
  and hard token generation caps (`num_predict`) to prevent infinite loops on 7B models.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

from localvibecode.config import LocalVibeCodeConfig


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    elapsed_sec: float


class SingleModelOllamaClient:
    """Stateless wrapper around local Ollama keeping 1 primary model pinned in RAM."""

    def __init__(self, config: LocalVibeCodeConfig) -> None:
        self.config = config
        self._active_model: Optional[str] = None

    def get_active_model(self) -> str:
        if self._active_model:
            return self._active_model
        available = self.list_local_models()
        if self.config.primary_model in available:
            self._active_model = self.config.primary_model
        elif self.config.fallback_model in available:
            self._active_model = self.config.fallback_model
        elif available:
            self._active_model = available[0]
        else:
            self._active_model = self.config.primary_model
        return self._active_model

    def list_local_models(self) -> list[str]:
        url = f"{self.config.ollama_base_url.rstrip('/')}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def generate_fresh(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        json_schema: Optional[Dict[str, Any]] = None,
        num_predict: int = 1536,
        model_override: Optional[str] = None,
    ) -> LLMResponse:
        """Executes a single-turn inference with a guaranteed FRESH context window."""
        model = model_override or self.get_active_model()
        url = f"{self.config.ollama_base_url.rstrip('/')}/api/chat"

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "keep_alive": self.config.keep_alive,
            "options": {
                "temperature": temperature,
                "num_ctx": self.config.num_ctx,
                "num_predict": num_predict,
                "repeat_penalty": 1.1,
            },
        }
        if json_schema is not None:
            payload["format"] = json_schema

        start = time.time()
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.llm_timeout_sec) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach local Ollama server at {self.config.ollama_base_url}: {exc}"
            ) from exc

        elapsed = round(time.time() - start, 2)
        message_content = raw.get("message", {}).get("content", "")
        prompt_eval_count = int(raw.get("prompt_eval_count", 0))
        eval_count = int(raw.get("eval_count", 0))

        return LLMResponse(
            content=message_content,
            model=model,
            prompt_tokens=prompt_eval_count,
            completion_tokens=eval_count,
            elapsed_sec=elapsed,
        )
