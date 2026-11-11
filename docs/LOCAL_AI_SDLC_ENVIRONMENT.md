# Thiết kế lại môi trường làm việc: Local AI cho SDLC

> **Mục tiêu:** dùng LLM chạy **local / offline** để tăng năng suất SDLC của team.
> **Ràng buộc:** MacBook Pro 24 GB (Apple M5), không gửi code ra ngoài, chỉ dùng công cụ mã nguồn mở.
> **Nguyên tắc:** mọi lựa chọn mặc định phải được chứng minh bằng benchmark (`docs/BENCHMARK_STANDARD.md`), không bằng cảm nhận.

---

## 1. Rút ra từ số liệu đã đo (Round 00 / 00b)

| Quan sát | Số liệu | Hệ quả cho thiết kế |
|---|---|---|
| Model 14B local đủ tốt cho **thay đổi nhỏ, phạm vi rõ** khi có đúng context | Repo nhỏ: B0 91%. Apollo: B0 giải 2/2 task sửa lỗ hổng nhỏ | Dồn AI vào việc nhỏ, rõ phạm vi; người giữ quyền chia việc |
| Trên repo thật, thay đổi lớn nhiều file vượt sức 14B **kể cả khi có context hoàn hảo** | Apollo: Oracle ~40%, B0 0/4 ở feature nhiều file | Feature lớn = L2 (người dẫn, AI làm từng phần), không tự động hoá |
| Pipeline PEV tự viết **làm kết quả tệ hơn** model trần | H 55% vs B0 91% (repo nhỏ); H 0/6 (Apollo) | Bỏ pipeline tự viết; dùng agent mã nguồn mở đã trưởng thành |
| Đưa cả graph repo vào prompt là không khả thi | GRAPH_REPORT Apollo 1.29M ký tự (~323k token) vs context 16k | Cần **retrieval có ngân sách token** (repo map xếp hạng, search, LSP) |
| Viết lại cả file vừa chậm vừa dễ hỏng | File Apollo 4–6k token ≈ 6 phút/lần ở 14 tok/s; JSON làm mất thụt lề | Edit dạng **search/replace / diff**; chỉ viết lại file nhỏ |
| Phản hồi từ việc chạy thật có giá trị cao | Oracle có vòng sửa theo test: 100% ở I1/I2/I6/M1 (repo nhỏ) | Agent **phải** chạy build/test và tự sửa theo lỗi |
| LLM critic không đáng tin | Critic trả PASS cho run thất bại | "Xong" = test/build/lint pass, không phải LLM tự chấm |
| SAST regex không dùng được | Recall 37.5%, false positive 67% | Dùng Semgrep OSS / SpotBugs+FindSecBugs chạy offline |
| Tốc độ là ràng buộc thật | 14B ≈ 14 tok/s trên M5 (giới hạn băng thông bộ nhớ) | Phân tầng model: model nhỏ cho việc cần nhanh, 14B cho việc cần suy luận |

---

## 2. Kiến trúc mới

