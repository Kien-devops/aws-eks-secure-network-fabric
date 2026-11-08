# Lab 02.03: Khởi Tạo TGW VPC Attachments (Appliance Mode) & 4 Route Tables

**Mã tài liệu:** `LAB-02-03`
**Trạng thái:** `RUNTIME_PASS`
**Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`

---

## 1. Mục Tiêu (Objective)
Đặc tả 4 Transit Gateway VPC Attachments (kích hoạt Appliance Mode cho Inspection và Egress) và 4 TGW Route Tables cô lập độc lập, loại bỏ hoàn toàn khả năng Route Leak.

---

## 2. Tài Nguyên (Resources)

### 2.1 TGW VPC Attachments (4 Attachments)
| Tên Logical | Định Danh Runtime (Snapshot) | VPC Gắn Kèm | Subnets Gắn Kèm (AZ-a / AZ-b) | Appliance Mode |
| :--- | :--- | :--- | :--- | :---: |
| `fabric-edge-tgw-attachment` | `tgw-attach-06219b0f6f3082f3e` | `fabric-edge-vpc` | `subnet-0ee88bbf364687ec6`, `subnet-027f9fd24d6ff94ca` | Disabled |
| `fabric-core-tgw-attachment` | `tgw-attach-0d9cc79cb91dafeb2` | `fabric-core-vpc` | `subnet-0b8fbf236704cd49f`, `subnet-067ef27abb3c9fc27` | Disabled |
| `fabric-insp-tgw-attachment` | `tgw-attach-0fb21514974415f35` | `fabric-inspection-vpc` | `subnet-0e260eae20eea3ccb`, `subnet-0a1481ce7d8302538` | **ENABLED** |
| `fabric-egress-tgw-attachment` | `tgw-attach-0646bdfa31c6c8e66` | `fabric-egress-vpc` | `subnet-0a9b70d43770f1e86`, `subnet-0b0653845a52c4f75` | **ENABLED** |

### 2.2 TGW Route Tables (4 Tables)
| Tên Logical | Định Danh Runtime (Snapshot) | Attachment Associated | Vai Trò Phân Đoạn |
| :--- | :--- | :--- | :--- |
| `fabric-tgw-edge-rt` | `tgw-rtb-004772ba5b83f2b17` | `fabric-edge-tgw-attachment` | Miền định tuyến Ingress Edge |
| `fabric-tgw-core-rt` | `tgw-rtb-03c493c67bc6dc820` | `fabric-core-tgw-attachment` | Miền định tuyến Workloads Core |
| `fabric-tgw-inspection-rt` | `tgw-rtb-01abf43ebf7f1b21f` | `fabric-insp-tgw-attachment` | Miền định tuyến Trả Luồng Sạch |
| `fabric-tgw-egress-rt` | `tgw-rtb-066c8310ab347bf30` | `fabric-egress-tgw-attachment` | Miền định tuyến Thoát & Trả Về |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-tgw-attachment` / `fabric-tgw-*-rt` | Toàn bộ 4 Attachments và 4 Route Tables |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ 4 Attachments và 4 Route Tables |
| `Environment` | `prod` | Toàn bộ tài nguyên TGW |
| `ManagedBy` | `manual` | Quản trị phân đoạn định tuyến thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### Ma Trận Định Tuyến Tĩnh TGW (RTB Transit Matrix)
| Bảng Định Tuyến | Đích (Destination CIDR) | Next Hop Target | Mục Đích Kỹ Thuật |
| :--- | :--- | :--- | :--- |
| **`fabric-tgw-edge-rt`** | `10.50.0.0/16`<br>`0.0.0.0/0` | `fabric-insp-tgw-attachment`<br>`fabric-egress-tgw-attachment` | Sang Core phải qua Inspection; ra Internet qua Egress. |
| **`fabric-tgw-core-rt`** | `10.40.0.0/16`<br>`0.0.0.0/0` | `fabric-insp-tgw-attachment`<br>`fabric-egress-tgw-attachment` | Về Edge phải qua Inspection; ra Internet qua Egress. |
| **`fabric-tgw-inspection-rt`** | `10.40.0.0/16`<br>`10.50.0.0/16` | `fabric-edge-tgw-attachment`<br>`fabric-core-tgw-attachment` | Chuyển tiếp traffic sạch về đích tương ứng. |
| **`fabric-tgw-egress-rt`** | `10.40.0.0/16`<br>`10.50.0.0/16` | `fabric-edge-tgw-attachment`<br>`fabric-core-tgw-attachment` | Chuyển tiếp traffic phản hồi từ Internet về Spoke VPC. |

---

## 5. Phụ Thuộc (Dependencies)
- Hoàn thành khởi tạo TGW tại [Lab 02.02](02-transit-gateway-setup.md).
- 4 Subnet TGW chuyên dụng (`/28`) tại 4 VPCs sẵn sàng.

---

## 6. Kiểm Tra Đạt (Verification)
- [x] Cả 4 VPC Attachments đều ở trạng thái `available`.
- [x] Cờ `ApplianceModeSupport` của `fabric-insp-tgw-attachment` và `fabric-egress-tgw-attachment` hiển thị `enable`.
- [x] 4 TGW Route Tables được phân tách và liên kết chính xác 1-1 với từng attachment.
- [x] Bằng chứng runtime đã thu thập: [`evidence/02-network/03-tgw-attachments-and-routes.json`](../../evidence/02-network/03-tgw-attachments-and-routes.json).

---

## 7. Cảnh Báo An Toàn & Rollback Plan
- **Cảnh báo tính đối xứng:** Bắt buộc bật Appliance Mode trên Inspection Attachment. Nếu tắt, lưu lượng TCP 2 chiều sẽ bị Suricata drop (chứng minh tại GameDay 10.02).
- **Kế hoạch khôi phục (Rollback):**
  ```bash
  for att_id in $(aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'TransitGatewayVpcAttachments[*].TransitGatewayAttachmentId' --output text); do
    aws ec2 delete-transit-gateway-vpc-attachment --region ap-southeast-1 --transit-gateway-attachment-id $att_id
  done
  ```
