# Round 00 — Baseline

**Trạng thái:** Running (bắt đầu 2026-11-10)
**Harness commit:** `5d06d09` (localVibeCode harness H không đổi so với `main`; chỉ thêm `localvibecode.bench`)
**Model:** `qwen2.5-coder:7b`, `qwen2.5-coder:14b`
**Phần cứng:** Apple M5, 24 GB unified memory, Ollama 0.40.13

## Mục tiêu
Đo baseline thật đầu tiên theo `docs/BENCHMARK_STANDARD.md`: năng lực model trần (B0), harness hiện tại (H) và trần model (O), từ đó xác định harness gap theo từng category.

## Action trong vòng
- **A0** — Hạ tầng benchmark: task YAML, runner k=5, worktree mỗi run, hidden tests, auto-tag H*/M*, `summary.json`.
- **A13** — Audit log mỗi run (vào `runs/`, không commit).
- **A14** — Unit test tối thiểu cho patcher, slicer, verifier.
- Bộ dev set ~30 instance: T1, I1, I2, D1, Q2, O1 (Nhóm A) + I3, M1 (Nhóm B); Python + Java.

Không thay đổi logic harness trong vòng này — chỉ đo.

## Cấu hình chạy
| Tham số | Giá trị |
|---|---|
| Split | dev — 22 task LLM (I1, I2, I3, I6, M1, T1 × Python/Java) + 14 case SAST (Q2) |
| k | **3** (lệch so với chuẩn k ≥ 5 — ngân sách tính toán: ~24 h cho 396 run; ghi nhận là giới hạn của vòng này) |
| Cấu hình | B0 (model trần, code block), H (localVibeCode PEV, không đổi), O (Oracle: gold files + gold plan + retry theo test) |
| Timeout | 900 s / run |
| Lệnh tái lập | `PYTHONPATH=src python3 -m localvibecode.bench run --round benchmarks/rounds/round_00 --models qwen2.5-coder:14b,qwen2.5-coder:7b --k 3` rồi `... report --round benchmarks/rounds/round_00 --k 3` |

**Kiểm chứng bộ task:** `python -m localvibecode.bench validate` — 22/22 task hợp lệ (hidden test fail ở base, pass với lời giải tham chiếu; T1 reference mutation score = 1.0).

**Ghi chú phương pháp (từ pilot):**
- B0 và O trả về code block thuần. Khi trả file đầy đủ trong chuỗi JSON, `qwen2.5-coder:7b` làm mất thụt lề Python, khiến O còn yếu hơn H; định dạng JSON chỉ giữ cho H vì đó là thiết kế đang được đo.
- H tự fallback sang model khác khi model yêu cầu chưa cài → runner từ chối chạy nếu model chưa có.
- `sample_java_repo` không dùng: HEAD hiện tại fail checkstyle của chính repo (2 method do lần chạy 14B trước thêm vào `ExampleService` sai thụt lề).

## Q2 — SAST (tất định, đã có kết quả)

Bộ 14 case (`benchmarks/sast_cases/`), chạy `ZeroTokenVerifier` hiện tại:

| | Kết quả |
|---|---|
| Recall (lỗ hổng bị bắt) | **3/8 = 37.5%** — bỏ sót `os.system`, `pickle.loads`, `yaml.load` unsafe, SQL nối chuỗi, `shell = True` có dấu cách |
| False positive | **4/6 = 67%** — chặn nhầm `ast.literal_eval`, `model.eval()`, comment nhắc tới `eval(` / `System.exit(` |

→ Q2 hiện **chưa đạt** mức kỳ vọng L4. Action: A9.

## Kết quả giữa kỳ (2026-11-10 17:30 — 28/396 run, chỉ 7B, k1, chỉ task Java)

> Chưa đủ dữ liệu để kết luận level (n = 1–2 mỗi category, CI rất rộng). Chỉ dùng để định hướng.

| Cấu hình (7B, ALL) | resolve@1 (CI95) | Regression | Scope P/R | s/run |
|---|---|---|---|---|
| B0 — model trần | 40% (17–69%) | 30% | 0.65/0.65 | 40 |
| H — localVibeCode | 44% (19–73%) | 33% | 0.63/0.67 | 155 |
| O — Oracle (trần) | **89%** (56–98%) | 11% | 1.00/1.00 | 52 |

- Harness gap (O − H) **+44 pp**; H − B0 chỉ **+4 pp** trong khi H chậm gấp ~4 lần.
- **100% thất bại của H là do harness** (H1 ×3, H7 ×2 là nhãn chính).
- **H7 xuất hiện ở cả 5/5 run H thất bại**: plan luôn thêm file test làm bước cuối, và test self-healing luôn sửa *file cuối cùng* → heal vào file test thay vì file gây lỗi.
- **H1 ở 3/5**: plan chọn sai file. Với M1 (lỗi gốc ở file khác), plan không bao giờ chọn đúng file gốc (`Product.java`, `CheckoutRequest.java`); D1 plan precision 0.63 / recall 0.67.
- Critic trả **PASS** cho một run thất bại (java-M1-02) → không tin được critic làm tín hiệu thành công (A10).

## Kết quả cuối
_(Điền theo mẫu Mục 9 của tiêu chuẩn sau khi chạy xong.)_

| Category | Model | n | resolve@1 (±CI) | pass^5 | Regression | Scope P/R | Level đạt | Level kỳ vọng | Gap tới Oracle | Δ so với B0 |
|---|---|---|---|---|---|---|---|---|---|---|

## Pareto lỗi
| Mã | Số run | % |
|---|---|---|

## Kết luận & action cho Round 01
—
