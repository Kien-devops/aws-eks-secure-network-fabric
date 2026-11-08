# 10.05 — GameDay Kịch Bản 5: Mất Tuyến Đường Về Tại Cổng Ra Tập Trung (NAT Return-Path Loss)

> **Mã bài lab:** `10.05`
> **Trạng thái:** `RUNTIME_PASS`
> **Thời gian dự kiến:** 45 phút
> **Chi phí ước tính:** $0.00 USD (Khai thác hạ tầng hiện hữu)
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)

---

## 1. Mục Tiêu (Objective)

Đặc tả kịch bản diễn tập mô phỏng sự cố mất tuyến đường về (One-Way Blackhole Drop) tại Public NAT Subnet trong Egress VPC khi route hồi đáp RFC1918 bị xóa. Xác thực quy trình phát hiện bằng VPC Flow Logs, đo lường chỉ số MTTD/MTTR và khôi phục tuyến đường về NFW endpoint AZ-a với thời gian gián đoạn tối thiểu.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | VPC / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-egress-public-rt-1a` | `AWS::EC2::RouteTable` | Egress VPC Public 1a | `rtb-0c759f9192847ad8b` |
| `fabric-egress-public-rt-1b` | `AWS::EC2::RouteTable` | Egress VPC Public 1b | `rtb-096055d7f0203f1eb` |
| `fabric-egress-nfw-vpce-1a` | `AWS::EC2::VPCEndpoint` | Egress NFW Subnet 1a | `vpce-008c9b7972ba12c2c` |
| `fabric-egress-nat-1a` | `AWS::EC2::NatGateway` | Egress Public Subnet 1a | `nat-090956bda19ee8ee4` |
| `/aws/vpc/fabric-egress-flow-logs` | `AWS::Logs::LogGroup` | Region `ap-southeast-1` | `arn:aws:logs:ap-southeast-1:123456789012:log-group:/aws/vpc/fabric-egress-flow-logs` |
| `egress-test` | `k8s:Deployment` | Core Cluster `fabric-apps` | `deployment/egress-test` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-gameday` | Toàn bộ tài nguyên kiểm thử |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ tài nguyên kiểm thử |
| `Environment` | `prod` | Phân vùng môi trường diễn tập |
| `ManagedBy` | `manual` | Quản lý phục vụ bài GameDay thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Bảng Định Tuyến Public NAT Subnet 1a (Baseline vs Fault vs Restored)

| Trạng Thái | Destination | Target Next Hop | Hành Động Kỹ Thuật |
| :--- | :--- | :--- | :--- |
| **Baseline** | `0.0.0.0/0` | `igw-0123456789abcdef0` | Egress ra Internet qua Internet Gateway |
| **Baseline** | `10.50.0.0/16` | `vpce-008c9b7972ba12c2c` | Trả gói tin về Core VPC qua NFW Endpoint 1a |
| **Baseline** | `10.40.0.0/16` | `vpce-008c9b7972ba12c2c` | Trả gói tin về Edge VPC qua NFW Endpoint 1a |
| **Baseline** | `10.80.0.0/16` | `local` | Định tuyến nội bộ Egress VPC |
| **Fault Injected** | `10.50.0.0/16` | **REMOVED** | Gây blackhole một chiều (Outbound SYN OK, SYN-ACK bị NAT drop) |
| **Restored** | `10.50.0.0/16` | `vpce-008c9b7972ba12c2c` | Bổ sung lại route khôi phục kết nối |

### 4.2 Truy Vấn Phân Tích Sự Cố (VPC Flow Logs Insights)
```sql
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, action, protocol
| filter (srcAddr like "10.50." or dstAddr like "10.50.") and dstPort = 443
| sort @timestamp desc
| limit 20
```

### 4.3 Khung Thời Gian & Chỉ Số SRE Đo Đạc
* $T_{fault}$: Mốc tiêm lỗi xóa route `10.50.0.0/16`.
* $T_{detect}$: Mốc phát hiện kết nối timeout qua VPC Flow Logs.
* $T_{mitigate}$: Mốc thực thi lệnh tạo lại route qua AWS CLI/Console.
* $T_{recover}$: Mốc xác nhận kết nối phục hồi hoàn toàn ($MTTR \approx 1.8$ phút).

---

## 5. Phụ Thuộc (Dependencies)

* [Module 06](../06-centralized-egress-firewall/README.md): Egress VPC, NAT Gateways per AZ và AWS Network Firewall Endpoints.
* [Module 02](../02-ha-tang-mang-co-ban/05-vpc-flow-logs-cloudwatch.md): VPC Flow Logs đẩy về CloudWatch Log Group.
* [Module 04](../04-phan-bo-workloads/README.md): Cụm Core EKS workload đang hoạt động và có nhu cầu kết nối Internet.

---

## 6. Kiểm Tra Đạt (Verification)

| Hạng Mục | Lệnh Kiểm Tra / Metric | Kỳ Vọng Đạt |
| :--- | :--- | :--- |
| **Mô Phỏng Blackhole** | `curl --max-time 5 -I https://github.com` từ Core Pod | 100% kết nối đi qua AZ-1a NAT bị timeout (`curl: (28) Connection timed out`) |
| **Đối Chứng Multi-AZ** | Kết nối đi qua AZ-1b NAT | Kết nối thành công HTTP 200 chứng minh tính cô lập lỗi theo AZ |
| **VPC Flow Logs** | Query `/aws/vpc/fabric-egress-flow-logs` | Ghi nhận outbound SYN thành công nhưng thiếu return flow tương ứng |
| **Phục Hồi Hoàn Toàn** | Thực hiện 10 requests egress liên tục sau khi add route | 10/10 requests HTTP 200 OK, MTTR $\le 3$ phút |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

> [!WARNING]
> Chỉ thực hiện tiêm lỗi trên một AZ đơn lẻ (AZ-1a) trong phiên diễn tập. Không được xóa đồng thời route trên cả 2 AZ để tránh làm gián đoạn toàn bộ hệ thống egress của production.

### Lệnh Khôi Phục Khẩn Cấp (Emergency Rollback)
Nếu giao diện Console bị treo, thực thi ngay lệnh khôi phục tuyến đường về qua AWS CLI:
```bash
aws ec2 create-route \
  --region ap-southeast-1 \
  --route-table-id rtb-0c759f9192847ad8b \
  --destination-cidr-block 10.50.0.0/16 \
  --vpc-endpoint-id vpce-008c9b7972ba12c2c
```
Kiểm tra lại trạng thái route sau khi add:
```bash
aws ec2 describe-route-tables \
  --region ap-southeast-1 \
  --route-table-ids rtb-0c759f9192847ad8b \
  --query 'RouteTables[0].Routes[?DestinationCidrBlock==`10.50.0.0/16`]'
```
