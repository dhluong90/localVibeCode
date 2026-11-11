# TIÊU CHUẨN BENCHMARK & VÒNG LẶP CẢI TIẾN HARNESS — localVibeCode

> **Mục đích:** Định nghĩa *đo cái gì*, *đạt bao nhiêu là đủ*, và *cải tiến harness theo quy trình nào* cho đến khi chạm giới hạn năng lực của LLM local hiện tại.
> **Phạm vi model:** `qwen2.5-coder:7b`, `qwen2.5-coder:14b` (Ollama, offline). Có thể thêm model mới mà không đổi tiêu chuẩn.
> **Thay thế:** Tài liệu này là chuẩn gốc. `BENCHMARK_AND_ACCEPTANCE_GUIDE.md` và các báo cáo cũ phải được đo lại theo chuẩn này trước khi dùng cho nghiệm thu.

---

## 0. Nguyên tắc trung thực đo lường (bắt buộc)

1. **Không có số nào không tái lập được.** Mọi con số trong báo cáo phải sinh ra từ một lệnh (`localvibecode bench ...`) và log run tương ứng được lưu.
2. **"Pass" chỉ khi có verifier khách quan.** File/task không được compile/test thì *không được tính* là pass.
3. **Hidden tests.** Acceptance tests dùng để chấm điểm **không được đưa cho agent**. Test do agent tự viết không được tính là bằng chứng hoàn thành.
4. **Ghi nhận mọi can thiệp của người** (số lần, số dòng sửa tay). Kết quả có người sửa phải ghi rõ là L2/L3, không ghi là "autonomous".
5. **Chạy lặp k lần.** LLM không tất định → mỗi instance chạy `k ≥ 5` lần, báo cáo trung bình + khoảng tin cậy 95%.
6. **Tách dev set / test set.** Harness chỉ được tune trên dev set. Test set chỉ chạy khi báo cáo milestone → chống overfit harness theo benchmark (ví dụ: hard-code `models.py` trong prompt Plan hiện tại).
7. **Luôn so với baseline.** Giá trị của localVibeCode = (kết quả qua harness) − (kết quả model trần cùng điều kiện).

---

## 1. Thang mức tự chủ (Autonomy Levels)

Mỗi loại task được gán một **mức kỳ vọng**. Mức được xác định bằng *số liệu đo được*, không bằng cảm nhận.

| Level | Tên | Mô tả vận hành | Vai trò của người |
|:---:|---|---|---|
| **L0** | Manual | Không dùng AI | Làm toàn bộ |
| **L1** | Assist | AI gợi ý snippet / giải thích; người viết code | Tác giả chính |
| **L2** | Vibe Code (Pair) | Người prompt từng bước, đọc từng diff, tự sửa lỗi AI để lại | Lái liên tục, sửa tay thường xuyên |
| **L3** | Supervised Autonomy | AI tự Plan → Execute → Verify end-to-end. Người duyệt **plan** và **diff cuối** (2 checkpoint), sửa tay rất ít | Duyệt, không lái |
| **L4** | Autonomous + PR Gate | AI tự làm đến khi tạo PR sẵn sàng merge; người chỉ review PR | Reviewer |
| **L5** | Self-Operating | AI tự merge dựa trên gate tự động, không người | Không có (không áp dụng cho enterprise trong phạm vi này) |

### 1.1 Ngưỡng định lượng cho từng level

Một loại task **đạt** level X khi thoả **tất cả** ngưỡng của level đó trên **test set**:

| Chỉ số | L2 | L3 | L4 |
|---|:---:|:---:|:---:|
| `resolve@1` (hidden tests pass, lần chạy đơn) | ≥ 50% | ≥ 70% | ≥ 85% |
| `pass^k` (cả k=5 lần đều pass — độ ổn định) | — | ≥ 40% | ≥ 70% |
| Regression rate (làm vỡ test có sẵn) | ≤ 15% | ≤ 5% | ≤ 1% |
| Can thiệp người / task (ngoài checkpoint chuẩn) | ≤ 3 | ≤ 1 | 0 |
| Tỷ lệ dòng người phải sửa tay / tổng dòng diff | ≤ 30% | ≤ 10% | 0% |
| Scope precision (file bị sửa ∩ gold / file bị sửa) | — | ≥ 0.8 | ≥ 0.9 |
| SAST finding mới (High/Critical) | 0 | 0 | 0 |
| Thời gian wall-clock / task (laptop 24GB) | ≤ 15' | ≤ 10' | ≤ 10' |

