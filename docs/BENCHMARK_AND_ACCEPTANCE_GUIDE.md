# TÀI LIỆU HƯỚNG DẪN NGHIỆM THU & BENCHMARK: LOCALVIBECODE
**Enterprise Local Vibe Coding Engine — 100% Offline / Air-Gapped**

---

## 1. MỤC ĐÍCH & PHẠM VI NGHIỆM THU (OBJECTIVES & SCOPE)

Tài liệu này được thiết kế làm **khung tham chiếu chính thức (Master Acceptance Guide)** dành cho Lead Architects, Engineering Managers, Tech Leads và QA Engineers để chạy kiểm thử, đánh giá hiệu năng và nghiệm thu kỹ thuật hệ thống **`localVibeCode`**.

### Mục Tiêu Cốt Lõi Cần Nghiệm Thu:
1. **Khả năng hoạt động 100% Độc lập Internet (Air-Gapped Readiness):**
   - Toàn bộ chu trình từ đọc mã nguồn, lập kế hoạch, sinh code, phân tích AST, đến chạy unit test và kiểm định bảo mật SAST phải chạy hoàn toàn trên laptop cục bộ, **không gửi bất kỳ byte dữ liệu nào ra ngoài**.
2. **Khắc phục triệt để hiện tượng "Lost in the Middle" của Model Nhỏ (7B - 14B):**
   - Chứng minh cơ chế **Surgical Context (< 4,000 tokens)** kết hợp **Graphify AST (0 LLM tokens)** giúp model nhỏ 7B/14B đạt độ chính xác tương đương model 200B của đám mây mà không bị ảo giác (hallucination).
3. **Độ ổn định tài nguyên phần cứng (Memory & VRAM Stability):**
   - Hệ thống chỉ ghim duy nhất **1 Base Model trong RAM** (`keep_alive: -1m`), tuyệt đối không xảy ra hiện tượng tràn bộ nhớ (OOM) hoặc Model Swapping gây đơ máy trên laptop 16GB – 24GB Unified Memory.
4. **Khả năng tự sửa lỗi khép kín (Self-Healing Loop):**
   - Khi phát hiện lỗi cú pháp AST hoặc lỗi chạy Unit Test, hệ thống tự động trích xuất đúng dòng lỗi và sửa chữa thành công mà không cần lập trình viên phải can thiệp thủ công.

---

## 2. MA TRẬN TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA MATRIX)

| STT | Tiêu Chí Đánh Giá | Chỉ Số Mục Tiêu (Target KPI) | Phương Pháp Đo Lường | Trạng Thái Đạt |
| :-: | :--- | :--- | :--- | :-: |
| **1** | **Tỷ lệ vượt qua tổng thể (Pass Rate)** | **$\ge 80\%$** các use case nghiệm thu | Bộ chạy tự động `localvibecode benchmark` đánh giá qua test suite | 🟢 Bắt buộc |
| **2** | **Bảo toàn giao diện (Contract Integrity)** | **100%** không làm gãy hàm đang gọi | Tra cứu 1-hop Inbound Callers trên đồ thị AST; kiểm tra regression | 🟢 Bắt buộc |
| **3** | **Tiết kiệm Token (Token Efficiency)** | **Giảm > 80%** lượng tokens tiêu thụ | So sánh: Surgical Context (< 4K tokens) vs. Vanilla Dump (> 30K tokens) | 🟢 Bắt buộc |
| **4** | **Ổn định VRAM / Không Swap đĩa cứng** | **0 lần OOM / 0 lần tráo model** | Giữ cố định 1 model trong Ollama; KV Cache $q8\_0$ | 🟢 Bắt buộc |
| **5** | **Khả năng tự sửa lỗi (Self-Healing)** | **$\le 2$ lần thử lại (Retries)** | Tự động phân tích traceback lỗi test và điều chỉnh patch code | 🟢 Bắt buộc |
| **6** | **Chặn vi phạm bảo mật (Zero-Token SAST)** | **Thời gian phát hiện < 0.05s** (0 token) | Bộ `ZeroTokenVerifier` quét AST phát hiện mẫu cấm (`eval`, `exec`) | 🟢 Bắt buộc |

---

## 3. CHI TIẾT 5 USE CASES BENCHMARK NGHIỆM THU

