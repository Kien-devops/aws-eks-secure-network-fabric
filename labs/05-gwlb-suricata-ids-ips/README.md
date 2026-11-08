# Module 05: GWLB & Suricata IDS/IPS (East-West Traffic Inspection)

Module này cung cấp các đặc tả tài nguyên triển khai hệ thống kiểm duyệt lưu lượng nội bộ giữa Edge và Core (East-West) sử dụng AWS Gateway Load Balancer, 2 Zonal GWLB Endpoints độc lập theo từng AZ, cụm Suricata EC2 xử lý GENEVE TLV options và kích hoạt TGW Appliance Mode để đảm bảo định tuyến đối xứng tuyệt đối (Symmetric Flow).

---

## 1. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
05.01 (2 Suricata EC2 Appliances: c6i.large Spot, Ubuntu 24.04, GENEVE 6081)
  │
  └──> 05.02 (Gateway Load Balancer & Target Group GENEVE)
         │
         └──> 05.03 (VPC Endpoint Service & 2 Zonal GWLB Endpoints: AZ-a, AZ-b)
                │
                └──> 05.04 (Cắt chuyển định tuyến East-West & Xác minh Luồng Đối Xứng)
```

---

## 2. Danh Mục Tài Nguyên (Resource Catalog)

| Tài Nguyên | Loại Resource | Số Lượng | Ghi Chú Kỹ Thuật |
| :--- | :--- | :---: | :--- |
| **Suricata EC2** | `AWS::EC2::Instance` | 2 | `fabric-suricata-1a` (`10.70.10.161`), `fabric-suricata-1b` (`10.70.11.137`), `SourceDestCheck: false` |
| **Security Group** | `AWS::EC2::SecurityGroup` | 1 | `fabric-suricata-sg` (Mở UDP 6081 & TCP 80 từ Inspection CIDR) |
| **Target Group** | `AWS::ElasticLoadBalancingV2::TargetGroup` | 1 | `fabric-suricata-tg` (Protocol GENEVE:6081, Health check HTTP:80) |
| **GWLB** | `AWS::ElasticLoadBalancingV2::LoadBalancer` | 1 | `fabric-gwlb` (Type gateway, Multi-AZ cross-zone enabled) |
| **Endpoint Service** | `AWS::EC2::VPCEndpointService` | 1 | `fabric-gwlb-endpoint-service` (Acceptance required: false) |
| **GWLB Endpoints** | `AWS::EC2::VPCEndpoint` | 2 | `fabric-gwlbe-1a` (AZ-a) và `fabric-gwlbe-1b` (AZ-b) |
| **VPC Route Tables** | `AWS::EC2::RouteTable` | 3 | `fabric-insp-tgw-rt-1a`, `fabric-insp-tgw-rt-1b`, `fabric-insp-gwlbe-rt` |

---

## 3. Danh Sách 4 Bài Lab Đặc Tả Chi Tiết

| Mã Lab | Tên Đặc Tả & Nội Dung Trọng Tâm | Trạng Thái | File Đặc Tả |
|---|---|:---:|---|
| **05.01** | **Suricata EC2 Appliances:** 2 instances c6i.large Spot xử lý GENEVE TLV trên UDP 6081. | `RUNTIME_PASS` | [01-suricata-ec2-instances.md](01-suricata-ec2-instances.md) |
| **05.02** | **GWLB & Target Group:** Giao thức GENEVE 6081, HTTP port 80 health checks. | `RUNTIME_PASS` | [02-gateway-load-balancer-and-target-group.md](02-gateway-load-balancer-and-target-group.md) |
| **05.03** | **Zonal GWLB Endpoints:** Khởi tạo 2 endpoints riêng biệt tại AZ-a và AZ-b. | `RUNTIME_PASS` | [03-gwlb-endpoints-creation.md](03-gwlb-endpoints-creation.md) |
| **05.04** | **Cutover East-West & Symmetric Flow:** Chuyển tuyến TGW, bắt tcpdump kiểm chứng đối xứng. | `RUNTIME_PASS` | [04-inspection-routing-and-symmetric-verification.md](04-inspection-routing-and-symmetric-verification.md) |
