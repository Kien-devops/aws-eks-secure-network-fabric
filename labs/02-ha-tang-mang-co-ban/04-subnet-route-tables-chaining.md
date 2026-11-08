# Lab 02.04: Cấu Hình Bảng Định Tuyến Subnet (Subnet Route Tables Chaining)

**Mã tài liệu:** `LAB-02-04`
**Trạng thái:** `RUNTIME_PASS`
**Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`

---

## 1. Mục Tiêu (Objective)
Đặc tả 16 bảng định tuyến tĩnh VPC (RTB Static) thực thi chuỗi dịch vụ kiểm soát an ninh (Service Chaining), bảo đảm cô lập vùng dữ liệu và thiết lập các tuyến đường về (Return Paths) chống blackhole.

---

## 2. Tài Nguyên (Resources)

### 2.1 Bảng Định Tuyến Tĩnh VPC (16 Route Tables)
| VPC | Tên Bảng Định Tuyến | Định Danh Runtime | Subnets Gắn Kèm | Vai Trò An Ninh |
| :--- | :--- | :--- | :--- | :--- |
| **Edge** | `fabric-edge-public-rt` | `rtb-0c5a68767a6fe2926` | `public-1a`, `public-1b` | Ingress Public ALB |
| **Edge** | `fabric-edge-private-rt` | `rtb-00cd096fd0d4a2615` | `nodes-1a/1b`, `vpce-1a/1b` | EKS `edge-frontend` Nodes |
| **Edge** | `fabric-edge-tgw-rt` | `rtb-0e6e7436bb74cdf73` | `tgw-1a`, `tgw-1b` | TGW Attachment (Chỉ có local route) |
| **Core** | `fabric-core-private-rt` | `rtb-00ac268964554cc7e` | `nodes-1a/1b`, `vpce-1a/1b` | EKS `core-service` Nodes |
| **Core** | `fabric-core-data-rt` | `rtb-0df8c388148a51656` | `data-1a`, `data-1b` | Aurora DB & Redis (Air-gapped) |
| **Core** | `fabric-core-tgw-rt` | `rtb-047cf904c6c014554` | `tgw-1a`, `tgw-1b` | TGW Attachment (Chỉ có local route) |
| **Insp** | `fabric-insp-tgw-rt-1a` | `rtb-0b04448561b80d486` | `insp-tgw-1a` | Ingress TGW AZ-a |
| **Insp** | `fabric-insp-tgw-rt-1b` | `rtb-026ce1b95a394d8c1` | `insp-tgw-1b` | Ingress TGW AZ-b |
| **Insp** | `fabric-insp-gwlbe-rt` | `rtb-0378f50d79f1ed01f` | `gwlbe-1a`, `gwlbe-1b` | GWLB Endpoints |
| **Insp** | `fabric-insp-fw-rt` | `rtb-00b06850e681ef0e6` | `insp-fw-1a`, `insp-fw-1b` | Cụm Suricata EC2 (GENEVE 6081) |
| **Egress** | `fabric-egress-tgw-rt-1a` | `rtb-0e44e9ee6af736348` | `egress-tgw-1a` | Ingress TGW AZ-a |
| **Egress** | `fabric-egress-tgw-rt-1b` | `rtb-0f49dc7e1ab7a050d` | `egress-tgw-1b` | Ingress TGW AZ-b |
| **Egress** | `fabric-egress-fw-rt-1a` | `rtb-0f71ea39c116e5857` | `egress-fw-1a` | Network Firewall Endpoint AZ-a |
| **Egress** | `fabric-egress-fw-rt-1b` | `rtb-04406e0f6edaaa3c8` | `egress-fw-1b` | Network Firewall Endpoint AZ-b |
| **Egress** | `fabric-egress-public-rt-1a` | `rtb-0c759f9192847ad8b` | `egress-public-1a` | NAT Gateway A & Return Route |
| **Egress** | `fabric-egress-public-rt-1b` | `rtb-086d9ec09e2b732d7` | `egress-public-1b` | NAT Gateway B & Return Route |

---

## 3. Thẻ Định Danh (Tags)

| Khóa (Key) | Giá Trị (Value) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-rt` | Toàn bộ 16 VPC Route Tables |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ 16 VPC Route Tables |
| `Environment` | `prod` | Toàn bộ bảng định tuyến |
| `ManagedBy` | `manual` | Quản trị chuỗi định tuyến subnet |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### Ma Trận Định Tuyến Tĩnh VPC (RTB Static Matrix)
| Bảng Định Tuyến | Đích (Destination) | Next Hop Target | Nguyên Tắc Kỹ Thuật |
| :--- | :--- | :--- | :--- |
| `fabric-edge-public-rt` | `0.0.0.0/0`<br>`10.50.0.0/16` | `fabric-edge-igw`<br>`fabric-tgw` | Đón Internet; gọi sang Core qua TGW. |
| `fabric-edge-private-rt` | `0.0.0.0/0`<br>`10.50.0.0/16` | `fabric-tgw`<br>`fabric-tgw` | Toàn bộ outbound và East-West đi qua TGW. |
| `fabric-edge-tgw-rt` | `10.40.0.0/16` | `local` | **Chỉ local route**, chống vòng lặp tại TGW attachment. |
| `fabric-core-private-rt` | `0.0.0.0/0`<br>`10.40.0.0/16` | `fabric-tgw`<br>`fabric-tgw` | Ra ngoài qua Egress; trả lời Edge qua TGW. |
| `fabric-core-data-rt` | `10.50.0.0/16`<br>`10.40.0.0/16` | `local`<br>`fabric-tgw` | **Zero 0.0.0.0/0 (Air-gapped)**; chỉ mở cổng 5432/6379 nội bộ. |
| `fabric-core-tgw-rt` | `10.50.0.0/16` | `local` | **Chỉ local route**, chuyển tiếp trực tiếp vào Core Nodes. |
| `fabric-insp-tgw-rt-1a/1b` | `10.40.0.0/16`, `10.50.0.0/16` | GWLBe Endpoint AZ tương ứng | Ép lưu lượng East-West vào GWLB cùng AZ. |
| `fabric-insp-gwlbe-rt` | `10.40.0.0/16`, `10.50.0.0/16` | `fabric-tgw` | Đẩy gói tin đã kiểm duyệt sạch quay lại TGW. |
| `fabric-insp-fw-rt` | `10.70.0.0/16` | `local` | One-arm GENEVE giao tiếp trên cổng UDP 6081. |
| `fabric-egress-tgw-rt-1a/1b` | `0.0.0.0/0` | NFW Endpoint AZ tương ứng | Ép lưu lượng Internet qua AWS Network Firewall. |
| `fabric-egress-fw-rt-1a/1b` | `0.0.0.0/0` | NAT Gateway AZ tương ứng | Chuyển tiếp traffic sạch sang NAT cùng AZ. |
| `fabric-egress-public-rt-1a/1b` | `0.0.0.0/0`<br>`10.40.0.0/16`, `10.50.0.0/16` | `fabric-egress-igw`<br>NFW Endpoint AZ tương ứng | **Return Route bắt buộc**: Đưa gói tin phản hồi quay lại NFW & TGW. |