Bộ benchmark bao gồm **5 kịch bản thực tế điển hình** đại diện cho toàn bộ chu trình phát triển phần mềm trong doanh nghiệp:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        5 USE CASES BENCHMARK CỦA LOCALVIBECODE                         │
├──────────────────────────┬─────────────────────────────────────────────────────────────┤
│ Case 1: Ideas to Code    │ Phát triển tính năng mới đa tầng (Model -> Service -> Test) │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Case 2: Unit Test Suite  │ Sinh bộ unit test bao phủ các ca biên và lỗi validation     │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Case 3: Self-Healing TDD │ Tự động phát hiện lỗi sai nghiệp vụ và sửa code pass test   │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Case 4: Blast-Radius     │ Đổi cấu trúc God Node mà không làm hỏng module phụ thuộc    │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Case 5: Zero-Token SAST  │ Chặn đứng mã độc/vi phạm an toàn thông tin với 0 LLM token  │
└──────────────────────────┴─────────────────────────────────────────────────────────────┘
```

---

### Case 1: Ideas to Code (Phát triển Tính Năng Mới Đa Tầng)
- **Kịch bản:** Nghiệp vụ yêu cầu: *"Thêm chiết khấu mua sỉ (Bulk Discount): nếu đơn hàng từ 1000.0 USD trở lên thì giảm thêm 5% (nhân 0.95, làm tròn 2 chữ số thập phân), áp dụng trên cả các phân hạng khách hàng hiện có. Thêm unit test kiểm tra đơn hàng 1000.0 USD phân hạng STANDARD trả về 950.0 USD."*
- **Điểm thách thức với LLM Local truyền thống:** Model 7B thường viết lại toàn bộ file `order_service.py` làm mất các logic tính toán VIP/ENTERPRISE cũ, hoặc viết thiếu import trong file test.
- **Cơ chế xử lý của localVibeCode:**
  1. *Phase 0:* Quét AST lập bản đồ phụ thuộc giữa `order_service.py` và `test_orders.py`.
  2. *Phase 1 (PLAN):* Ép khuôn JSON sinh đúng 2 atomic tasks theo thứ tự: sửa `order_service.py` trước $\rightarrow$ sửa `test_orders.py` sau.
  3. *Phase 2 (EXECUTE):* Nạp ngữ cảnh phẫu thuật (~600 tokens) cho từng file, áp dụng patch và chạy kiểm chứng AST ngay lập tức.
- **Tiêu chuẩn Nghiệm Thu:**
  - Logic cũ không bị mất; hàm `calculate_payable_amount` hỗ trợ đơn $\ge 1000.0$.
  - File `tests/test_orders.py` có thêm test `test_bulk_order_discount`.
  - Toàn bộ test suite chạy pass 100% (**Ran 5 tests, OK**).

---

### Case 2: Zero-to-One Unit Test Suite & Boundary Coverage (Sinh Test Case Biên)
- **Kịch bản:** Yêu cầu: *"Bổ sung unit test kiểm tra các trường hợp lỗi dữ liệu: đơn hàng có tiền tệ không được hỗ trợ ('XYZ') phải báo ValueError, và đơn hàng có số tiền bằng 0.0 phải báo ValueError. Không được làm thay đổi logic các file production."*
- **Điểm thách thức:** Model dễ sinh mock sai chữ ký hàm hoặc tự ý sửa code trong file `validators.py` để né lỗi.
- **Cơ chế xử lý của localVibeCode:** Slicer chỉ nạp chữ ký hàm của `models.py` và `validators.py` (Outbound Signatures) vào context của `test_orders.py`.
- **Tiêu chuẩn Nghiệm Thu:**
  - File `services/` và `models.py` giữ nguyên 100%.
  - Thêm 2 test methods: `test_unsupported_currency_raises` và `test_zero_amount_raises`.
  - Bộ test mở rộng chạy sạch sẽ (**Ran 6 tests, OK**).

---

### Case 3: Bug Diagnosis & Automated Self-Healing (Tự Chuẩn Đoán & Vá Lỗi TDD)
- **Kịch bản:** Hệ thống cố tình tiêm một lỗi tính toán tinh vi vào `order_service.py`: phân hạng VIP chỉ được giảm 5% (0.95) thay vì 10% (0.90), khiến unit test `test_vip_order_discount` bị FAIL với AssertionError.
- **Điểm thách thức:** Model nhỏ khi nhận stack trace dài thường hoảng loạn, xóa nhầm hàm hoặc thử sửa lung tung sang file khác.
- **Cơ chế xử lý của localVibeCode:**
  1. Bộ `ZeroTokenVerifier` bắt được mã lỗi test `AssertionError: 190.0 != 180.0`.
  2. Kích hoạt quy trình **Self-Healing Loop**: nạp đúng dòng traceback lỗi + thân hàm `calculate_payable_amount` vào context sạch.
  3. Model tự nhận biết hệ số `0.95` là sai và sửa lại thành `0.90`.
- **Tiêu chuẩn Nghiệm Thu:**
  - Hệ thống tự sửa thành công trong vòng $\le 2$ lượt thử lại (attempts).
  - Không cần người dùng phải gõ prompt can thiệp.
  - Toàn bộ test suite quay trở lại trạng thái GREEN (**OK**).

---

### Case 4: Blast-Radius Protection (Bảo Vệ Kiến Trúc Khi Sửa God Node)
- **Kịch bản:** Yêu cầu nâng cấp `models.py` (Node trung tâm có nhiều file gọi nhất): *"Thêm thuộc tính tùy chọn `created_at: str = '2026-01-01'` vào dataclass Order."*
- **Điểm thách thức:** Nếu AI đổi thứ tự các thuộc tính không có giá trị mặc định lên sau thuộc tính có giá trị mặc định trong Python Dataclass (`non-default argument follows default argument`), toàn bộ ứng dụng sẽ bị `SyntaxError` khi import.
- **Cơ chế xử lý của localVibeCode:** Đồ thị AST nhận diện `models.py` là **God Node số 1** (Score: 8, có 4 Inbound Callers). Bộ Slicer gắn cờ cảnh báo không được phá vỡ tương thích ngược.
- **Tiêu chuẩn Nghiệm Thu:**
  - Dataclass `Order` có thêm `created_at` với giá trị mặc định hợp lệ.
  - 100% các file đang gọi (`payment_gateway.py`, `order_service.py`, `validators.py`, `test_orders.py`) hoạt động bình thường, không xảy ra TypeError.

---

### Case 5: Zero-Token SAST & Enterprise Security Policy Enforcement
- **Kịch bản:** Hệ thống tiêm một đoạn mã nguy hiểm `eval(payload)` vào `payment_gateway.py`.
- **Điểm thách thức:** Nếu dùng AI để quét mã độc thì tốn hàng ngàn token và dễ bị AI bỏ sót (False Negative).
- **Cơ chế xử lý của localVibeCode:**
  1. Trình kiểm tra `ZeroTokenVerifier` quét cây AST ở cấp độ CPU (**0 LLM Token, tốn 0.005 giây**).
  2. Bắt ngay vi phạm bảo mật: `Enterprise Security Violation: Forbidden pattern 'eval(' detected`.
  3. Chặn đứng quá trình sinh code, bắt buộc AI phải loại bỏ `eval` và dùng logic kiểm tra chuỗi an toàn (`tx_id.startswith('TX-')`).
- **Tiêu chuẩn Nghiệm Thu:**
  - Phát hiện và chặn đứng mã độc ngay lập tức.
  - Code sau khi nghiệm thu sạch 100% mẫu cấm SAST.

---

## 4. HƯỚNG DẪN TEAM CHẠY NGHIỆM THU TỪNG BƯỚC (QUICK EXECUTION GUIDE)

Để team của anh có thể chạy nghiệm thu độc lập trên máy của từng kỹ sư, chỉ cần thực hiện 4 bước sau:

### Bước 1: Clone Repository & Kiểm Tra Môi Trường (Preflight Check)
```bash
git clone https://github.com/dhluong90/localVibeCode.git
cd localVibeCode

