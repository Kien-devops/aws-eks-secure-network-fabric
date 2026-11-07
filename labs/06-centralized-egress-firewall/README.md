# Module 06: Centralized Egress Firewall (AWS Network Firewall & NAT)

Module này hướng dẫn triển khai kiến trúc tường lửa ra Internet tập trung (Centralized Egress) sử dụng AWS Network Firewall kết hợp 2 NAT Gateways đa AZ, cấu hình Domain Allowlist Stateful Rules, kích hoạt TGW Appliance Mode và khắc phục triệt để lỗi Return Path để bảo toàn tính toàn vẹn của tường lửa.

## Danh Sách Bài Lab

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **06.01** | **NAT Gateways & Elastic IPs:** 2 NAT Gateways tại Public Subnets AZ-a và AZ-b. | `COMPLETED` | [01-nat-gateways-per-az.md](01-nat-gateways-per-az.md) |
| **06.02** | **Network Firewall Rule Groups:** Stateful Domain Allowlist và Suricata Drop rules. | `COMPLETED` | [02-network-firewall-rule-groups.md](02-network-firewall-rule-groups.md) |
| **06.03** | **Network Firewall Deployment:** Triển khai NFW Endpoints, bật Egress Appliance Mode. | `COMPLETED` | [03-network-firewall-deployment.md](03-network-firewall-deployment.md) |
| **06.04** | **Egress Return Path & Domain Test:** Cấu hình chuẩn Return Path và xác minh Allow/Block. | `DRAFT` | [04-egress-routing-and-domain-filtering-test.md](04-egress-routing-and-domain-filtering-test.md) |
