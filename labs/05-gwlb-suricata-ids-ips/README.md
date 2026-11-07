# Module 05: GWLB & Suricata IDS/IPS (East-West Traffic Inspection)

Module này hướng dẫn triển khai hệ thống kiểm duyệt lưu lượng nội bộ giữa Edge và Core (East-West) sử dụng AWS Gateway Load Balancer, 2 Zonal GWLB Endpoints độc lập theo từng AZ, cụm Suricata EC2 xử lý GENEVE TLV options và kích hoạt TGW Appliance Mode để đảm bảo định tuyến đối xứng tuyệt đối (Symmetric Flow).

## Danh Sách Bài Lab

Bootstrap cần AMI đã chuẩn bị hoặc management egress tạm được phép; 05.01 ghi chi tiết đường SSM/build và gỡ ngoại lệ. Tunnel handler giải đóng gói GENEVE, Suricata NFQUEUE kiểm tra inline; không giải mã HTTPS. Cross-zone bật để kết nối mới có target còn sống khi mất một AZ; đối xứng là cùng flow qua cùng appliance hai chiều, không bắt buộc appliance cùng AZ nguồn. Giữ DRAFT đến khi controls, drop EVE, fail-closed và reboot persistence được chạy thật.

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **05.01** | **Suricata EC2 Appliances:** 2 instances c6i.large Spot xử lý GENEVE TLV trên UDP 6081. | `COMPLETED` | [01-suricata-ec2-instances.md](01-suricata-ec2-instances.md) |
| **05.02** | **GWLB & Target Group:** Giao thức GENEVE 6081, HTTP port 80 health checks. | `COMPLETED` | [02-gateway-load-balancer-and-target-group.md](02-gateway-load-balancer-and-target-group.md) |
| **05.03** | **Zonal GWLB Endpoints:** Khởi tạo 2 endpoints riêng biệt tại AZ-a và AZ-b. | `COMPLETED` | [03-gwlb-endpoints-creation.md](03-gwlb-endpoints-creation.md) |
| **05.04** | **Cutover East-West & Symmetric Flow:** Chuyển tuyến TGW, bắt tcpdump kiểm chứng đối xứng. | `COMPLETED` | [04-inspection-routing-and-symmetric-verification.md](04-inspection-routing-and-symmetric-verification.md) |