> Với task không có hidden test (spec, tài liệu, review), `resolve@1` được thay bằng chỉ số chuyên biệt ở Mục 3.

---

## 2. Danh mục task theo SDLC & mức kỳ vọng

Mã task: `<Phase><số>`. Cột **Kỳ vọng** là mục tiêu nghiệm thu; cột **Trần dự kiến** là ước lượng giới hạn model nếu harness hoàn hảo (sẽ được thay bằng số đo từ thí nghiệm Oracle, Mục 5.2).

### P1 — Requirements

| Mã | Task | Verifier | Kỳ vọng 7B | Kỳ vọng 14B | Trần dự kiến 14B |
|---|---|---|:---:|:---:|:---:|
| R1 | Phát hiện điểm mơ hồ / thiếu trong yêu cầu | Recall trên tập điểm mơ hồ đã gán nhãn | L1 | L2 | L2 |
| R2 | Sinh acceptance criteria (Given/When/Then) | Rubric + chuyển thành test chạy được | L1 | L2 | L3 |

### P2 — Design & Analysis

| Mã | Task | Verifier | Kỳ vọng 7B | Kỳ vọng 14B | Trần dự kiến 14B |
|---|---|---|:---:|:---:|:---:|
| D1 | Impact analysis: file nào cần đổi cho yêu cầu X | Precision/Recall so với gold files | L3 | L4 | L4 |
| D2 | Thiết kế thay đổi contract/API (signature, DTO) | Compile + test contract | L2 | L3 | L3 |

### P3 — Implementation

| Mã | Task | Verifier | Kỳ vọng 7B | Kỳ vọng 14B | Trần dự kiến 14B |
|---|---|---|:---:|:---:|:---:|
| I1 | Sửa bug trong 1 file (có mô tả lỗi) | Hidden tests | L3 | L4 | L4 |
| I2 | Feature nhỏ trong 1 file | Hidden tests | L3 | L4 | L4 |
| I3 | Feature xuyên tầng (model → service → controller → test), 3–6 file | Hidden tests + build | L2 | L3 | L3/L4 |
| I4 | Refactor giữ nguyên hành vi (rename, extract, move) | Toàn bộ test cũ pass + diff đúng scope | L2 | L3 | L4 |
| I5 | Greenfield module/scaffold mới (≥ 10 file) | Build + hidden tests + E2E smoke | L2 | L2 | L3 |
| I6 | Đổi contract ở God Node + cập nhật toàn bộ caller | Build + test toàn repo, regression = 0 | L2 | L3 | L3 |

### P4 — Testing

| Mã | Task | Verifier | Kỳ vọng 7B | Kỳ vọng 14B | Trần dự kiến 14B |
|---|---|---|:---:|:---:|:---:|
| T1 | Sinh unit test cho code có sẵn | Pass + coverage Δ + **mutation score** | L3 | L4 | L4 |
| T2 | Viết regression test tái hiện bug (fail trước fix, pass sau fix) | Fail-on-buggy / pass-on-fixed | L2 | L3 | L4 |
| T3 | Sửa test hỏng do thay đổi hợp lệ | Test pass, không xoá/vô hiệu assertion | L2 | L3 | L3 |

### P5 — Review & Quality

| Mã | Task | Verifier | Kỳ vọng 7B | Kỳ vọng 14B | Trần dự kiến 14B |
|---|---|---|:---:|:---:|:---:|
| Q1 | Code review diff, phát hiện lỗi cài sẵn | Recall lỗi cài sẵn, false-positive rate | L1 | L2 | L3 |
| Q2 | Phát hiện lỗ hổng bảo mật | Deterministic SAST (0 token) | L4 | L4 | L4 |
| Q3 | Sửa lỗ hổng bảo mật đã phát hiện | SAST sạch + test pass | L2 | L3 | L3 |

### P6 — Debug & Maintenance

