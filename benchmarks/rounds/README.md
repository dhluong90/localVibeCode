# Benchmark Rounds

Kết quả từng vòng cải tiến harness. Tiêu chuẩn đo (task, level, metric, điều kiện dừng): [`docs/BENCHMARK_STANDARD.md`](../../docs/BENCHMARK_STANDARD.md).

## Tổng hợp

| Round | Ngày | Harness commit | Model | Action chính | resolve@1 (dev) | Harness gap (Oracle − H) | % lỗi do harness | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| [00](round_00/README.md) | — | — | 7B / 14B | A0, A13, A14 — đo baseline | — | — | — | Planned |

## Lộ trình

| Round | Nội dung | Kỳ vọng |
|---|---|---|
| 00 | A0 + A13 + A14 tối thiểu; ~30 instance dev (Nhóm A + một phần B); chạy B0, H, O | Baseline thật đầu tiên, harness gap theo category |
| 01 | Theo Pareto, dự kiến A1, A2, A8 (output bị cắt, patch hỏng, đường dẫn) | % lỗi do harness giảm mạnh |
| 02 | A3, A4, A5 (verifier thật, heal đúng file, context theo symbol) | I3, I6, M1 lên L3 |
| 03 | A6, A7, A10 (plan checkpoint, spec-first, critic) | Ổn định `pass^k` |
| 04 | A11, A12 (best-of-n, prompt profile theo model) | Tiệm cận trần model |
| Milestone | Đủ ~70 instance, chạy test set | Báo cáo nghiệm thu |

Lộ trình từ Round 01 trở đi chỉ là dự kiến — action thực tế của mỗi vòng do Pareto lỗi của vòng trước quyết định.

## Quy ước

- Mỗi vòng một thư mục `round_XX/` gồm `README.md` + `summary.json`. Raw log ở `round_XX/runs/` không commit.
- Mỗi vòng chỉ thay đổi một yếu tố chính; ghi rõ harness commit để tái lập.
- Test set chỉ chạy ở vòng Milestone.
