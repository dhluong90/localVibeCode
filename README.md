# localVibeCode

<p align="center">
  <strong>Enterprise Local Vibe Coding Engine — 100% Offline & Air-Gapped</strong><br>
  <em>Turn your local laptop into an autonomous, hallucination-resistant AI coding node without internet access.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Environment-100%25%20Offline%20%2F%20Air--Gapped-success" alt="Offline">
  <img src="https://img.shields.io/badge/Inference-Ollama%20Local-blue" alt="Ollama">
  <img src="https://img.shields.io/badge/Context%20Engine-Graphify%20AST%20(0--Token)-orange" alt="AST Graph">
  <img src="https://img.shields.io/badge/Architecture-Deterministic%20PEV-purple" alt="PEV Loop">
  <img src="https://img.shields.io/badge/License-Apache%202.0-green" alt="License">
</p>

---

## 🎯 What is localVibeCode?

In high-security enterprise environments (banking, financial services, telecom, defense, healthcare), developers face a strict constraint: **no public internet access or high network bottlenecks**. At the same time, traditional AI coding tools rely on frontier cloud LLMs with 200k+ token context windows by dumping dozens of files into the prompt.

When running local models (7B – 14B) on laptops (16GB – 32GB RAM):
1. **Dumping multiple files causes severe "Lost in the Middle"** hallucination and memory blowup.
2. **Running multiple models (Planner + Coder + Reviewer) causes VRAM thrashing** and 10–20 second swapping freezes.
3. **Unchecked edits cause breaking contract changes** across dependent modules.

**localVibeCode** solves this by shifting structural discovery and verification to the CPU (0 LLM Tokens), feeding your local model only **surgical, high-precision context (< 4,000 tokens)** under a deterministic state machine.

---

## ⚡ The 3 Architectural Breakthroughs

```
[Developer Requirement]
          │
          ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Phase 0: Graphify AST Indexer (CPU • 0 LLM Tokens)                    │
│  - Parses AST across codebase in < 0.1s                                │
│  - Identifies Architectural God Nodes & Leiden subsystem clusters      │
│  - Extracts 1-Hop Inbound Callers & Outbound Signatures                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Phase 1: PLAN (Fresh Context #1 • Constrained JSON Schema)            │
│  - Analyzes Requirement + GRAPH_REPORT.md + Enterprise Guardrails      │
│  - Generates minimal ordered Atomic Tasks (Model -> Service -> Test)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Context Reset)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Phase 2: EXECUTE (Fresh Context #2 per file • Surgical Slice)         │
│  - Blast-Radius Slicer feeds ONLY: Target File + 1-Hop Signatures      │
│  - Single Pinned Base Model generates surgical patch                   │
│  - Immediate Zero-Token Verifier (AST check + SAST + Unit Tests)       │
│  - Self-Healing loop with error traceback if verification fails        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Context Reset)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Phase 3: VERIFY (Fresh Context #3 • Spec Critic)                      │
│  - Evaluates unified git diff against original requirements            │
│  - Produces pass/replan scorecard and compliance score (0-100)         │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Deterministic AST Knowledge Graph (Graphify Style):**
   - 0 LLM tokens consumed.
   - Maps classes, functions, and import/call dependencies deterministically using AST parsing.
   - Ranks **Architectural God Nodes** so AI knows which core interfaces cannot be broken.
2. **Blast-Radius Slicer (< 4,000 Tokens Surgical Context):**
   - Extracts only: Target file + 1-Hop Outbound Signatures (function bodies stripped) + 1-Hop Inbound Callers.
   - Allows a 7B or 14B model to make multi-file modifications with the precision of a 200B cloud model.
3. **Single Pinned Base Model & Deterministic PEV:**
   - Keeps **only 1 model** pinned in Unified Memory/VRAM (`keep_alive: -1m`), eliminating model swapping.
   - Resets context at every phase (**Plan $\rightarrow$ Execute $\rightarrow$ Verify**) to keep the model in its **Peak Reasoning Zone**.
   - Zero-token verification (AST, Security SAST, Test Suite) before displaying changes.

---

## 🚀 Quickstart

### 1. Prerequisites
- **OS:** macOS (Apple Silicon M-series recommended) or Linux.
- **RAM:** 16GB+ Unified Memory / RAM recommended.
- **Python:** Python >= 3.9.
- **Inference Engine:** [Ollama](https://ollama.com/) running locally.
- **Recommended Model:** `qwen2.5-coder:7b` (fast) or `qwen2.5-coder:14b` (deep reasoning).

```bash
# Pull your preferred local coding model
ollama pull qwen2.5-coder:7b
```

### 2. Installation
Clone the repository:
```bash
git clone https://github.com/dhluong90/localVibeCode.git
cd localVibeCode

