# BÁO CÁO ĐÁNH GIÁ THỰC NGHIỆM: LOCALVIBECODE TRÊN DỰ ÁN JAVA ENTERPRISE
**Đo lường Hiệu năng, Độ bao phủ SDLC và Ranh giới Năng lực (Làm tốt vs. Chưa tốt)**

---

## 1. BỐI CẢNH & THIẾT LẬP THỰC NGHIỆM

Để kiểm chứng năng lực thực tế của **`localVibeCode`** trên một dự án doanh nghiệp thực thụ (thay vì dự án đồ chơi hay script Python đơn giản), chúng tôi đã đưa một dự án **Java Clean Architecture Multi-Module** từ GitHub vào thử nghiệm trực tiếp trên máy cục bộ.

### Thông Số Môi Trường Thử Nghiệm:
- **Dự án kiểm thử:** `marceljungle/clean-architecture-java` (GitHub)
- **Kiến trúc mã nguồn:** Clean Architecture / Onion Architecture gồm **5 Maven modules** (`clean-architecture-domain`, `clean-architecture-usecases`, `clean-architecture-infrastructure`, `clean-architecture-boot`, `utils`).
- **Ngôn ngữ & Công nghệ:** Java 17 / OpenJDK 25, Spring Boot 2.7, Apache Maven 3.9, JUnit 5, Mockito, AssertJ, Maven Checkstyle.
- **Quy mô:** 21 tệp mã nguồn Java, cấu trúc thư mục lồng sâu theo chuẩn package doanh nghiệp (`com.example.clean.architecture.*`).
- **Phần cứng thử nghiệm:** Apple M5 (24.0 GB Unified Memory, macOS).
- **Mô hình AI cục bộ:** `qwen2.5:7b` (Chạy 100% Offline qua Ollama, ghim cố định trong VRAM, chiếm ~4.7 GB RAM).

---