---

## 5. Phụ Thuộc (Dependencies)
- Hoàn thành khởi tạo 4 VPC Attachments tại [Lab 02.03](03-tgw-route-tables-and-attachments.md).

---

## 6. Kiểm Tra Đạt (Verification)
- [x] Toàn bộ 28 subnets được gán đúng vào các Route Tables tương ứng.
- [x] Data Subnet cô lập hoàn toàn khỏi Internet (không có default route `0.0.0.0/0`).
- [x] Spoke TGW subnets chỉ chứa local route (chống routing loop).
- [x] Egress Public Subnet có đầy đủ route trả về Spoke CIDRs qua NFW Endpoint.
- [x] Bằng chứng runtime đã thu thập: [`evidence/02-network/04-subnet-route-tables.json`](../../evidence/02-network/04-subnet-route-tables.json).

---

## 7. Cảnh Báo An Toàn & Rollback Plan
- **Cảnh báo mất kết nối NAT (Blackhole):** Nếu xóa tuyến trả về `10.40.0.0/16` hoặc `10.50.0.0/16` trên `fabric-egress-public-rt`, gói SYN-ACK phản hồi từ Internet sẽ bị NAT Gateway đẩy ra IGW và bị drop (chứng minh tại GameDay 10.05).
- **Kế hoạch khôi phục (Rollback):**
  ```bash
  aws ec2 create-route --route-table-id rtb-0c759f9192847ad8b --destination-cidr-block 10.50.0.0/16 --vpc-endpoint-id vpce-008c9b7972ba12c2c --region ap-southeast-1
  ```