# Make the CLI launcher executable (or add to your PATH)
chmod +x ./localvibecode
```

### 3. Run Preflight Health Check
Verify your local environment, RAM budget, Ollama daemon, and models:
```bash
./localvibecode doctor
```
```text
──────────────────── SYSTEM PREFLIGHT DIAGNOSTICS ────────────────────
  [PASS] Python Version (Runtime)
         ↳ Python 3.9.6 (/usr/bin/python3)
  [PASS] System Memory (Hardware)
         ↳ 24.0 GB RAM / Unified Memory detected (Darwin arm64)
  [PASS] Git CLI (Toolchain)
         ↳ Found at /usr/bin/git
  [PASS] Ollama Binary (Inference)
         ↳ Found at /usr/local/bin/ollama
  [PASS] Ollama Daemon Service (Inference)
         ↳ Responding at http://localhost:11434 (2 model(s) installed)
  [PASS] Coding LLM Models (Inference)
         ↳ Available: ['qwen2.5:7b', 'gemma4:latest']
──────────────────────────────────────────────────────────────────────
[SUCCESS] All environment checks passed! localVibeCode is 100% ready to run offline.
```

### 4. Test on the Included Enterprise Demo Repo
```bash
./localvibecode pev "Add 20% discount for ENTERPRISE tier in order service and add unit test verifying 500.0 USD charges 400.0."
```

---

## 🛠️ Onboarding an Existing Project

You can apply localVibeCode to any existing repository in one command:

```bash
./localvibecode init /path/to/your/existing/project
```

What `init` does automatically in 1 second:
1. Detects project test suite (`pytest`, `npm test`, `go test`).
2. Generates `localvibecode.json` config.
3. Configures OpenCode CLI integration (`opencode.json`).
4. Configures VS Code / Cursor MCP integration (`.vscode/mcp.json`).
5. Generates starter `enterprise_rules/` folder.
6. Builds the initial Graphify AST map in `graphify-out/GRAPH_REPORT.md`.

---

## 💻 IDE & Tool Integrations

### 1. OpenCode CLI (Terminal Agent)
Run OpenCode in any onboarded repository:
```bash
cd /path/to/your/project
opencode
```
Use custom slash commands:
- `/graph` — Inspect architectural God Nodes and repository skeleton (0 tokens).
- `/impact path/to/file.py` — View 1-hop blast-radius surgical slice.
- `/pev <requirement>` — Trigger autonomous offline Plan-Execute-Verify cycle.

### 2. VS Code & Cursor (MCP Integration)
The onboarded project includes `.vscode/mcp.json`. Any MCP client (VS Code Cline, Roo Code, Continue.dev, Claude Code) connects directly to:
```json
{
  "servers": {
    "localvibecode": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "localvibecode.mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/localVibeCode/src"
      }
    }
  }
}
```

Exposed MCP Tools:
- `localvibecode_build_graph`
- `localvibecode_blast_radius`
- `localvibecode_verify`
- `localvibecode_pev_run`

---

## 📖 CLI Reference

| Command | Description |
| :--- | :--- |
| `localvibecode doctor` | Run environment diagnostics (Python, RAM, Ollama, Models) |
| `localvibecode init <path>` | Onboard an existing codebase for CLI, OpenCode, and VS Code |
| `localvibecode pev "<req>"` | Run end-to-end Plan $\rightarrow$ Execute $\rightarrow$ Verify with 1 local pinned model |
| `localvibecode graph` | Generate & display Graphify AST structural report & God Nodes (0 tokens) |
| `localvibecode slice <file>` | Extract 1-hop surgical context (< 4K tokens) for a specific file |
| `localvibecode verify` | Run zero-token AST check, offline security SAST, and unit tests |
| `localvibecode mcp` | Launch stdio MCP server for IDE agents |

Options:
- `--repo <path>`: Specify target project path (overrides config).
- `--model <name>`: Override Ollama model (e.g. `--model qwen2.5-coder:14b`).
- `--no-banner`: Hide ASCII logo.

---

## 🇻🇳 Dành Cho Kỹ Sư Việt Nam (Vietnamese Summary)

**localVibeCode** được thiết kế đặc thù cho các môi trường doanh nghiệp Việt Nam (ngân hàng, tài chính, viễn thông, cơ quan nhà nước):
- **100% Không cần Internet:** Source code, tài liệu và logic nghiệp vụ không bao giờ rời khỏi laptop.
- **Khắc phục triệt để giới hạn của Local LLM (7B - 14B):**
  - Không nhồi bừa bãi hàng chục file vào context làm AI "lú" (Lost in the Middle).
  - Dùng **Graphify AST (0 token)** để trích xuất đúng vùng ảnh hưởng (Blast-Radius < 4,000 tokens).
  - Ghim cố định **1 model duy nhất trong VRAM**, chia nhỏ quy trình thành vòng lặp **Plan $\rightarrow$ Execute $\rightarrow$ Verify** với context sạch ở mỗi bước.
  - Tự động chạy **AST Check + Security SAST + Unit Test** để tự sửa lỗi (Self-Healing) trước khi giao code cho dev.

---

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).