```
┌──────────────────────────────── Developer ─────────────────────────────────┐
│  IDE (VS Code / IntelliJ)                 │  Terminal                      │
│  ├─ Continue: autocomplete (FIM)          │  ├─ Aider  (git-native edits,  │
│  ├─ Continue: chat / inline edit          │  │         repo map, auto-test)│
│  └─ Continue: codebase search (@codebase) │  └─ OpenCode (agent, MCP,      │
│                                           │             AGENTS.md)         │
└───────────────┬───────────────────────────┴───────────────┬───────────────┘
                │ OpenAI-compatible API (localhost)         │ MCP (stdio)
┌───────────────▼──────────────────────┐   ┌────────────────▼────────────────┐
│  Model serving: Ollama               │   │  Context & verification tools   │
│  ├─ qwen2.5-coder:1.5b  (FIM, nhanh) │   │  (MCP server — thay PEV cũ)     │
│  ├─ qwen2.5-coder:14b   (chat/agent) │   │  ├─ repo map có ngân sách token │
│  └─ embedding model     (search)     │   │  ├─ search symbol / ripgrep     │
└──────────────────────────────────────┘   │  ├─ test theo module + parse lỗi│
                                           │  └─ SAST: Semgrep / SpotBugs    │
┌──────────────────────────────────────┐   └─────────────────────────────────┘
│  Quality gates (tất định, 0 token):  │
│  build · unit test · Checkstyle/Spotless · Semgrep · pre-commit hook       │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Thành phần

| Lớp | Công cụ (mã nguồn mở) | Vì sao chọn | Thay thế cái cũ |
|---|---|---|---|
| Serving | **Ollama** (đang có), bật `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, context 16–32k | API tương thích OpenAI, mọi client dùng được; KV q8 giảm ~½ bộ nhớ context | — |
| Autocomplete trong IDE | **Continue** + `qwen2.5-coder:1.5b` (FIM) | Phản hồi < 1 s; dùng hàng trăm lần/ngày — lợi ích năng suất chắc chắn nhất | — |
| Chat / inline edit trong IDE | **Continue** + `qwen2.5-coder:14b` | Dev tự chọn file làm context (đúng kịch bản B0 — 91% trên việc nhỏ) | — |
| Agent ở terminal | **Aider** (mặc định đề xuất) và **OpenCode** (đánh giá song song) | Aider: repo map bằng tree-sitter có ngân sách token, edit search/replace, `--test-cmd`/`--auto-test`, commit git từng bước. OpenCode: agent đầy đủ, MCP, đọc `AGENTS.md` | Pipeline PEV |
| Retrieval | Repo map (Aider) + ripgrep + embedding (Continue `@codebase`) + MCP tools | Giải đúng bài toán "repo không vừa context" có ngân sách token | GRAPH_REPORT toàn repo |
| Kiểm chứng | Maven/Gradle test theo module, Checkstyle/Spotless, **Semgrep OSS** (rule offline), SpotBugs + FindSecBugs | Tất định, đáng tin hơn mọi LLM critic | ZeroTokenVerifier regex, LLM critic |
| Quy ước repo | `AGENTS.md` / `CONVENTIONS.md` mỗi repo (lệnh build/test, style, kiến trúc) | Cả Aider, OpenCode, Continue đều nạp được; thay "enterprise_rules" | `enterprise_rules/` |

### 2.2 Ngân sách bộ nhớ (24 GB)

| Thành phần | RAM (ước tính) |
|---|---|
| qwen2.5-coder:14b Q4_K_M | ~9 GB |
| KV cache 16k (q8_0) | ~1.5 GB |
| qwen2.5-coder:1.5b (FIM) | ~1.2 GB |
| Embedding model | ~0.3–0.6 GB |
| **Tổng AI** | **~12–13 GB** → còn ~10 GB cho IDE, JVM, Maven, trình duyệt |

---

## 3. Quy trình theo SDLC — dùng AI ở đâu, mức tự chủ nào

Mức tự chủ theo `BENCHMARK_STANDARD.md` §1. Ban đầu đặt theo số liệu đã có; mỗi dòng có cột "cách kiểm chứng" để benchmark xác nhận/điều chỉnh.

| Giai đoạn | Việc | Công cụ | Mức khởi điểm | Căn cứ hiện có | Cách kiểm chứng |
|---|---|---|---|---|---|
| Coding | Autocomplete dòng / khối | Continue FIM 1.5b | L1 | (chuẩn ngành) | Tỷ lệ chấp nhận gợi ý (telemetry local) |
| Coding | Sửa bug / lỗ hổng 1–2 file khi đã biết chỗ | Continue edit hoặc Aider + test | **L3** | Apollo Q3: 2/2; repo nhỏ I1: 83–100% | Apollo I1/Q3 dev+test split |
| Coding | Feature nhỏ 1 file | Aider + test | L3 | Repo nhỏ I2: 100% | Apollo I2 |
| Coding | Feature nhiều file / xuyên module | Người chia bước, AI làm từng bước + test | **L2** | Apollo I3: B0 0/3, Oracle 1/3 | Apollo I3 |
| Testing | Sinh unit test cho code có sẵn | Aider (chạy test, sửa đến khi pass) | L3 | Repo nhỏ T1: B0 67% (không có vòng chạy test) | T1 + mutation score |
| Debug | Lỗi CI có stack trace | Aider/OpenCode với output lỗi | L2→L3 | Oracle M1 100% khi có file đúng; cần retrieval tốt | M1 |
| Review | Giải thích diff, tóm tắt PR, gợi ý rủi ro | Continue chat / Aider `/ask` | L3 | (chưa đo) | Rubric + lỗi cài sẵn (Q1) |
| Security | Phát hiện lỗ hổng | **Semgrep/SpotBugs** (không dùng LLM) | L4 | Regex cũ: recall 37.5% | Q2 suite hiện có |
| Docs | Giải thích module legacy, viết javadoc/README | Continue chat | L3 | (chưa đo) | Rubric |

**Quy tắc vận hành:**
1. "Xong" chỉ khi build + test + lint + Semgrep pass (pre-commit hook chạy tự động).
2. Agent làm việc trên branch/commit riêng (Aider tự commit từng bước → dễ `undo`).
3. Việc L2: dev viết plan ngắn (danh sách file + thay đổi), AI làm từng bước, dev duyệt diff mỗi bước.
4. Không để AI sửa test có sẵn để "cho pass" (ghi trong `AGENTS.md`).