| Mã | Task | Verifier | Kỳ vọng 7B | Kỳ vọng 14B | Trần dự kiến 14B |
|---|---|---|:---:|:---:|:---:|
| M1 | Sửa build/test fail từ traceback, **nguyên nhân gốc ở file khác** | Build + test pass | L2 | L3 | L3 |
| M2 | Nâng version dependency minor, sửa breaking nhỏ | Build + test pass | L1 | L2 | L3 |
| M3 | Giải thích / viết tài liệu cho module legacy | Rubric + câu hỏi kiểm tra có đáp án | L3 | L4 | L4 |

### P7 — Release & Ops

| Mã | Task | Verifier | Kỳ vọng 7B | Kỳ vọng 14B | Trần dự kiến 14B |
|---|---|---|:---:|:---:|:---:|
| O1 | Sinh mô tả PR / changelog từ diff | Rubric (đúng, đủ, không bịa) | L3 | L4 | L4 |
| O2 | Viết/sửa Dockerfile, CI config | Build image / pipeline chạy được | L2 | L2 | L3 |

### 2.1 Ưu tiên đầu tư

Ưu tiên theo **giá trị × khả năng tự động hoá cao × verifier khách quan**:

1. **Nhóm A (làm trước, mục tiêu L4):** T1, I1, I2, D1, Q2, O1
2. **Nhóm B (mục tiêu L3, là "giá trị cốt lõi" của harness):** I3, I4, I6, M1, T2, Q3
3. **Nhóm C (L2 – hỗ trợ vibe code):** I5, R1, R2, M2, O2, Q1

---

## 3. Bộ chỉ số (Metrics)

| Chỉ số | Định nghĩa | Áp dụng |
|---|---|---|
| `resolve@1` | % lần chạy mà toàn bộ hidden tests pass | I*, T3, M*, Q3, D2 |
| `pass^k` | % instance mà **cả k** lần chạy đều pass | Tất cả task có hidden test |
| `regression_rate` | % lần chạy làm fail ≥1 test đã pass ở base commit | Tất cả task sửa code |
| `scope_precision` / `scope_recall` | So file bị sửa với gold files | I*, D1, M1 |
| `human_interventions` | Số lần người phải can thiệp ngoài checkpoint chuẩn | L2–L3 |
| `human_edit_ratio` | Dòng người sửa / tổng dòng diff | L2–L3 |
| `mutation_score` | % mutant bị test sinh ra bắt được | T1, T2 |
| `defect_recall` / `fp_rate` | Lỗi cài sẵn bị phát hiện / cảnh báo sai | Q1, Q2, R1 |
| `harness_failure_share` | % thất bại do harness (mã H*, Mục 5.3) | Đo độ trưởng thành harness |
| Cost | Wall-clock, prompt/completion tokens, peak RAM, số lần gọi LLM | Tất cả |

---

## 4. Thiết kế bộ dữ liệu benchmark

### 4.1 Repo nguồn

| Repo | Ngôn ngữ | Vai trò |
|---|---|---|
| `demo_enterprise_repo` | Python | Smoke test, chạy nhanh |
| `sample_java_repo` (clean-architecture, 5 module Maven) | Java / Spring | Multi-module, God Node, contract |
| `apps/ecommerce_app` | Spring Boot + React | Full-stack, xuyên ngôn ngữ |
| ≥ 1 repo nội bộ thật (đã ẩn danh) | Java/TS | Đại diện thực tế enterprise — **bắt buộc trước nghiệm thu** |

### 4.2 Định dạng một task instance

Mỗi task là một thư mục `benchmarks/tasks/<id>/`:

```
task.json        # định nghĩa task (bên dưới)
hidden/          # hidden tests — copy vào workspace SAU khi agent chạy xong, agent không bao giờ thấy
reference/       # lời giải tham chiếu — dùng để tự kiểm chứng task (`validate`)
```

