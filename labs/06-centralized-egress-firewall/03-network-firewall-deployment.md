# 06.03 — Khởi Tạo AWS Network Firewall & Firewall Policy

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Triển khai cụm tường lửa tập trung AWS Network Firewall đa AZ trong Egress VPC.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo **AWS Network Firewall Policy** gắn kết Stateful Rule Group vừa tạo ở bài trước.
- Triển khai **AWS Network Firewall** (`fabric-egress-nfw`) đặt tại các Subnet chuyên dụng `fabric-egress-nfw-1a` và `fabric-egress-nfw-1b` trong `fabric-egress-vpc`.
- Kích hoạt cơ chế ghi log tập trung (Alert Logs và Flow Logs) đẩy trực tiếp về CloudWatch Log Groups.
- Thu thập **Firewall Endpoint IDs** (VPC Endpoint ENIs) tại từng AZ để phục vụ cấu hình bảng định tuyến.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Khởi Tạo Firewall Policy
1. Mở **VPC Console** tại Singapore (`ap-southeast-1`) -> Nhóm **Network Firewall** -> Chọn **Firewall policies**.
2. Nhấp nút cam **Create firewall policy**:
   - **Name:** `fabric-egress-nfw-policy`
   - **Description:** `Firewall policy for centralized egress inspection with domain allowlist`
3. **Stateless default actions:**
   - **Action for fragmented packets:** Chọn `Drop`.
   - **Action for all other packets:** Chọn `Forward to stateful rule groups`.
4. **Stateful rule groups:**
   - Nhấp **Add rule groups** -> Chọn **Add stateful rule groups**.
   - Tích chọn `fabric-egress-domain-allowlist-rg` đã tạo ở bài trước.
   - Nhấp **Add stateful rule group**.
5. Nhấp nút cam **Create firewall policy**.

---

### Bước 2: Khởi Tạo AWS Network Firewall
1. Tại menu bên trái VPC Console, chọn **Firewalls** -> Nhấp nút cam **Create firewall**.
2. **Firewall details:**
   - **Name:** `fabric-egress-nfw`
   - **Firewall policy:** Chọn `fabric-egress-nfw-policy`.
3. **VPC settings:**
   - **VPC:** Chọn `fabric-egress-vpc`.
   - **Firewall subnets (Chọn cả 2 AZs):**
     - `ap-southeast-1a`: Chọn subnet `fabric-egress-nfw-1a`.
     - `ap-southeast-1b`: Chọn subnet `fabric-egress-nfw-1b`.
4. **Tags:** `Project` = `aws-eks-secure-network-fabric`, `Environment` = `dev`.
5. Nhấp nút cam **Create firewall**.
> *Lưu ý: Quá trình triển khai AWS Network Firewall mất khoảng 3 - 5 phút để chuyển từ trạng thái `PROVISIONING` sang `READY`.*

---

### Bước 3: Cấu Hình Logging Đẩy Về CloudWatch Logs
1. Chọn firewall `fabric-egress-nfw` vừa tạo -> Mở tab **Firewall details** -> Cuộn xuống mục **Logging**.
2. Nhấp **Edit**:
   - **Log type 1 (Alerts):** Tích chọn `Alert` -> Destination: `CloudWatch log group` -> Nhập `/aws/network-firewall/fabric-egress-alerts`.
   - **Log type 2 (Flows):** Tích chọn `Flow` -> Destination: `CloudWatch log group` -> Nhập `/aws/network-firewall/fabric-egress-flows`.
3. Nhấp **Save**.

---

## 3. Xác Minh & Lấy Endpoint IDs (Verification)

Chạy lệnh kiểm tra trạng thái và lấy Endpoint IDs:
```bash
aws network-firewall describe-firewall \
  --firewall-name fabric-egress-nfw \
  --region ap-southeast-1 \
  --query 'FirewallStatus.{Status:Status,SyncStates:SyncStates}' \
  --output json
```
Ghi lại 2 giá trị `Attachment.EndpointId` tương ứng với Subnet `1a` và `1b` (ví dụ: `vpce-0123...` và `vpce-0456...`).

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] AWS Network Firewall ở trạng thái `READY` với 2 Endpoints tại 2 AZs.
- [ ] Tính năng ghi log Alert và Flow về CloudWatch Logs được kích hoạt thành công.