# Cấp quyền thực thi cho file launcher
chmod +x ./localvibecode

# Chạy bác sĩ chẩn đoán hệ thống (Kiểm tra RAM, Python, Ollama, Models)
./localvibecode doctor
```
> **Kết quả mong đợi:** Tất cả các mục hiển thị `[PASS]`, bao gồm Python $\ge 3.9$, RAM $\ge 16GB$, Ollama đang chạy và đã có model code (`qwen2.5:7b` hoặc `qwen2.5-coder:7b`).

---

### Bước 2: Chạy Tự Động Toàn Bộ Benchmark Suite (1-Click Run)
Chạy lệnh sau để tự động tạo môi trường cách ly, chạy lần lượt 5 use cases và ghi nhận điểm số:
```bash
./localvibecode benchmark
```
*(Nếu muốn chỉ định rõ model chạy: `./localvibecode --model qwen2.5:7b benchmark`)*

---

### Bước 3: Chạy Thử Từng Use Case Riêng Lẻ (Nếu Cần Debug Sâu)
Nếu team muốn quan sát kỹ quá trình xử lý của một use case cụ thể:
```bash
# Chạy riêng Case 1: Ideas to Code (Tính năng mua sỉ)
./localvibecode benchmark --case 1

# Chạy riêng Case 3: Thử nghiệm khả năng Tự sửa lỗi (Self-Healing)
./localvibecode benchmark --case 3

