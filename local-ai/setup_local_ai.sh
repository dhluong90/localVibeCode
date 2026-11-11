#!/bin/sh
# One-shot setup of the local AI dev environment (macOS, Apple Silicon, 24 GB):
#   Ollama tuned for agents + qwen3:14b + tool-call repair proxy (LaunchAgent) + OpenCode config.
# Idempotent: re-running re-applies settings. See docs/LOCAL_AI_SDLC_ENVIRONMENT.md.
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
MODEL="${LOCAL_AI_MODEL:-qwen3:14b}"
CONTEXT="${LOCAL_AI_CONTEXT:-32768}"
PROXY_PORT="${LOCAL_AI_PROXY_PORT:-11435}"
SHARE="$HOME/.local/share/local-ai"

echo "==> Ollama settings (context ${CONTEXT}, flash attention, q8 KV cache, keep model loaded)"
launchctl setenv OLLAMA_CONTEXT_LENGTH "$CONTEXT"
launchctl setenv OLLAMA_FLASH_ATTENTION 1
launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0
launchctl setenv OLLAMA_KEEP_ALIVE -1
echo "    Restart the Ollama app (menu bar -> Quit Ollama, then open it again) to apply."

echo "==> Model ${MODEL}"
ollama list | grep -q "^${MODEL} " || ollama pull "$MODEL"

echo "==> Tool-call repair proxy on 127.0.0.1:${PROXY_PORT} (LaunchAgent, starts at login)"
mkdir -p "$SHARE" "$HOME/Library/LaunchAgents"
cp "$HERE/ollama_proxy.py" "$SHARE/ollama_proxy.py"
PLIST="$HOME/Library/LaunchAgents/local.ai.ollama-proxy.plist"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>local.ai.ollama-proxy</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string><string>$SHARE/ollama_proxy.py</string>
    <string>--port</string><string>$PROXY_PORT</string>
    <string>--upstream</string><string>http://localhost:11434</string>
    <string>--log</string><string>$SHARE/proxy.jsonl</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

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
      "name": "Ollama (local, via repair proxy)",
      "options": { "baseURL": "http://localhost:${PROXY_PORT}/v1" },
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
echo "    Usage log (latency/tokens per model call): $SHARE/proxy.jsonl"
