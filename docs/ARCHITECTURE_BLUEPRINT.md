# TÀI LIỆU ĐẶC TẢ KIẾN TRÚC: ENTERPRISE LOCAL VIBE CODING
**Thuộc Hệ Sinh Thái: AISDLC — Software Production Factory**

*(Bản lưu trữ chính thức trong Repository dự án)*

Xem chi tiết kiến trúc:
1. **Mục tiêu:** Vận hành 100% Offline / Air-Gapped trên Laptop cá nhân, bảo mật tuyệt đối source code, đưa trải nghiệm Agentic Vibe Coding về máy local với chất lượng chuẩn Enterprise Factory.
2. **Thử thách:** Giới hạn VRAM (10-16GB), Context Window thực tế nhỏ (<8K-12K tokens trước khi bị Lost-in-the-Middle), Hallucination khi sửa nhiều file, lỗi định dạng Diff/Patch.
3. **Giải pháp:**
   - **Graphify AST Knowledge Graph + Blast-Radius Slicer:** Chuyển việc tìm kiếm sang CPU (0 token), chỉ cắt ngữ cảnh phẫu thuật `< 4,000 tokens` (Target file + 1-hop Outbound Signatures + 1-hop Inbound Callers).
   - **1 Base Model cố định + Deterministic PEV (Plan – Execute – Verify) State Machine:** Xóa sạch Context (Fresh Context) giữa mỗi pha để model luôn ở Peak Reasoning Zone.
   - **Zero-Token Verification + Constrained Decoding:** Ép JSON Schema ở pha Plan/Verify và tự động chạy AST Check + Unit Test ngay sau mỗi pha Execute (Self-Healing Loop).
4. **Tích hợp IDE (OpenCode & VS Code):**
   - Thông qua **`aisdlc-mcp` (Model Context Protocol Server)** và **`aisdlc-cli`**.
   - Cấu hình sẵn trong `opencode.json` (cho OpenCode) và `.vscode/mcp.json` + `.continue/config.json` (cho VS Code).
