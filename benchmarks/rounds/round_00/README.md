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

## Kết quả giữa kỳ #2 (2026-11-11 09:20 — 76/396 run)

**Tiến độ:** 7B đã xong lượt k1 (22 task × 3 cấu hình); 14B mới 10/66 run của k1. Máy khởi động lại lúc 18:16 ngày 10/11 nên runner dừng ~15 h; đã chạy tiếp lúc 09:00 ngày 11/11 (resume, không mất kết quả). Dự kiến xong khoảng 21:00 ngày 11/11.

> k = 1, n = 2–4 mỗi category → CI rất rộng, **chưa kết luận level**. Chỉ dùng để định hướng.

### `qwen2.5-coder:7b`, k1, đủ 22 task

| Category | B0 | H | O (trần) | O − H | H − B0 |
|---|---|---|---|---|---|
| I1 sửa bug 1 file | 75% | 75% | 100% | +25 pp | 0 |
| I2 feature 1 file | 100% | 75% | 100% | +25 pp | −25 pp |
| I3 xuyên tầng | 50% | 75% | 75% | 0 | +25 pp |
| I6 đổi contract | 50% | 100% | 100% | 0 | +50 pp |
| M1 lỗi gốc ở file khác | 25% | 25% | 100% | **+75 pp** | 0 |
| T1 sinh unit test | 50% | **0%** | 75% | **+75 pp** | −50 pp |
| **Tất cả** (CI95) | 59% (39–77%) | 55% (35–73%) | **91%** (72–98%) | **+36 pp** | −5 pp |
| Regression | 14% | 23% | 4% | | |
| Thời gian / run | 31 s | 144 s | 47 s | | |

**Nhận định:**
1. **H chưa tạo ra giá trị so với model trần** (55% vs 59%) trong khi chậm gấp ~4.6 lần và gây regression nhiều hơn. Nơi H thắng: I3, I6 (đổi contract nhiều file) — đúng chỗ blast-radius có ích.
2. **Trần của 7B cao: 91%** khi được cấp đúng file + đúng plan + format code block + retry theo test. Harness gap +36 pp → còn nhiều dư địa cho harness, chưa chạm giới hạn model.
3. **M1 (+75 pp):** plan của H không bao giờ chọn đúng file gốc (H1 ×3); heal luôn sửa file cuối cùng của plan (thường là file test) — H7.
4. **T1 (0%) — phát hiện mới:** với yêu cầu "viết test", plan của H tách thành **6–8 bước cùng sửa một file test**; mỗi bước viết lại cả file trong context mới, nên kết quả cuối là file test fail ngay trên code đúng. Auto-tag ghi M1/M2 nhưng thực chất là lỗi plan (H1) — bổ sung luật tag ở Round 01.
5. Critic trả PASS cho run thất bại (java-M1-02) → không dùng critic làm tín hiệu thành công (A10).
6. 14B (10 run đầu, chỉ Java I1/I2): B0, H, O đều 100% — chưa đủ để so sánh.

**Sửa bộ chấm trong vòng:** mutation score được tính cả khi test của agent fail trên code đúng (fail thì "giết" mọi mutant) → hiển thị 1.0 sai. Đã sửa (score = 0 khi test không pass trên code gốc) và vá 7 kết quả đã chạy; `resolved` không bị ảnh hưởng.

## Kết quả cuối
_(Điền theo mẫu Mục 9 của tiêu chuẩn sau khi chạy xong.)_

| Category | Model | n | resolve@1 (±CI) | pass^5 | Regression | Scope P/R | Level đạt | Level kỳ vọng | Gap tới Oracle | Δ so với B0 |
|---|---|---|---|---|---|---|---|---|---|---|

## Pareto lỗi
| Mã | Số run | % |
|---|---|---|

## Kết luận & action cho Round 01
—