```json
{
  "id": "java-I3-02",
  "category": "I3",
  "fixture": "java_shop",              // repo nguồn đóng băng trong benchmarks/fixtures/
  "split": "dev",                      // dev | test
  "difficulty": "M",                   // S / M / L
  "prompt": "Add order cancellation ...",
  "setup": [{"file": "...", "find": "...", "replace": "..."}],   // cài lỗi (I1, M1)
  "gold_files": ["src/main/java/.../OrderService.java", "..."],  // scope P/R, KHÔNG đưa cho agent (trừ Oracle)
  "oracle_plan": [{"file": "...", "instruction": "..."}],        // plan chuẩn cho cấu hình Oracle
  "fail_to_pass_base": ["OrderServiceTest"],                     // test có sẵn đang fail do lỗi cài (M1)
  "t1": {"test_file": "...", "min_mutation_score": 0.67, "mutants": [{"file": "...", "find": "...", "replace": "..."}]}
}
```

**Điều kiện hợp lệ của task** (kiểm tra bằng `python -m localvibecode.bench validate`): hidden tests **fail** ở trạng thái ban đầu và **pass** với lời giải tham chiếu, không regression; với T1, test tham chiếu phải pass trên code gốc và đạt ngưỡng mutation score.

### 4.3 Quy mô & phân bổ

- **Giai đoạn 1:** Nhóm A + B, mỗi category ≥ 6 instance (3 Python + 3 Java), tức là ~70 instance. Tỷ lệ dev/test = 60/40.
- **Giai đoạn 2:** Thêm Nhóm C và repo nội bộ, ≥ 120 instance.
- Mỗi instance có độ khó S/M/L cân bằng; báo cáo kết quả theo cả category lẫn độ khó.
- Instance được tạo theo 3 cách: (a) lấy từ commit thật trong lịch sử repo (revert commit → prompt = commit message đã viết lại), (b) cài lỗi có kiểm soát (bug injection, mutation), (c) viết tay bởi senior dev.

### 4.4 Cấu hình chạy

| Tham số | Giá trị |
|---|---|
| Lặp mỗi instance | `k = 5` |
| Cách ly | Mỗi run một bản sao sạch của fixture (đã áp `setup`), có git riêng để lấy diff; chạy trong subprocess riêng với timeout |
| Nhiệt độ / seed | Theo `localvibecode.json`, ghi lại seed từng run |
| Timeout | 15 phút / run |
| Log | Raw log (prompt, response, diff, verifier output) lưu local tại `benchmarks/rounds/round_XX/runs/<run_id>/` — **không commit** (gitignore). Chỉ commit kết quả tổng hợp của vòng (Mục 8) |

---

## 5. Baseline, trần năng lực LLM & phân loại lỗi

### 5.1 Các cấu hình so sánh

| Mã | Cấu hình | Mục đích |
|---|---|---|
| **B0** | Model trần: 1 prompt chứa yêu cầu + file liên quan, trả full file, không retry | Đo năng lực "vibe code" thô |
| **B1** | Model + nhồi repo/RAG đơn giản + retry theo lỗi compile | Baseline agent ngây thơ |
| **H** | localVibeCode harness (phiên bản hiện tại) | Sản phẩm |
| **O** | **Oracle harness**: cùng model, nhưng được cấp *gold files*, *gold plan*, context đầy đủ, edit format đúng, không giới hạn output | Ước lượng **trần của model** |
| **F** (tuỳ chọn) | Frontier model qua cùng harness H, chỉ trên repo không nhạy cảm | Tham chiếu: harness có giới hạn hay model có giới hạn |

### 5.2 Định nghĩa "chạm giới hạn LLM"

- **Harness gap** = `resolve@1(O) − resolve@1(H)` theo từng category.
- Một category được coi là **đã chạm trần model** khi **đồng thời**:
  1. Harness gap ≤ **5 điểm %**, và
  2. `harness_failure_share` ≤ **10%** (phần lớn thất bại còn lại là do model, mã M*), và
  3. 3 vòng cải tiến liên tiếp mỗi vòng tăng < **2 điểm %** trên dev set (plateau).
- Khi chạm trần → dừng tối ưu harness cho category đó; muốn tăng thêm chỉ còn cách đổi model hoặc tăng test-time compute (best-of-n, Mục 6 – A11).
- Nếu **O** vẫn thấp hơn ngưỡng level kỳ vọng → hạ mức kỳ vọng của category đó cho model này và ghi rõ trong báo cáo nghiệm thu.

