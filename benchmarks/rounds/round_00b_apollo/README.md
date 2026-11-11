# Round 00b — Baseline trên dự án lớn (Apollo)

**Trạng thái:** Running (bắt đầu 2026-11-11 14:05)
**Harness commit:** `0d817a1` (chạy từ bản sao code đóng băng để việc phát triển Round 01 không ảnh hưởng)
**Model:** `qwen2.5-coder:14b` · **Phần cứng:** Apple M5, 24 GB, Ollama 0.40.13

## Mục tiêu
Đo baseline của 14B trên repo enterprise thật: **apolloconfig/apollo** @ `5b663c5f8` (~57.6k LOC Java, 14 module Maven, Spring Boot 4.1). Đây là bài kiểm tra chính cho giá trị của harness: repo không vừa context, agent phải tự tìm đúng file.

## Bộ task
18 task hợp lệ khai thác từ lịch sử commit (`benchmarks/tools/mine_history_tasks.py`): đảo ngược commit trên HEAD, test của commit làm hidden test; prompt viết lại thành ticket, có plan cho Oracle và baseline thời gian người (`proxy:claude-mid-dev`, 40–205 phút/task). Validate: hidden test fail ở trạng thái gốc, pass với lời giải tham chiếu, không regression (1 task refactor bị loại).

| Split | Task | Loại |
|---|---|---|
| **dev (11)** — dùng để tune harness | 190b96e6f, 42d4d827e, c01018384, b4ab0ea9f | Q3 sửa lỗ hổng bảo mật |
| | 55fdcbb57, 5d0755e1e | I1 sửa bug |
| | 0008c348e | I2 feature 1 file |
| | 40a25df02, 0c919ab85, 26ff9f09b, bfc4e89e8 | I3 xuyên tầng / nhiều file |
| **test (7)** — chỉ chạy ở milestone | a99e636d3, b124f902d · dae91b599 · ce54e20b5, e8384a520, a47a122fb, 7daf30647 | Q3 · I1 · I3 |

## Cấu hình
| | |
|---|---|
| Cấu hình | B0 (model + **chỉ các file liên quan**, mô phỏng dev đã tự tìm file), H (localVibeCode PEV, không đổi), O (Oracle) |
| num_ctx | 16384 cho mọi cấu hình (fixture lớn) |
| Test của agent | chỉ test của module liên quan (`-pl … -am`, lọc theo package) |
| k | 3 |
| Lệnh | `PYTHONPATH=src python3 -m localvibecode.bench run --round benchmarks/rounds/round_00b_apollo --models qwen2.5-coder:14b --k 3 --tasks <11 dev ids>` |

## Kết quả
_(Điền sau khi chạy.)_
