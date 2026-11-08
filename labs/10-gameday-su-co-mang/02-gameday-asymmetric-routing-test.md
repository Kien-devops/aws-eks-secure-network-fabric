# 10.02 — Đặc Tả GameDay Kịch Bản 2: Lỗi Định Tuyến Bất Đối Xứng (Asymmetric Routing Failure)

> **Mã bài lab:** `10.02`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/10-gameday/gameday-02-asymmetric-routing-drops.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả kịch bản diễn tập GameDay 10.02 tiêm lỗi định tuyến bất đối xứng bằng cách vô hiệu hóa tính năng TGW Appliance Mode trên Inspection VPC Attachment, phân tích hiện tượng Stateful Firewall Drop khi gói tin SYN và SYN-ACK bị định tuyến lệch AZ, và chứng minh vai trò sống còn của Appliance Mode.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Bảng Áp Dụng | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-insp-tgw-attachment` | `AWS::EC2::TransitGatewayVpcAttachment` | Inspection VPC Attachment | `tgw-attach-0fb21514974415f35` |
| `fabric-suricata-1a` | `AWS::EC2::Instance` | Subnet `fabric-insp-fw-1a` | Node xử lý gói tin SYN |
| `fabric-suricata-1b` | `AWS::EC2::Instance` | Subnet `fabric-insp-fw-1b` | Node nhận gói SYN-ACK bị lệch |
| Evidence File | `Artifact::Evidence` | `evidence/10-gameday/` | `gameday-02-asymmetric-routing-drops.json` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-gameday` | Tài nguyên diễn tập GameDay |
| `Project` | `aws-eks-secure-network-fabric` | Tài nguyên diễn tập GameDay |
| `Environment` | `prod` | Tài nguyên diễn tập GameDay |
| `ManagedBy` | `manual` | Quản trị kịch bản sự cố thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Cơ Chế Lỗi Kỹ Thuật (Asymmetric Routing Root Cause)

- **Trạng thái chuẩn (Baseline):** `ApplianceModeSupport = enable` trên `fabric-insp-tgw-attachment`. TGW ép cả chiều đi và về của cùng 1 phiên TCP đi qua cùng một AZ ENI của Inspection VPC.
- **Tiêm Lỗi (Fault Injection):** Chuyển `ApplianceModeSupport = disable`. TGW băm ngẫu nhiên 5-tuple độc lập cho từng chiều:
  - Chiều đi (`SYN`): Đi vào Inspection qua AZ `1a`, chuyển cho `fabric-suricata-1a` ghi nhận session.
  - Chiều về (`SYN-ACK`): Do Core gửi từ AZ `1b`, TGW trả về qua AZ `1b`, chuyển cho `fabric-suricata-1b`.
  - Do `fabric-suricata-1b` không thấy gói `SYN` trước đó trong bộ nhớ, nó lập tức DROP gói tin vì vi phạm trạng thái TCP (TCP Out-of-Order / Out-of-State Drop).

### 4.2 Khắc Phục Sự Cố (Remediation)

- Kích hoạt lại `ApplianceModeSupport = enable` trên `fabric-insp-tgw-attachment`.
- Đảm bảo 100% các phiên TCP được giữ đối xứng trên cùng một AZ appliance.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.03`: `fabric-insp-tgw-attachment` phải sẵn sàng để chỉnh sửa options.
- Phụ thuộc vào `05.01`, `05.04`: Cụm Suricata đang hoạt động ở chế độ inline stateful inspection.
- Phụ thuộc vào `04.04`: Microservices `edge-frontend` và `core-service` đang giao tiếp HTTPS liên cụm.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Xác Nhận Tắt Appliance Mode** | `aws ec2 describe-transit-gateway-vpc-attachments --transit-gateway-attachment-ids <InspAttachId>` | `ApplianceModeSupport: disable` trong giai đoạn thử nghiệm. |
| **Hiện Tượng Rớt Gói Tin** | Chạy vòng lặp 40 HTTP requests giữa 2 AZs | Ghi nhận tỉ lệ timeout/drop đáng kể do bất đối xứng trạng thái luồng. |
| **Xác Thực Khôi Phục** | Bật lại `ApplianceModeSupport: enable` và gửi lại 40 requests | Đạt tỉ lệ thành công **100% (40/40 HTTP 200)**, 0 lỗi timeout. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo gián đoạn:** Tắt Appliance Mode ảnh hưởng trực tiếp tới toàn bộ lưu lượng East-West đi qua Inspection VPC. Chỉ thực hiện trong khung giờ diễn tập đã được phê duyệt.
- **Quy trình Rollback:**
  ```bash
  # Bật lại Appliance Mode ngay lập tức
  aws ec2 modify-transit-gateway-vpc-attachment --region ap-southeast-1 \
    --transit-gateway-attachment-id tgw-attach-0fb21514974415f35 \
    --options "ApplianceModeSupport=enable"
  ```