### 5.3 Phân loại nguyên nhân thất bại (gắn nhãn cho mọi run fail)

**Do harness (H\*) — cần sửa tool:**

| Mã | Nguyên nhân | Dấu hiệu tự động |
|---|---|---|
| H1 | Plan chọn sai/thiếu file | scope_recall < 1 so với gold |
| H2 | Context thiếu symbol cần dùng | Lỗi "cannot find symbol" với symbol có trong repo nhưng không có trong slice |
| H3 | Context bị cắt (truncate) | Slice chạm `max_chars` |
| H4 | Output bị cắt (`num_predict`) | `eval_count == num_predict` |
| H5 | Patch không áp được / JSON hỏng | `PatchOutcome.applied == False` hoặc `json.loads` lỗi |
| H6 | Verifier báo sai (false pass / false block) | Verifier pass nhưng hidden test fail do compile; hoặc block pattern hợp lệ |
| H7 | Self-heal sửa sai file | File gây lỗi (từ stack trace) ≠ file được heal |
| H8 | Hạ tầng (timeout, Ollama lỗi) | Exception/timeout |

**Do model (M\*) — gần trần, cần đổi model hoặc tăng compute:**

| Mã | Nguyên nhân |
|---|---|
| M1 | Logic sai dù context đầy đủ |
| M2 | Bịa API/signature dù signature có trong context |
| M3 | Không tuân thủ chỉ dẫn/quy ước (style, framework) |
| M4 | Làm thiếu yêu cầu |

Gắn nhãn tự động theo dấu hiệu trước; run không gắn được thì người gắn tay (và bổ sung luật tự động).

---

## 6. Backlog cải tiến harness (Actions)

Mỗi action gắn với mã lỗi nó nhắm tới. Thứ tự thực hiện do dữ liệu quyết định (Mục 7), bảng dưới là thứ tự khởi điểm dựa trên review code.

| ID | Action | Nhắm tới | Ghi chú triển khai |
|---|---|---|---|
| **A0** | **Hạ tầng benchmark**: định dạng task YAML, runner k lần, worktree mỗi run, hidden tests, auto-tag H*/M*, báo cáo kèm CI 95% | Tiền đề | Bắt buộc trước mọi action khác |
| A1 | Edit theo diff (SEARCH/REPLACE) làm mặc định; full-file chỉ cho file mới/nhỏ; `num_predict` động theo kích thước file | H4, H5 | `llm_client.py:70`, `schemas.py` |
| A2 | An toàn đường dẫn (`resolve` + `is_relative_to`), sửa lỗi `lstrip("./")`; chạy trên git worktree, rollback khi fail | An toàn, H8 | `state_machine.py:124` |
| A3 | Verifier thật theo ngôn ngữ: `javac`/`mvn -q compile`, `tsc --noEmit`, `py_compile` + `pyflakes` | H6, M2 | Thay đếm `{}` ở `verifier/runner.py:118` |
| A4 | Định vị nguyên nhân gốc cho self-heal: parse compiler error/stack trace → map file qua graph → heal đúng file, cho phép heal nhiều file | H7 | Thay logic "heal file cuối" ở `state_machine.py:229` |
| A5 | Context theo symbol: chỉ đưa symbol thực sự dùng; Java đưa đủ constructor + field; ưu tiên giữ target file khi cắt; slicer dùng đúng ngôn ngữ cho code fence | H2, H3, M2 | `slicer.py:49,73` |
| A6 | Kiểm tra plan tất định (file tồn tại/được phép tạo, trong repo); checkpoint duyệt plan cho L3; gợi ý file ứng viên từ graph | H1 | Bỏ hard-code `models.py` ở `state_machine.py:91` |
| A7 | Bước Spec-first: sinh acceptance criteria → test trước khi code (TDD) và dùng làm verifier nội bộ | M4 | Liên quan R2, T2 |
| A8 | JSON robust: retry khi parse lỗi, repair theo schema | H5 | `state_machine.py:110` |
| A9 | SAST thật offline: Bandit (Python), Semgrep rules (Java/JS), bỏ so khớp chuỗi | H6, Q2 | `verifier/runner.py:28` |
| A10 | Critic: `success` lấy từ tiêu chí tất định; LLM critic chỉ kiểm checklist yêu cầu/scope, prompt không mớm đáp án | H6 | `state_machine.py:267` |
| A11 | Test-time compute: best-of-n + chọn bằng verifier; tăng n khi lỗi M* chiếm ưu thế | M1, M2 | Công cụ để vắt kiệt trần model |
| A12 | Prompt profile theo model (7B vs 14B), few-shot lấy từ chính repo (quy ước test, style) | M3 | |
| A13 | Audit log mỗi run (prompt, response, diff, verdict) | Truy vết, tuân thủ | Dùng chung với A0 |
| A14 | Unit test cho chính tool (patcher, slicer, verifier, graph) | Chất lượng harness | Chặn regression của harness |