---

## 4. Nguyên tắc harness (rút từ số liệu, áp dụng cho mọi công cụ)

| Nên | Không nên |
|---|---|
| Edit search/replace hoặc diff; viết lại cả file chỉ với file nhỏ | Nhét cả file vào chuỗi JSON |
| Retrieval có ngân sách token (repo map xếp hạng + search) | Đưa cả graph / cả repo vào prompt |
| Vòng phản hồi build/test thật, sửa đúng file lỗi chỉ tới | LLM tự chấm "PASS" |
| Một bước = một file/một thay đổi gọn; gộp bước cùng file | Tách một việc nhỏ thành nhiều bước viết lại cùng file |
| Timeout theo độ dài output (14B ≈ 14 tok/s) | Timeout cứng 90 s |
| Người duyệt plan ở việc lớn (checkpoint rẻ) | Tự động hoá việc lớn mà trần model thấp |
| Best-of-N chỉ cho việc khó, chọn bằng test | Best-of-N mặc định (tốn thời gian ×N) |

---

## 5. Kế hoạch triển khai

| Phase | Nội dung | Đầu ra | Thời gian |
|---|---|---|---|
| **0. Dựng & đo** | Cài Aider, OpenCode, Continue; cấu hình Ollama (flash attention, KV q8, model 1.5b + embedding); viết `AGENTS.md` cho Apollo; thêm cấu hình benchmark **AD** (Aider) và **OC** (OpenCode) vào bench; chạy trên Java nhỏ + Apollo dev | Bảng so sánh B0 / Aider / OpenCode / (H cũ) theo category → chọn stack mặc định bằng số liệu | 1–2 ngày (đa phần là thời gian chạy) |
| **1. Đóng gói** | `localvibecode init` mới: sinh cấu hình Continue/Aider/OpenCode, `AGENTS.md`, pre-commit (Semgrep, Checkstyle, test theo module); `doctor` kiểm tra RAM/model/cấu hình | 1 lệnh cài môi trường cho máy dev | 2–3 ngày |
| **2. Pilot** | 2–3 dev dùng 2 tuần trên việc thật; log thời gian theo task (task type, có/không AI) | Velocity **đo thật** (thay baseline proxy), danh sách lỗi/khó khăn | 2 tuần |
| **3. Rollout** | Hướng dẫn theo bảng §3, đào tạo ngắn, lặp lại benchmark mỗi khi đổi model/công cụ | Quy trình chuẩn của team | liên tục |

**Tiêu chí chọn stack ở Phase 0:** công cụ nào đạt resolve cao nhất trên **Apollo dev** ở nhóm I1/Q3/I2/T1 với regression ≤ 5% và thời gian/task chấp nhận được (≤ 10 phút) → mặc định. Trên repo nhỏ, công cụ đó không được kém B0 quá 5 điểm %.

---

## 6. Số phận của localVibeCode

| Giữ / làm mới | Bỏ |
|---|---|
| **Bộ benchmark** (`localvibecode.bench`, task Apollo, chuẩn đo) — dùng làm cổng nghiệm thu cho mọi công cụ/model | Pipeline PEV (`pev/`) làm luồng chính |
| MCP server → viết lại thành **context & verification tools** (repo map có ngân sách, test theo module + parse lỗi, Semgrep) | GRAPH_REPORT toàn repo trong prompt |
| `init` / `doctor` → cài & kiểm tra môi trường mới | ZeroTokenVerifier regex SAST, LLM critic |
| Các phát hiện về timeout, edit format, retrieval → đưa vào cấu hình công cụ | Các tuyên bố "100/100", "+88.5%" trong README cũ |

---

## 7. Rủi ro & câu hỏi mở

- **Tool calling của 14B** (cần cho OpenCode) kém tin cậy hơn model lớn → Aider (không cần tool calling, dùng edit format văn bản) có thể phù hợp hơn với model local. Phase 0 sẽ đo.
- **Tốc độ** 14 tok/s giới hạn mọi luồng agent; việc lớn có thể chậm hơn người. Velocity phải đo thật ở Phase 2.
- **Model mới** (vd. qwen3-coder, gpt-oss) có thể tốt hơn 14B hiện tại; chỉ đổi khi benchmark chứng minh.
- Cần biết: IDE chính của team (IntelliJ hay VS Code), ngôn ngữ/repo chính ngoài Java, số máy và RAM thực tế.
