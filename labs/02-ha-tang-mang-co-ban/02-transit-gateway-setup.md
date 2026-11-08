# Lab 02.02: Cấu Hình AWS Transit Gateway (TGW) Tắt Mặc Định Propagation

**Mã tài liệu:** `LAB-02-02`
**Trạng thái:** `RUNTIME_PASS`
**Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)
Khởi tạo trục truyền tải trung tâm AWS Transit Gateway (`fabric-tgw`) tại Singapore, tắt tự động liên kết và lan truyền định tuyến (Disable Default Association & Propagation) để kiểm soát phân đoạn an ninh tường minh.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Amazon ASN | Định Danh Runtime (Snapshot) |
| :--- | :--- | :---: | :--- |
| `fabric-tgw` | AWS Transit Gateway | `64512` | `tgw-0fca495dfa8cfee17` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-tgw` | AWS Transit Gateway |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ tài nguyên TGW |
| `Environment` | `prod` | Trục mạng trung tâm |
| `ManagedBy` | `manual` | Quản trị hạ tầng kết nối |

---

## 4. Cấu Hình Chi Tiết (Configuration)
- **Amazon Side ASN:** `64512` (Private Autonomous System Number theo RFC 6996).
- **DNS Support:** `enable` (Cho phép phân giải Route 53 Private DNS giữa các VPC).
- **VPN ECMP Support:** `enable` (Equal-Cost Multi-Path).
- **Default Route Table Association:** `disable` (**Bắt buộc vô hiệu hóa** để ngăn tự động gán RTB mặc định).
- **Default Route Table Propagation:** `disable` (**Bắt buộc vô hiệu hóa** để ngăn lan truyền route tự động).
- **Auto Accept Shared Attachments:** `disable`.

---

## 5. Phụ Thuộc (Dependencies)
- Hoàn thành khởi tạo 4 VPCs tại [Lab 02.01](01-four-vpcs-and-subnets.md).

---

## 6. Kiểm Tra Đạt (Verification)
- [x] Transit Gateway `fabric-tgw` ở trạng thái `available` tại `ap-southeast-1` (`tgw-0fca495dfa8cfee17`).
- [x] `AmazonSideAsn = 64512`, `DnsSupport = enable`.
- [x] `DefaultRouteTableAssociation = disable`, `DefaultRouteTablePropagation = disable`.
- [x] Bằng chứng runtime đã thu thập: [`evidence/02-network/02-tgw-status.json`](../../evidence/02-network/02-tgw-status.json).

---

## 7. Cảnh Báo An Toàn & Rollback Plan
- **Cảnh báo an ninh:** Tuyệt đối không bật Default Association/Propagation, nếu không traffic sẽ bypass qua lại trực tiếp mà không đi qua cụm Suricata IDS/IPS.
- **Kế hoạch khôi phục (Rollback):**
  ```bash
  aws ec2 delete-transit-gateway --transit-gateway-id tgw-0fca495dfa8cfee17 --region ap-southeast-1
  ```
