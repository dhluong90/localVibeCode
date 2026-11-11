# Round 01-OC — OpenCode + qwen3:14b (môi trường mới, chưa tinh chỉnh)

**Trạng thái:** Done (2026-11-11 22:40 → 2026-11-12 00:30)
**Cấu hình:** `OC` — OpenCode 1.19.5 (headless, `--auto`), model `qwen3:14b` qua proxy sửa tool-call (`local-ai/ollama_proxy.py`, thinking tắt), Ollama context 32k, flash attention, KV q8.
**Code:** `ec474f0` (bản đóng băng) · k = 1 · 22 task (11 Java nhỏ + 11 Apollo dev)

## Vì sao cấu hình như vậy (phát hiện khi dựng môi trường)
| Vấn đề | Bằng chứng | Xử lý |
|---|---|---|
| `qwen2.5-coder:14b` không gọi tool | Model in lời gọi tool thành văn bản `json`, OpenCode lặp build→compaction vô hạn | Đổi sang `qwen3:14b` (có tool calling) |
| Qwen3 "thinking" quá chậm | Thêm 2 dòng code: 6 phút, ~2k token suy luận/bước | Proxy đặt `reasoning_effort=none` → 18 s |
| Tắt thinking làm hỏng file | Model ghi `\n` dạng chữ trong tham số `edit` → 0/3 file hợp lệ | Proxy sửa `\n` ngoài dấu nháy trong tham số code → 5/5 |
| OpenCode tìm nhầm thư mục | Lấy `PWD` của shell cha, đọc file trong worktree khác (không sửa gì) | `--dir` + `PWD` = workspace |
| OpenCode không tự nhận Ollama local | `Model not found: ollama/...`, chế độ JSON treo im lặng | Khai báo provider Ollama trong `opencode.json` |

## Kết quả

| Bộ | OC (OpenCode + qwen3:14b) | Tham chiếu (Round 00 / 00b, qwen2.5-coder:14b) |
|---|---|---|
| **Java nhỏ (11)** | **7/11 = 64%** · regression 9% · ~5 phút/task | B0 91% · H 55% · O 88% |
| **Apollo dev (11)** | **0/11** | B0 2/6 · H 0/6 · O 2/5 |

Java nhỏ theo loại: I1 2/2 · I2 1/2 · I3 1/2 · I6 1/1 · M1 1/2 · T1 1/2.

## Phân tích thất bại

**Java nhỏ (4 fail):**
- `I2-02`: import sai (`java.util.Collectors`), xoá nhầm import, rồi **báo "compiles, tests pass" sau một lỗi compile** mà không chạy lại test.
- `M1-01`: 55 lần gọi model, không sửa file nào (lỗi gốc ở `CheckoutRequest.addItem`).
- `I3-02`, `T1-02`: logic/test chưa đúng.

**Apollo (11 fail)** — phân loại từng run:
| Nguyên nhân | Run | Ghi chú |
|---|---|---|
| Không tìm được file trong repo nhiều module | 6/11 | Đoán `src/main/java/...` không có tiền tố module; glob `**/X.java` chỉ dùng đôi khi; bỏ cuộc "file not found" |
| Không chạy được test | 4/11 | **Lỗi của bench**: test command trong prompt không quote, zsh mở rộng `**` trong `-Dtest=...**` → "no matches found". Đã sửa ở `e24e3d5` |
| Context đầy → compaction → dừng | 3/11 (chồng lấn) | Đọc nguyên file lớn + kết quả grep dài vượt 32k |

## Kết luận & action cho Round 02
- Trên repo nhỏ, môi trường mới dùng được (64%, tự chạy test, diff gọn) nhưng chưa bằng việc dev đưa đúng file cho model code chuyên dụng.
- Trên repo lớn, điểm nghẽn là **điều hướng + quản lý context**, và một lỗi môi trường của bench.
- **Round 02 = `OCVG`**: OpenCode + **vòng kiểm tra** (harness chạy test sau khi agent dừng, gửi lỗi lại vào cùng session, tối đa 2 vòng) + **hướng dẫn điều hướng trong `AGENTS.md`** (bản đồ module, `**/ClassName.java`, grep rồi chỉ đọc ~80 dòng quanh chỗ cần, quote `-Dtest`) + test command đã quote.
