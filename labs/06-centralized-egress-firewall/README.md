# Module 06: Centralized Egress Firewall (AWS Network Firewall & NAT)

Module này cung cấp các đặc tả tài nguyên triển khai kiến trúc tường lửa ra Internet tập trung (Centralized Egress) sử dụng AWS Network Firewall kết hợp 2 NAT Gateways đa AZ, cấu hình Domain Allowlist Stateful Rules, kích hoạt TGW Appliance Mode và bảo toàn tính toàn vẹn của Return Path.

---

## 1. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
06.01 (2 NAT Gateways & Elastic IPs đa AZ tại Public Subnets)
  │
  └──> 06.02 (Network Firewall Rule Groups: Domain Allowlist & Suricata Malicious Drop)
         │
         └──> 06.03 (Triển khai AWS Network Firewall đa AZ, Log Groups & Egress Appliance Mode)
                │
                └──> 06.04 (Bảng định tuyến Egress Return Path & Kiểm thử lọc tên miền L7)
```

---

## 2. Danh Mục Tài Nguyên (Resource Catalog)

| Tài Nguyên | Loại Resource | Số Lượng | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :--- |
| **Elastic IPs** | `AWS::EC2::EIP` | 2 | `fabric-nat-eip-1a`, `fabric-nat-eip-1b` |
| **NAT Gateways** | `AWS::EC2::NatGateway` | 2 | `fabric-nat-gw-1a`, `fabric-nat-gw-1b` (Public subnets A/B) |
| **Stateful Rule Groups** | `AWS::NetworkFirewall::RuleGroup` | 2 | `fabric-egress-domain-allowlist-rg`, `fabric-egress-malicious-drop-rg` |
| **Firewall Policy** | `AWS::NetworkFirewall::FirewallPolicy` | 1 | `fabric-egress-fw-policy` (Default action order) |
| **Network Firewall** | `AWS::NetworkFirewall::Firewall` | 1 | `fabric-egress-nfw` (2 Zonal Endpoints `vpce-***`) |
| **CloudWatch Log Groups** | `AWS::Logs::LogGroup` | 2 | `/aws/network-firewall/fabric-egress-alerts`, `/aws/network-firewall/fabric-egress-flows` (7 days) |
| **VPC Route Tables** | `AWS::EC2::RouteTable` | 6 | 2 TGW RTBs, 2 FW RTBs, 2 Public RTBs (Return path qua NFW) |

---

## 3. Danh Sách 4 Bài Lab Đặc Tả Chi Tiết

| Mã Lab | Tên Đặc Tả & Nội Dung Trọng Tâm | Trạng Thái | File Đặc Tả |
|---|---|:---:|---|
| **06.01** | **NAT Gateways & Elastic IPs:** 2 NAT Gateways tại Public Subnets AZ-a và AZ-b. | `RUNTIME_PASS` | [01-nat-gateways-per-az.md](01-nat-gateways-per-az.md) |
| **06.02** | **Network Firewall Rule Groups:** Stateful Domain Allowlist và Suricata Drop rules. | `RUNTIME_PASS` | [02-network-firewall-rule-groups.md](02-network-firewall-rule-groups.md) |
| **06.03** | **Network Firewall Deployment:** Triển khai NFW Endpoints, bật Egress Appliance Mode. | `RUNTIME_PASS` | [03-network-firewall-deployment.md](03-network-firewall-deployment.md) |
| **06.04** | **Egress Return Path & Domain Test:** Cấu hình chuẩn Return Path và xác minh Allow/Block. | `READY_TO_RUN` | [04-egress-routing-and-domain-filtering-test.md](04-egress-routing-and-domain-filtering-test.md) |