# Chạy riêng Case 5: Thử nghiệm khả năng Chặn mã độc SAST (Zero-Token SAST)
./localvibecode benchmark --case 5
```

---

### Bước 4: Đọc Báo Cáo Nghiệm Thu Tự Động Sinh Ra
Ngay sau khi chạy xong, kết quả chính thức sẽ được xuất ra tại:
```text
benchmarks/BENCHMARK_REPORT.md
```
Team có thể mở file này trực tiếp bằng VS Code, trình duyệt hoặc GitHub để xem bảng tổng hợp kết quả (Pass/Fail, thời gian, số token tiêu thụ, điểm QA critic).

---

## 5. SO SÁNH HIỆU QUẢ VỚI CÁC PHƯƠNG PHÁP KHÁC

| Tiêu Chí Kỹ Thuật | Phương Pháp Cũ: Dump File Vào Prompt | Phương Pháp Cũ: Vector RAG Truyền Thống | Phương Pháp Mới: localVibeCode |
| :--- | :--- | :--- | :--- |
| **Token tiêu thụ mỗi lần chạy** | $30,000 - 60,000$ tokens | $15,000 - 25,000$ tokens | **$< 4,000$ tokens** (Tiết kiệm > 85%) |
| **Thời gian phản hồi (TTFT)** | $15 - 30$ giây | $8 - 15$ giây | **$< 2$ giây** (Cực nhanh) |
| **Độ hiểu biết về quan hệ gọi hàm** | Rất kém (AI tự đoán) | Kém (chỉ tìm theo từ khóa tương đồng) | **Chính xác 100%** (Dựa trên đồ thị AST Graph) |
| **Hiện tượng phá vỡ giao diện (Breaking Changes)** | Rất thường xuyên | Thường xuyên | **Gần như bằng 0** (Nhờ 1-hop Inbound Callers) |
| **Khả năng tự sửa lỗi (Self-Healing)** | Không có hoặc lặp lại lỗi cũ | Không có | **Tự động vá lỗi qua vòng lặp Unit Test** |
| **Chi phí hạ tầng & Bản quyền** | Phụ thuộc Cloud / Token | Phụ thuộc Vector DB server | **0 VNĐ / 100% Chạy Cục Bộ Trên Laptop** |

---

## 6. HƯỚNG DẪN CẤU HÌNH PHẦN CỨNG TỐI ƯU CHO TEAM

Khi phân phối `localVibeCode` cho các lập trình viên trong doanh nghiệp, hãy cấu hình model phù hợp theo dung lượng RAM của máy:

| Cấu Hình Máy Của Kỹ Sư | Model Khuyên Dùng | Lệnh Kéo Model | Trải Nghiệm Thực Tế |
| :--- | :--- | :--- | :--- |
| **MacBook M-series (16GB RAM)** hoặc Laptop Windows RTX 4060 (8GB VRAM + 16GB RAM) | `qwen2.5-coder:7b` hoặc `qwen2.5:7b` | `ollama pull qwen2.5-coder:7b` | **Siêu nhanh (35-50 tok/s):** Tốn ~5GB RAM, hoàn thành các task tính năng trong 10-25 giây. |
| **MacBook M-series (24GB - 36GB Unified Memory)** (Máy của anh) | `qwen2.5-coder:14b` hoặc `gemma4:latest` | `ollama pull qwen2.5-coder:14b` | **Điểm ngọt tối ưu (Sweet Spot):** Năng lực suy luận mạnh mẽ, sửa nhiều file cực kỳ chuẩn xác, tốn ~9GB RAM. |
| **MacBook M-series (64GB+ Unified Memory)** hoặc Workstation | `qwen2.5-coder:32b` | `ollama pull qwen2.5-coder:32b` | **Đạt chuẩn tương đương Claude 3.5 Sonnet:** Giải quyết các bài toán tái cấu trúc kiến trúc phức tạp. |

---

## 7. BIÊN BẢN KÝ DUYỆT NGHIỆM THU MẪU (ACCEPTANCE SIGN-OFF TEMPLATE)

Team nghiệm thu có thể sử dụng mẫu bên dưới để ký duyệt chính thức:

```
HỘI ĐỒNG NGHIỆM THU KỸ THUẬT: DỰ ÁN LOCALVIBECODE
Ngày nghiệm thu: ................................................
Phiên bản thử nghiệm: v0.2.0 (Branch: main)
Thiết bị kiểm thử: ..............................................

KẾT QUẢ ĐÁNH GIÁ:
[  ] ĐẠT YÊU CẦU: Hệ thống vượt qua các kịch bản benchmark với Pass Rate >= 80%.
[  ] ĐẠT BẢO MẬT: 100% dữ liệu không rời khỏi môi trường local (Air-gapped verified).
[  ] ĐẠT HIỆU NĂNG: Vận hành ổn định, không tràn RAM/VRAM, phản hồi nhanh.

ĐẠI DIỆN TEAM PHÁT TRIỂN                    ĐẠI DIỆN HỘI ĐỒNG NGHIỆM THU
(Ký và ghi rõ họ tên)                       (Ký và ghi rõ họ tên)
```