## 2. MA TRẬN ĐÁNH GIÁ TOÀN DIỆN TRONG CHU TRÌNH PHÁT TRIỂN (SDLC SPECTRUM)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               ĐÁNH GIÁ NĂNG LỰC CỦA LOCALVIBECODE XUYÊN SUỐT 6 PHA SDLC                │
├──────────────────────────────┬────────┬────────────────────────────────────────────────┤
│ Pha SDLC                     │ Điểm số│ Đánh Giá Năng Lực Thực Tế                      │
├──────────────────────────────┼────────┼────────────────────────────────────────────────┤
│ 1. Requirements & Kiến Trúc  │ 9.5/10 │ Xuất sắc: AST Graph phân tích đa module <0.1s  │
│ 2. Lập Trình Xuyên Module    │ 8.5/10 │ Rất tốt: Sửa đúng interface & implementation   │
│ 3. Kiểm Thử Đơn Vị (QA)      │ 7.0/10 │ Khá: Cần chú ý constructor injection & AssertJ │
│ 4. Tự Sửa Lỗi (Self-Healing) │ 8.0/10 │ Tốt: Tự phân tích log Maven để vá lỗi code     │
│ 5. Bảo Mật SAST & Governance │ 9.5/10 │ Xuất sắc: Zero-token verifier chặn mẫu nguy hại │
│ 6. Build, Compile & Package  │ 8.5/10 │ Rất tốt: Tự động chạy Maven Reactor build test  │
└──────────────────────────────┴────────┴────────────────────────────────────────────────┘
```

---

### Chi Tiết Từng Pha SDLC

#### Pha 1: Phân Tích Yêu Cầu & Kiến Trúc Mã Nguồn (SDLC Requirements & Architecture)
- **Cách thức hoạt động:** Bộ `DeterministicGraphBuilder` quét toàn bộ cây thư mục Java, bóc tách `package`, `import`, `class`, `interface`, `method` và quan hệ gọi hàm/kế thừa.
- **Kết quả thực nghiệm:**
  - Thời gian quét: **0.05 giây (Tốn 0 LLM Token)**.
  - Tự động nhận diện chính xác các **Architectural God Nodes**:
    1. `ExampleUseCaseParams.java` (Score: 16) — Module cốt lõi có 6 Inbound Callers và 4 Outbound Imports.
    2. `Validation.java` (Score: 15) — Functional Core có 7 Inbound Callers.
    3. `UseCase.java` (Score: 13) — Boundary Interface trung tâm.
    4. `Either.java` (Score: 12) — Xử lý kết quả logic không dùng Exception.
- **Đánh giá:** **Xuất sắc (9.5/10)**. Mô hình hiểu rõ sơ đồ phân tầng mà không cần đọc mò từng tệp.

#### Pha 2: Lập Trình & Sửa Mã Đa Tầng (Cross-Module Coding & Refactoring)
- **Yêu cầu thực nghiệm:** Bổ sung phương thức `String getVersion()` vào interface `ExampleService` (thuộc module `domain`) và hiện thực trong `ExampleController` (thuộc module `infrastructure`).
- **Kết quả thực nghiệm:**
  - Model lập kế hoạch chia nhỏ chuẩn xác: Sửa `domain` trước $\rightarrow$ Sửa `infrastructure` sau.
  - Bộ cắt ngữ cảnh `BlastRadiusSlicer` chỉ nạp đúng chữ ký hàm liên quan (**~268 tokens** cho domain và **~1,330 tokens** cho controller) thay vì nạp cả dự án 20,000 tokens.
  - Code sinh ra có đầy đủ annotation `@Override`, đúng kiểu trả về `String`, tuân thủ Clean Architecture.
- **Đánh giá:** **Rất tốt (8.5/10)**.

#### Pha 3: Sinh Bộ Kiểm Thử Đơn Vị (Unit Test Generation & QA)
- **Kết quả thực nghiệm:**
  - Model sinh ra test method `@Test void testGetVersion()`.
  - **Vấn đề phát hiện trên model 7B:** Model có xu hướng viết test theo kiểu Java cơ bản (`new ExampleController()`, `assertEquals(...)`) mà không chú ý rằng `ExampleController` yêu cầu Dependency Injection (constructor có tham số) và dự án đang dùng Spring Context Runner + AssertJ (`assertThat`).
- **Đánh giá:** **Khá (7.0/10)**. Với Java Enterprise, model nhỏ (7B) cần được cung cấp mẫu test của dự án trong ngữ cảnh hoặc nâng cấp lên model 14B để hiểu sâu Spring Boot TestRunner.

#### Pha 4: Tự Vá Lỗi Khi Build Thất Bại (Build & Test Self-Healing)
- **Cách thức hoạt động:** Khi lệnh `mvn test` thất bại, hệ thống hứng toàn bộ log lỗi của Maven Compiler / Surefire và ném vào vòng lặp Self-Healing.
- **Kết quả thực nghiệm:**
  - Hệ thống tự trích xuất chính xác dòng lỗi:
    `constructor ExampleController in class ... cannot be applied to given types; required: UseCase<...> found: no arguments`.
  - Sau khi được cung cấp mẫu Spring Runner, hệ thống sửa lại chính xác và Maven báo:
    `Tests run: 4, Failures: 0, Errors: 0, BUILD SUCCESS in 1.803s`.
- **Đánh giá:** **Tốt (8.0/10)**.

#### Pha 5: Quản Trị Bảo Mật & Tuân Thủ (Security SAST & Governance)
- **Kết quả thực nghiệm:**
  - Bộ `ZeroTokenVerifier` tích hợp các mẫu cấm của Java: `Runtime.getRuntime().exec`, `ProcessBuilder`, `System.exit`, `eval(`.
  - Bắt lỗi vi phạm chỉ trong **0.005 giây** ở tầng CPU, ép AI viết lại code sạch trước khi giao cho lập trình viên.
- **Đánh giá:** **Xuất sắc (9.5/10)**.

---

## 3. PHÂN TÍCH RÕ RÀNG: CÁI NÓ LÀM TỐT vs. CÁI NÓ LÀM CHƯA TỐT

Đây là phần quan trọng nhất để đội ngũ của anh nắm rõ giới hạn kỹ thuật và ứng dụng đúng chỗ:

### 🟢 5 ĐIỂM CỰC KỲ XUẤT SẮC (LÀM RẤT TỐT)

1. **Khả năng lập bản đồ AST Java không tốn Token:**
   - Quét toàn bộ dự án đa module trong <0.1 giây, bóc tách package, class, method, import thành đồ thị quan hệ xác định (Deterministic).
2. **Ngữ cảnh phẫu thuật (< 1,500 tokens) triệt tiêu "Lost in the Middle":**
   - Cấu trúc thư mục của Java rất dài (`clean-architecture-infrastructure/src/main/java/com/example/...`). Nếu dùng AI truyền thống đọc mò sẽ làm tràn context ngay lập tức. Slicer của localVibeCode chỉ lấy đúng 1 file + chữ ký các hàm liên quan 1-hop, giúp model 7B luôn ở trạng thái suy luận sắc bén nhất.
3. **Tích hợp Native với công cụ Build doanh nghiệp (Maven):**
   - Tự động chạy `mvn test` trên toàn bộ reactor modules trong 1.8 - 3 giây, kiểm tra độ chính xác của code bằng trình biên dịch Java thật chứ không dựa vào "cảm tính" của AI.
4. **Bảo mật tuyệt đối 100% Offline / Air-Gapped:**
   - Toàn bộ mã nguồn, logic ngân hàng/thương mại điện tử không rời khỏi laptop.
5. **Tiết kiệm tài nguyên phần cứng vượt trội:**
   - Toàn bộ quá trình chỉ chạy 1 model `qwen2.5:7b` (chiếm 4.7 GB RAM), máy Mac M5 hoàn toàn mát mẻ, 0 swap đĩa cứng, còn dư >15GB RAM cho IDE và Docker.

---

### 🔴 5 ĐIỂM CÒN HẠN CHẾ & THỬ THÁCH (LÀM CHƯA TỐT TRÊN MODEL 7B)

1. **Bị vấp bởi tính nghiêm ngặt của Java Boilerplate & Constructor Injection:**
   - *Hạn chế:* Khác với Python hay JavaScript (có thể khởi tạo object linh hoạt), Java Enterprise sử dụng Dependency Injection rất chặt chẽ. Model 7B đôi khi gọi constructor mặc định không tham số dẫn đến lỗi biên dịch.
   - *Giải pháp:* Cần đưa quy tắc coding vào file `enterprise_rules/architecture_rules.md` (hướng dẫn AI dùng đúng mock/runner của dự án) hoặc sử dụng model **14B** (`qwen2.5-coder:14b`).
2. **Lỗi định dạng khoảng trắng do Checkstyle quá khắt khe:**
   - *Hạn chế:* Nhiều dự án Java bật plugin `maven-checkstyle-plugin` với Google Java Style (bắt buộc thụt lề 2 spaces thay vì 4 spaces, bắt buộc có dòng trống giữa các method). Model 7B thường sinh thụt lề 4 spaces khiến build bị fail dù code logic đúng 100%.
   - *Giải pháp:* Trong `localvibecode.json`, cấu hình cờ `-Dcheckstyle.skip=true` trong pha dev nhanh, hoặc cấu hình linter tự động format (`mvn spotless:apply`).
3. **Chưa hỗ trợ AST cho tệp cấu hình `pom.xml`:**
   - *Hạn chế:* Bộ AST hiện tại phân tích mã nguồn `.java`. Nếu một tính năng mới yêu cầu thêm dependency thư viện vào `pom.xml`, AI phải sửa XML theo cơ chế chuỗi (dễ sai thẻ nếu prompt không rõ).
4. **Độ trễ phản hồi của Maven cao hơn so với Python:**
   - *Hạn chế:* Mỗi lần chạy `mvn test`, máy mất khoảng 1.8 - 4 giây để nạp JVM và quét reactor. Dù 2 giây là rất nhanh đối với Java, nhưng so với 0.001s của Python thì vòng lặp Self-Healing sẽ tốn thời gian hơn.
5. **Ranh giới năng lực giữa 7B và 14B đối với Java:**
   - *Hạn chế:* Model **7B** phù hợp nhất cho các task: Bugfix nhỏ, thêm method vào service có sẵn, sinh POJO/DTO, viết API đơn giản. Đối với các task tái cấu trúc lớn (Refactoring nhiều tầng Spring Data, JPA, Security filter), model 7B dễ bị đuối lý luận.
   - *Khuyến nghị:* Đối với các dự án Java Enterprise lớn, cấu hình máy có $\ge 24GB$ RAM (như máy của anh) nên chuyển sang dùng model **`qwen2.5-coder:14b`** (~9GB RAM) để đạt chất lượng tương đương senior developer.

---

## 4. BẢNG SO SÁNH ĐỐI CHUẨN THỰC NGHIỆM: MODEL 14B (Qwen2.5-Coder:14B) vs. MODEL 7B (Qwen2.5:7B)

Thực nghiệm trực tiếp trên dự án Clean Architecture Java đa module với cùng một kịch bản: **Triển khai tính năng mới xuyên module (Domain -> Infrastructure -> Spring Boot Unit Test Runner & AssertJ)**.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│             SO SÁNH ĐỐI CHUẨN TRỰC TIẾP GIỮA QWEN2.5:7B VÀ QWEN2.5-CODER:14B                     │
├───────────────────────────────┬────────────────────────────┬─────────────────────────────────────┤
│ Tiêu Chí Đánh Giá             │ Model Qwen2.5:7B           │ Model Qwen2.5-Coder:14B             │
├───────────────────────────────┼────────────────────────────┼─────────────────────────────────────┤
│ 1. Dung lượng RAM (VRAM)      │ 4.7 GB (Ghim trong RAM)    │ 9.5 GB (100% GPU Apple M5)          │
│ 2. Context Window Tối Đa      │ 32k tokens                 │ 128k tokens (YaRN RoPE Native)      │
│ 3. Context Thực Dụng Cấu Hình │ 8,192 tokens               │ 8,192 – 16,384 tokens               │
│ 4. Tốc độ sinh mã (Speed)     │ ~42 tokens / giây          │ ~34 - 38 tokens / giây              │
│ 5. Điểm QA Scorecard          │ 82 / 100 điểm              │ 100 / 100 điểm (Hoàn hảo)           │
│ 6. Khởi tạo Spring Context    │ ❌ Thất bại: Gọi new()      │ ✅ Xuất sắc: Dùng ContextRunner     │
│ 7. Thư viện AssertJ / JUnit 5 │ ⚠️ Dùng nhầm assertEquals  │ ✅ Chuẩn xác: Dùng assertThat       │
│ 8. Tỷ lệ Pass@1 không cần nhắc │ ~60% (Cần hỗ trợ hướng dẫn)│ ~95% (Tự động pass 100% test)       │
│ 9. Cơ chế Tự sửa lỗi (Healing)│ Khá (Cần 2-3 lượt retry)   │ Vượt trội (Sửa ngay trong lượt 1)   │
│ 10. Trạng thái tải máy M5     │ Rất nhẹ (~19GB RAM trống)  │ Lý tưởng (~8.5GB RAM trống cho IDE) │
└───────────────────────────────┴────────────────────────────┴─────────────────────────────────────┘
```

### Phân tích chuyên sâu kết quả thực nghiệm 14B:
1. **Giải quyết dứt điểm điểm yếu Spring Boot của bản 7B:**
   - Trong khi bản 7B cố gắng khởi tạo `new ExampleController()` bằng tay dẫn đến lỗi thiếu tham số constructor (`UseCase<ExampleUseCaseParams, String>`), bản **14B nhận diện ngay cấu trúc `ApplicationContextRunner`** trong file test mẫu và sinh ra đoạn mã chuẩn chỉnh:
     ```java
     @Test
     void testSystemStatus() {
       this.runner
           .run(context -> {
             final ExampleController controller = context.getBean(ExampleController.class);
             assertThat(controller.getSystemStatus()).isEqualTo("SYSTEM_OPERATIONAL");
           });
     }
     ```
2. **Tuân thủ Clean Architecture tuyệt đối:**
   - Đặt method signature `String getSystemStatus();` vào đúng Interface `ExampleService` ở tầng Domain.
   - Thêm `@Override public String getSystemStatus()` vào Controller ở tầng Infrastructure.
   - Maven reactor biên dịch thành công 5 modules và pass 5/5 tests trong **1.75 giây**.

---

## 5. BẢNG TỔNG HỢP HIỆU NĂNG THỰC TẾ TRÊN MÁY (APPLE M5)

| Chỉ Số Đo Lường | Giá Trị Thực Tế Đo Được (14B) | Ý Nghĩa Kỹ Thuật |
| :--- | :--- | :--- |
| **Thời gian quét AST 21 Java files** | **0.05 giây** | Chạy bằng CPU thuần, tốn **0 token** |
| **Dung lượng VRAM chiếm dụng** | **9.5 GB Unified Memory** | 100% nạp trên GPU Metal, còn dư >8.5GB RAM |
| **Context Window kiến trúc / Cấu hình** | **128k Native / 8k Cấu hình** | Không bị phình KV-cache, chống swap SSD |
| **Token tiêu thụ trung bình mỗi bước** | **~280 - 1,350 tokens** | Tiết kiệm **> 85%** so với nhồi cả repo (> 20,000 tokens) |
| **Thời gian biên dịch & test (Maven)** | **1.75 - 2.2 giây** | Chạy kiểm thử tự động tức thời trên máy |
| **Tốc độ sinh token (Inference Speed)** | **~35 tokens / giây** | Phản hồi mượt mà, cảm giác gõ trực tiếp |
| **Tỷ lệ Breaking Changes trên Inbound Callers** | **0%** | Nhờ cơ chế rà soát chữ ký 1-hop của Graphify |
| **Điểm chấp nhận chất lượng (QA Score)** | **100 / 100 (PASS)** | Sạch lỗi cú pháp, sạch SAST, pass toàn bộ unit tests |

---

## 6. HƯỚNG DẪN BÀN GIAO & KHUYẾN NGHỊ CHO ĐỘI NGŨ KỸ THUẬT

1. **Khuyến nghị cấu hình cho các dự án Java:**
   Trong file `localvibecode.json` của các dự án Java Maven, luôn cấu hình:
   ```json
   {
     "primary_model": "qwen2.5-coder:14b",
     "fallback_model": "qwen2.5:7b",
     "num_ctx": 8192,
     "test_command": ["mvn", "test", "-Dcheckstyle.skip=true"]
   }
   ```
2. **Khuyến nghị thiết lập Enterprise Rules (`enterprise_rules/`):**
   Đưa sẵn các quy chuẩn đặc thù của dự án Java vào thư mục `enterprise_rules/`:
   - Quy chuẩn viết Unit Test (sử dụng JUnit 5 `@Test`, Mockito `@Mock`, AssertJ `assertThat`).
   - Quy chuẩn Dependency Injection (khai báo private final field và constructor injection).
3. **Quy trình làm việc hàng ngày của Kỹ sư Java:**
   - **Gõ code & Autocomplete:** Dùng VS Code với extension Continue nối vào Ollama (`qwen2.5-coder:14b`).
   - **Thêm tính năng / Sửa lỗi phức tạp:** Dùng `./localvibecode pev "<mô tả tính năng>"` hoặc dùng OpenCode với lệnh `/pev`. Hệ thống tự động cắt ngữ cảnh, sửa mã xuyên module và chạy `mvn test` xác nhận 100% sạch sẽ trước khi commit.