---

## 7. Vòng lặp cải tiến liên tục (Harness Improvement Loop)

```
        ┌─────────────────────────────────────────────────────────┐
        │ 1. Chạy benchmark trên DEV set (H, k=5)                  │
        └───────────────┬─────────────────────────────────────────┘
                        ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 2. Gắn nhãn thất bại H*/M* → Pareto theo category        │
        └───────────────┬─────────────────────────────────────────┘
                        ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 3. Chọn bucket H* lớn nhất → giả thuyết → chọn Action    │
        └───────────────┬─────────────────────────────────────────┘
                        ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 4. Triển khai trên branch + unit test cho thay đổi       │
        └───────────────┬─────────────────────────────────────────┘
                        ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 5. A/B trên DEV set: giữ nếu cải thiện có ý nghĩa và     │
        │    không category nào tụt > 2 điểm % (luật "bánh cóc")   │
        └───────────────┬─────────────────────────────────────────┘
                        ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 6. Ghi vào round_XX/README.md: action, Δ metric, bucket  │
        └───────────────┬─────────────────────────────────────────┘
                        ▼
              Đã chạm trần (Mục 5.2)?  ── Chưa ──► quay lại bước 1
                        │ Rồi
                        ▼
        Chạy TEST set → báo cáo milestone / nghiệm thu
```

**Quy tắc:**
- Mỗi vòng chỉ thay đổi **một** yếu tố chính để quy được nguyên nhân.
- Chạy **O (Oracle)** lại mỗi khi đổi model, để cập nhật trần.
- Test set chạy tối đa 1 lần / milestone. Nếu phải tune lại sau khi xem test set → rút instance mới cho test set.
- Khi bucket lớn nhất là M* → chuyển sang A11/A12 hoặc kết luận chạm trần.

---

## 8. Lưu kết quả theo vòng (Rounds)

Tài liệu này là **chuẩn chung**, chỉ thay đổi khi đổi tiêu chuẩn. Kế hoạch và kết quả của từng vòng cải tiến nằm riêng tại `benchmarks/rounds/`:

```
benchmarks/rounds/
├── README.md              # Bảng tổng hợp mọi vòng + lộ trình
└── round_XX/
    ├── README.md          # Mục tiêu, action, cấu hình, kết quả (theo mẫu Mục 9), Pareto lỗi, kết luận
    ├── summary.json       # Metric tổng hợp máy đọc được (để so sánh giữa các vòng)
    └── runs/              # Raw log từng run — local only, không commit
```

**Commit gì:** `README.md` + `summary.json` của mỗi vòng. **Không commit:** `runs/` (raw log có thể lớn và chứa code nội bộ; giữ local hoặc lưu trữ nội bộ khi cần audit).

---

## 9. Mẫu báo cáo nghiệm thu

Mỗi category một dòng, cho từng model:

| Category | n instance | resolve@1 (±CI) | pass^5 | Regression | Scope P/R | Human edits | Level đạt | Level kỳ vọng | Gap tới Oracle | Δ so với B0 |
|---|---|---|---|---|---|---|---|---|---|---|

Kèm theo:
- Lệnh tái lập, commit của tool, phiên bản model, cấu hình phần cứng.
- Pareto lỗi H*/M* còn lại.
- Danh sách category **chưa đạt** và lý do (harness hay model).

