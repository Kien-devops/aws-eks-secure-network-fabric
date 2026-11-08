# 06.04 — Đặc Tả Bảng Định Tuyến Egress Return Path & Kiểm Thử Lọc Tên Miền

> **Mã bài lab:** `06.04`
> **Trạng thái tài liệu:** `READY_TO_RUN`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — Subnets: Egress VPC
> **File bằng chứng:** `evidence/06-firewall/04-egress-domain-filter-test.log`

---

## 1. Mục Tiêu (Objective)

Đặc tả 6 bảng định tuyến phân tách theo từng vùng sẵn sàng (AZ) trong Centralized Egress VPC nhằm ép toàn bộ lưu lượng Egress chiều đi và chiều về (Return Path) phải đi xuyên qua AWS Network Firewall trước khi tới NAT Gateway, đồng thời kiểm thử tính hiệu quả của chính sách lọc tên miền L7.

---

## 2. Tài Nguyên (Resources)

| Tên Tài Nguyên | Loại Resource | Vị Trí / Subnet Gắn | Runtime ID / ARN |
| :--- | :--- | :--- | :--- |
| `fabric-egress-tgw-rt-1a` | `AWS::EC2::RouteTable` | `fabric-egress-tgw-1a` (`10.80.0.0/28`) | Chờ runtime ID |
| `fabric-egress-tgw-rt-1b` | `AWS::EC2::RouteTable` | `fabric-egress-tgw-1b` (`10.80.0.16/28`) | Chờ runtime ID |
| `fabric-egress-fw-rt-1a` | `AWS::EC2::RouteTable` | `fabric-egress-fw-1a` (`10.80.1.0/28`) | Chờ runtime ID |
| `fabric-egress-fw-rt-1b` | `AWS::EC2::RouteTable` | `fabric-egress-fw-1b` (`10.80.1.16/28`) | Chờ runtime ID |
| `fabric-egress-public-rt-1a` | `AWS::EC2::RouteTable` | `fabric-egress-public-1a` (`10.80.10.0/24`) | Chờ runtime ID |
| `fabric-egress-public-rt-1b` | `AWS::EC2::RouteTable` | `fabric-egress-public-1b` (`10.80.11.0/24`) | Chờ runtime ID |

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-egress-*-rt` | 6 Bảng định tuyến Egress VPC |
| `Project` | `aws-eks-secure-network-fabric` | 6 Bảng định tuyến Egress VPC |
| `Environment` | `prod` | 6 Bảng định tuyến Egress VPC |
| `RoutingDomain` | `centralized-egress` | Phân đoạn lưu lượng Egress |
| `ManagedBy` | `manual` | Quản trị chính sách định tuyến |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Ma Trận Định Tuyến Phân Tách Theo AZ Trong Egress VPC

| Bảng Định Tuyến | Subnet Gắn | CIDR Đích | Next Hop Target | AZ | Mục Đích Thiết Kế |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **`fabric-egress-tgw-rt-1a`** | `fabric-egress-tgw-1a` | `0.0.0.0/0` | `vpce-008c9b7972ba12c2c` (NFW 1a) | `1a` | Gói tin từ TGW vào AZ-a phải gửi sang Firewall AZ-a. |
| **`fabric-egress-tgw-rt-1b`** | `fabric-egress-tgw-1b` | `0.0.0.0/0` | `vpce-0a4193a072d8c041f` (NFW 1b) | `1b` | Gói tin từ TGW vào AZ-b phải gửi sang Firewall AZ-b. |
| **`fabric-egress-fw-rt-1a`** | `fabric-egress-fw-1a` | `0.0.0.0/0`<br>`10.40.0.0/16`<br>`10.50.0.0/16` | `nat-02df31dd744888594` (NAT 1a)<br>`fabric-tgw`<br>`fabric-tgw` | `1a` | Sau kiểm tra: ra Internet qua NAT 1a hoặc trả về Spoke qua TGW. |
| **`fabric-egress-fw-rt-1b`** | `fabric-egress-fw-1b` | `0.0.0.0/0`<br>`10.40.0.0/16`<br>`10.50.0.0/16` | `nat-048410a645ccfea3e` (NAT 1b)<br>`fabric-tgw`<br>`fabric-tgw` | `1b` | Sau kiểm tra: ra Internet qua NAT 1b hoặc trả về Spoke qua TGW. |
| **`fabric-egress-public-rt-1a`** | `fabric-egress-public-1a` | `0.0.0.0/0`<br>`10.40.0.0/16`<br>`10.50.0.0/16` | `fabric-egress-igw`<br>`vpce-008c9b7972ba12c2c` (NFW 1a)<br>`vpce-008c9b7972ba12c2c` (NFW 1a) | `1a` | **Return Path Sống Còn:** Gói tin quay về từ Internet BẮT BUỘC gửi qua Firewall, cấm gửi thẳng về TGW. |
| **`fabric-egress-public-rt-1b`** | `fabric-egress-public-1b` | `0.0.0.0/0`<br>`10.40.0.0/16`<br>`10.50.0.0/16` | `fabric-egress-igw`<br>`vpce-0a4193a072d8c041f` (NFW 1b)<br>`vpce-0a4193a072d8c041f` (NFW 1b) | `1b` | **Return Path Sống Còn:** Gói tin quay về từ Internet BẮT BUỘC gửi qua Firewall, cấm gửi thẳng về TGW. |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `06.01`: Cụm NAT Gateways `fabric-nat-gw-1a/b` và IGW `fabric-egress-igw`.
- Phụ thuộc vào `06.03`: Hai Firewall Endpoints `vpce-008c9b7972ba12c2c` (1a) và `vpce-0a4193a072d8c041f` (1b) ở trạng thái `READY`.
- Phụ thuộc vào `03.03`, `04.04`: Worker nodes và pods trong cụm EKS để thực thi lệnh kiểm thử curl.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Tên miền Cho Phép (Allowlist)** | `kubectl exec <pod> -- curl -Iv https://github.com --connect-timeout 5` | `HTTP/2 200` hoặc `HTTP/1.1 200 OK` (Bắt tay TLS thành công). |
| **Tên miền Bị Chặn (Non-Allowlist)** | `kubectl exec <pod> -- curl -Iv https://example.com --connect-timeout 5` | `Connection timed out` sau 5s do Network Firewall DROP gói tin. |
| **Nhật ký Cảnh báo CloudWatch** | `aws logs filter-log-events --log-group-name /aws/network-firewall/fabric-egress-alerts` | Ghi nhận chi tiết bản ghi DROP sự kiện kết nối tới domain trái phép. |
| **Không Bị Lệch AZ (Zonal Isolation)** | Kiểm tra IP nguồn NAT tương ứng theo AZ của Pod | Pod tại AZ-a đi ra bằng NAT 1a; Pod tại AZ-b đi ra bằng NAT 1b. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo lỗi định tuyến bất đối xứng (NAT Return Bypass):** Tuyệt đối không trỏ `10.40.0.0/16` hoặc `10.50.0.0/16` trong Public Route Table về TGW. Nếu trỏ về TGW, lưu lượng chiều về sẽ bypass tường lửa, gây mất đồng bộ trạng thái TCP và rớt gói tin.
- **Quy trình Rollback:**
  ```bash
  # Tạm thời khóa lưu lượng egress hoặc khôi phục bảng định tuyến trước cutover
  aws ec2 replace-route --region ap-southeast-1 --route-table-id <TgwRt1aId> --destination-cidr-block 0.0.0.0/0 --gateway-id <OldTarget>
  ```
