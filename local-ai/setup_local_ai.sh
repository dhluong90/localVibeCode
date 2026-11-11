#!/bin/sh
# One-shot setup of the local AI dev environment (macOS, Apple Silicon, 24 GB):
#   Ollama tuned for agents + qwen3:14b + OpenCode configured for the local model.
# Idempotent: re-running only re-applies settings. See docs/LOCAL_AI_SDLC_ENVIRONMENT.md.
set -e

MODEL="${LOCAL_AI_MODEL:-qwen3:14b}"
CONTEXT="${LOCAL_AI_CONTEXT:-32768}"

echo "==> Ollama settings (context ${CONTEXT}, flash attention, q8 KV cache, keep model loaded)"
launchctl setenv OLLAMA_CONTEXT_LENGTH "$CONTEXT"
launchctl setenv OLLAMA_FLASH_ATTENTION 1
launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0
launchctl setenv OLLAMA_KEEP_ALIVE -1
echo "    Restart the Ollama app (menu bar → Quit Ollama, then open it again) to apply."

echo "==> Model ${MODEL}"
ollama list | grep -q "^${MODEL} " || ollama pull "$MODEL"

echo "==> OpenCode"
command -v opencode >/dev/null 2>&1 || npm install -g opencode-ai
CONFIG_DIR="$HOME/.config/opencode"
mkdir -p "$CONFIG_DIR"
if [ -f "$CONFIG_DIR/opencode.json" ]; then
  cp "$CONFIG_DIR/opencode.json" "$CONFIG_DIR/opencode.json.bak.$(date +%s)"
fi
cat > "$CONFIG_DIR/opencode.json" <<EOF
{
  "\$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": {
        "${MODEL}": { "name": "${MODEL} (local)", "tools": true, "limit": { "context": ${CONTEXT}, "output": 8192 } }
      }
    }
  },
  "model": "ollama/${MODEL}"
}
EOF
echo "    Wrote $CONFIG_DIR/opencode.json (previous config backed up if it existed)."
echo "==> Done. In a repository: add AGENTS.md (template: local-ai/AGENTS.template.md), then run: opencode"