**Điều kiện nghiệm thu:** Toàn bộ Nhóm A đạt mức kỳ vọng và ≥ 80% Nhóm B đạt mức kỳ vọng trên test set, với 14B; không có SAST High/Critical mới; mọi số liệu tái lập được.

---

## 10. % SDLC được phủ (SDLC Coverage)

Trả lời câu hỏi: *"Model + harness tự gánh được bao nhiêu phần trăm công sức SDLC?"*

### 10.1 Trọng số công sức theo loại task

Mặc định dưới đây là **giả định khởi điểm** (không phải số đo) — team cần chỉnh theo phân bổ thời gian thực tế của mình. Tổng = 100%.

| Phase | Trọng số | Phân bổ trong phase |
|---|---|---|
| P1 Requirements | 10% | R1 5, R2 5 |
| P2 Design | 10% | D1 5, D2 5 |
| P3 Implementation | 35% | I1 5, I2 8, I3 10, I4 4, I5 4, I6 4 |
| P4 Testing | 20% | T1 10, T2 6, T3 4 |
| P5 Review & Quality | 10% | Q1 5, Q2 2, Q3 3 |
| P6 Debug & Maintenance | 10% | M1 5, M2 3, M3 2 |
| P7 Release & Ops | 5% | O1 2, O2 3 |

### 10.2 Công thức

Với mỗi category `c` có trọng số `w_c` và level đạt được `L_c` (đo trên **test set**, theo Mục 1.1):

- **Mức phủ chặt** = Σ `w_c` với `L_c ≥ L3` — phần công sức AI tự làm, người chỉ duyệt.
- **Mức phủ có trọng số** = Σ `w_c × a(L_c)`, với `a(L4) = 1.0`, `a(L3) = 0.7`, `a(L2) = 0.3`, `a(<L2) = 0`.
- **Độ phủ đo lường** = Σ `w_c` của các category đã có dữ liệu. Category chưa đo được tính `a = 0` và liệt kê riêng là *"chưa đo"* — không được ngoại suy.

Báo cáo luôn ghi cả ba con số, kèm bảng trọng số đã dùng.

---

## 11. Velocity

Trả lời câu hỏi: *"Dùng model + harness thì nhanh hơn tự làm bao nhiêu?"*

### 11.1 Baseline thời gian người làm (`T_human`)

Mỗi task có trường `human_baseline` trong `task.json`:

```json
"human_baseline": {"minutes": 35, "source": "proxy:claude-mid-dev", "breakdown": {"understand": 10, "implement": 12, "test": 8, "build_debug": 5}}
```

| `source` | Ý nghĩa | Được dùng để |
|---|---|---|
| `measured:<người>` | Developer thật làm task, có bấm giờ | Báo cáo velocity **đo được** |
| `proxy:claude-mid-dev` | Claude đóng vai developer trình độ trung bình, ước lượng theo breakdown (đọc hiểu → code → viết test → build/debug) dựa trên lời giải tham chiếu | Báo cáo velocity **mô hình hoá** — luôn ghi nhãn rõ |

Khi có số đo thật, báo cáo ghi thêm sai lệch giữa proxy và đo thật để hiệu chỉnh proxy.

### 11.2 Thời gian khi dùng AI (`T_ai`) cho một run

```
T_ai = T_agent + T_review + (nếu run thất bại hoặc gây regression: T_triage + T_human)
```

- `T_agent`: wall-clock của agent (đo được). Mặc định coi là developer **chờ**; báo cáo thêm biến thể *song song* (`T_agent` không tính) làm cận trên.
- `T_review` = 3 phút + 1 phút / 20 dòng diff — thời gian đọc và duyệt diff (giả định proxy).
- `T_triage` = 5 phút — đọc kết quả AI trước khi bỏ và tự làm (giả định proxy).

### 11.3 Chỉ số

- **Velocity** = Σ `T_human` / Σ `T_ai` trên mọi run của tập đánh giá (lấy kỳ vọng qua k lần chạy).
- **Thời gian tiết kiệm** = 1 − Σ `T_ai` / Σ `T_human`.
- Báo cáo theo từng category và tổng, ghi rõ `source` của baseline và các giả định ở 11.2. Velocity < 1 nghĩa là dùng AI **chậm hơn** tự làm — phải báo cáo đúng như vậy.
