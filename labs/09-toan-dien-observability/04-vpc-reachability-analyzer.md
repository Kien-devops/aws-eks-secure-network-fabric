# 09.04 — Kiểm Chứng Đường Truyền Logic Bằng AWS VPC Reachability Analyzer

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Phân tích toán học cấu hình mạng (Formal Reasoning) để xác thực tính thông suốt giữa Edge và Core mà không cần gửi gói tin thực tế.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo đường dẫn phân tích (**Reachability Analyzer Path**) giữa giao diện mạng ENI của Frontend Pod (Edge VPC) và Core Internal NLB (Core VPC).
- Kiểm tra toàn bộ các chặng mạng trung gian: Security Groups, Subnet Route Tables, Transit Gateway Route Tables, GWLB Endpoints, NACLs.
- Xác nhận kết quả phân tích: **`PathFound = true`**.
- Sử dụng Reachability Analyzer để phát hiện nhanh các lỗi cấu hình ngắt kết nối (misconfigurations).

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Mở Menu Reachability Analyzer
1. Mở dịch vụ **VPC Console** tại Region Singapore (`ap-southeast-1`).
2. Tại menu bên trái, cuộn xuống mục **Network analysis** -> Chọn **Reachability Analyzer**.
3. Nhấp nút cam **Create and analyze path**.

---

### Bước 2: Cấu Hình Thông Số Đường Dẫn (Path Configuration)
1. **Name tag:** `fabric-edge-to-core-path`.
2. **Source:**
   - **Source type:** Chọn `Network Interfaces`.
   - **Source:** Chọn ENI của một Worker Node trong cụm `fabric-edge-eks` (hoặc ENI của Pod).
   - **Source IP address:** Nhập IP của Frontend Pod (`10.40.10.x`).
3. **Destination:**
   - **Destination type:** Chọn `Network Interfaces` (hoặc `Load Balancers`).
   - **Destination:** Chọn Network Interface của Core Internal NLB (`fabric-core-internal-nlb`).
   - **Destination IP address:** Nhập IP nội bộ của NLB (`10.50.20.x`).
4. **Protocol:** Chọn `TCP`.
5. **Destination port:** Nhập `443`.
6. Nhấp nút cam **Create and analyze path**.

---

### Bước 3: Quan Sát Kết Quả Phân Tích (Hops Analysis)
Quá trình phân tích diễn ra trong khoảng 30 - 60 giây:
- Quan sát danh sách các chặng (Hops) hiển thị màu xanh lá:
  - `Source ENI` -> `Edge Security Group` -> `Edge Subnet Route Table` -> `TGW Attachment`
  - -> `Transit Gateway (edge-rt)` -> `Inspection TGW Attachment` -> `Inspection Subnet Route Table`
  - -> `GWLB Endpoint` -> `Transit Gateway (inspection-rt)` -> `Core TGW Attachment`
  - -> `Core Subnet Route Table` -> `Core NLB ENI`.
- Trạng thái tổng thể: **`Path reachable`**.

---

## 3. Xác Minh (Verification)

Chạy lệnh kiểm tra kết quả qua AWS CLI:
```bash
aws ec2 get-reachability-analyzer-path-analysis \
  --analysis-id $(aws ec2 describe-network-insights-analyses --region ap-southeast-1 --query 'NetworkInsightsAnalyses[0].NetworkInsightsAnalysisId' --output text) \
  --region ap-southeast-1 \
  --query 'Analysis.{Id:NetworkInsightsAnalysisId,Status:Status,PathFound:NetworkPathFound}' \
  --output table
```
> Kết quả: `Status = SUCCEEDED`, `PathFound = True`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] AWS VPC Reachability Analyzer hoàn tất phân tích thành công với `Path reachable`.
- [ ] Mọi chặng trung gian (SG, Route Table, TGW, GWLBe) đều hợp lệ, không có lỗi chặn ngoài ý muốn.

