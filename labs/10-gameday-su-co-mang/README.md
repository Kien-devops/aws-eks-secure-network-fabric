# Module 10 — GameDay Diễn Tập Sự Cố Mạng (Chaos & Fault Injection)

## 1. Tổng Quan Module

Module 10 đặc tả 5 kịch bản diễn tập sự cố mạng (GameDay) cấp enterprise nhằm chứng minh khả năng tự phục hồi, tính năng an ninh chặn chủ động (IPS Drop), tính năng định tuyến đối xứng (Appliance Mode) và quy trình ứng cứu sự cố SRE/DevOps trên hạ tầng AWS EKS Secure Network Fabric.

Mọi kịch bản đều có runtime evidence thực tế với đầy đủ mốc timestamps ($T_{fault}, T_{detect}, T_{mitigate}, T_{recover}$), chỉ số MTTD/MTTR và nhật ký CloudWatch Logs Insights.

---

## 2. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
[Module 02, 05, 06, 07, 09]
         │
         ▼
[10.01 Route Leak Bypass Test]
         │
         ▼
[10.02 Asymmetric Routing & Appliance Mode Test]
         │
         ▼
[10.03 Suricata Appliance Failure & GWLB Failover]
         │
         ▼
[10.04 Inline IPS Malicious Signature Drop Test]
         │
         ▼
[10.05 NAT Gateway Return-Path Loss & Recovery]
```

---

## 3. Danh Mục Bài Lab & Trạng Thái

| Mã Bài | Tên Bài Lab | Kịch Bản Tiêm Lỗi & Khắc Phục | Trạng Thái | File Đặc Tả |
| :--- | :--- | :--- | :--- | :--- |
| **10.01** | Route Leak Test | Sửa route Edge->Core bypass Inspection; đo lường phát hiện và khôi phục target TGW attachment | `RUNTIME_PASS` | [01-gameday-route-leak-test.md](01-gameday-route-leak-test.md) |
| **10.02** | Asymmetric Routing Test | Tắt Appliance Mode trên Inspection attachment; phân tích rủi ro TCP desync và khôi phục | `RUNTIME_PASS` | [02-gameday-asymmetric-routing-test.md](02-gameday-asymmetric-routing-test.md) |
| **10.03** | Suricata Appliance Loss | Giả lập mất appliance 1a; kiểm chứng GWLB Target Group failover sang 1b trong 32s | `RUNTIME_PASS` | [03-gameday-suricata-appliance-loss.md](03-gameday-suricata-appliance-loss.md) |
| **10.04** | Firewall Malicious Drop | Gửi marker plaintext `FABRIC_IPS_TEST` qua cổng 8084; xác nhận Suricata IPS drop và EVE alert SID 2026001 | `RUNTIME_PASS` | [04-gameday-firewall-malicious-drop.md](04-gameday-firewall-malicious-drop.md) |
| **10.05** | NAT Return-Path Loss | Xóa route `10.50.0.0/16` trên public NAT table 1a; ghi nhận blackhole một chiều và khôi phục MTTR ~1.8m | `RUNTIME_PASS` | [05-gameday-nat-return-failure.md](05-gameday-nat-return-failure.md) |

---

## 4. Danh Mục Tài Nguyên Tham Gia Diễn Tập (Resource Inventory)

| Tên Resource | Loại Resource | Phạm Vi VPC / Subnet | Trạng Thái Thực Tế |
| :--- | :--- | :--- | :--- |
| `fabric-tgw-rt-edge` | `AWS::EC2::TransitGatewayRouteTable` | TGW Global | Hoạt động bình thường (Target Inspection attachment) |
| `tgw-attach-inspection` | `AWS::EC2::TransitGatewayAttachment` | Inspection VPC (`10.60.0.0/16`) | Appliance Mode: `enable` |
| `fabric-gwlb-tg` | `AWS::ElasticLoadBalancingV2::TargetGroup` | Inspection VPC | 2 Instances Healthy (`i-09dfd64e9a8f1ca33`, `i-079730fdf83f4fbb4`) |
| `fabric-egress-public-rt-1a` | `AWS::EC2::RouteTable` | Egress VPC Public 1a | Khôi phục đầy đủ route về NFW endpoint AZ-a |
| `/aws/suricata/fabric-inspection-eve` | `AWS::Logs::LogGroup` | Region `ap-southeast-1` | Ghi nhận sự kiện SID 2026001 (`action: blocked`) |
