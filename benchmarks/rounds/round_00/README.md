# Round 00 — Baseline

**Trạng thái:** Planned
**Harness commit:** —
**Model:** `qwen2.5-coder:7b`, `qwen2.5-coder:14b`
**Phần cứng:** —

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
| Split | dev |
| k | 5 |
| Cấu hình | B0, H, O |
| Lệnh tái lập | — |

## Kết quả
_(Điền theo mẫu Mục 9 của tiêu chuẩn sau khi chạy.)_

| Category | Model | n | resolve@1 (±CI) | pass^5 | Regression | Scope P/R | Level đạt | Level kỳ vọng | Gap tới Oracle | Δ so với B0 |
|---|---|---|---|---|---|---|---|---|---|---|

## Pareto lỗi
| Mã | Số run | % |
|---|---|---|

## Kết luận & action cho Round 01
—
