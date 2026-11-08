# 05.01 — Đặc Tả Khởi Tạo 2 Suricata Appliances EC2 & Cấu Hình Xử Lý GENEVE TLV

> **Mã bài lab:** `05.01`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — Subnets: `fabric-insp-fw-1a`, `fabric-insp-fw-1b`
> **File bằng chứng:** `evidence/05-gwlb/01-suricata-instances.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả hạ tầng máy ảo kiểm tra gói tin sâu Suricata IDS/IPS (EC2 Spot `c6i.large`, Ubuntu 24.04) chạy đa AZ trong Inspection VPC, tích hợp daemon xử lý GENEVE Type 1 Option 1 TLV metadata và tắt Source/Dest Check để làm backend cho AWS Gateway Load Balancer.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-suricata-sg` | `AWS::EC2::SecurityGroup` | `fabric-inspection-vpc` | Chờ runtime ID |
| `fabric-suricata-1a` | `AWS::EC2::Instance` | `fabric-insp-fw-1a` (`ap-southeast-1a`) | `i-089127472b112deff` (Private IP: `10.70.10.161`) |
| `fabric-suricata-1b` | `AWS::EC2::Instance` | `fabric-insp-fw-1b` (`ap-southeast-1b`) | `i-091e84ae2b923eea2` (Private IP: `10.70.11.137`) |
| `fabric-ssm-instance-profile` | `AWS::IAM::InstanceProfile` | Global (IAM) | Gắn `AmazonSSMManagedInstanceCore` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-suricata-1a` / `fabric-suricata-1b` | Máy chủ EC2, Security Group |
| `Project` | `aws-eks-secure-network-fabric` | EC2 Instances, Security Group, ENIs |
| `Environment` | `prod` | EC2 Instances, Security Group, ENIs |
| `ManagedBy` | `manual` | Quản trị thiết bị mạng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Security Group Bảo Vệ Appliance (`fabric-suricata-sg`)

- **Inbound Rules:**
  - `UDP 6081` (GENEVE) từ Inspection VPC CIDR (`10.70.0.0/16`).
  - `TCP 80` (HTTP Health Check probe từ GWLB) từ Inspection VPC CIDR (`10.70.0.0/16`).
- **Outbound Rules:** Cho phép toàn bộ traffic ra nội bộ.

### 4.2 Cấu Hình Kỹ Thuật Máy Chủ EC2 Suricata

| Thuộc Tính | Máy ảo 1a (`fabric-suricata-1a`) | Máy ảo 1b (`fabric-suricata-1b`) | Lý Do Thiết Kế |
| :--- | :--- | :--- | :--- |
| **Instance Type** | `c6i.large` (Compute Optimized) | `c6i.large` (Compute Optimized) | Tối ưu hóa năng lực tính toán giải mã GENEVE và xử lý quy tắc Suricata. |
| **Capacity Type** | `SPOT` | `SPOT` | Giảm 55% chi phí vận hành trong môi trường lab. |
| **Subnet Binding** | `fabric-insp-fw-1a` (`10.70.10.0/24`) | `fabric-insp-fw-1b` (`10.70.11.0/24`) | Phân bổ đa vùng sẵn sàng (Multi-AZ HA). |
| **Source/Dest Check** | `false` (Disabled) | `false` (Disabled) | Bắt buộc đối với thiết bị middlebox chuyển tiếp gói tin của bên thứ 3. |
| **Tunnel Handler** | `gwlbtun` v3.3 (Cổng UDP 6081) | `gwlbtun` v3.3 (Cổng UDP 6081) | Xử lý GENEVE Type 1 Option 1 TLV metadata cho GWLB. |
| **Suricata Mode** | Inline NFQUEUE (`-q 0`) | Inline NFQUEUE (`-q 0`) | Chặn (`DROP`) hoặc ghi nhật ký (`ALERT`) gói tin mã độc. |
| **Kernel Settings** | `net.ipv4.ip_forward=1`, `rp_filter=0` | `net.ipv4.ip_forward=1`, `rp_filter=0` | Bật IP forwarding và tắt reverse path filtering trên interface tunnel. |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.01`: Subnets `fabric-insp-fw-1a` và `fabric-insp-fw-1b` sẵn sàng.
- Phụ thuộc vào IAM Instance Profile `fabric-ssm-instance-profile` để quản trị không mở SSH port 22.
- Là điều kiện tiên quyết cho Gateway Load Balancer Target Group tại `05.02`.

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái EC2 Instances** | `aws ec2 describe-instances --filters "Name=tag:Role,Values=firewall-appliance"` | Cả 2 máy ảo `i-089127472b112deff` và `i-091e84ae2b923eea2` ở trạng thái `running`. |
| **Source/Dest Check** | Kiểm tra trường `SourceDestCheck` của 2 instances | Giá trị chính xác là `false`. |
| **Cổng Lắng Nghe Mạng** | Kiểm tra cổng trên instance qua SSM | UDP `6081` (gwlbtun) và TCP `80` (health probe) đang LISTEN. |
| **Health Check Response** | `curl -i http://127.0.0.1:80/` | Trả về `HTTP/1.1 200 OK` (Health check: Healthy). |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo gián đoạn luồng mạng (Fail-Closed):** Nếu tiến trình Suricata hoặc gwlbtun gặp sự cố, các gói tin sẽ bị chặn hoàn toàn do iptables NFQUEUE không cấu hình bypass.
- **Quy trình Rollback:**
  ```bash
  # Hủy 2 máy ảo EC2 Suricata
  aws ec2 terminate-instances --region ap-southeast-1 --instance-ids i-089127472b112deff i-091e84ae2b923eea2

  # Xóa Security Group sau khi instances bị hủy
  aws ec2 delete-security-group --region ap-southeast-1 --group-id <SuricataSGId>
  ```
