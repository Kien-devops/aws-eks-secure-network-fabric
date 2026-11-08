# Module 12 — Dọn Dẹp Tài Nguyên Theo Phụ Thuộc Ngược & Kiểm Kê FinOps (Teardown & Cleanup)

## 1. Tổng Quan Module

Module 12 đặc tả quy trình dọn dẹp và thu hồi toàn bộ tài nguyên trên AWS Cloud theo thứ tự phụ thuộc ngược 6 tầng (Reverse 6-Tier Dependency). Quy trình này ngăn ngừa triệt để lỗi kẹt ENI, đảm bảo an toàn dữ liệu trước khi xóa và thực hiện kiểm kê đối soát đưa chi phí vận hành về $0.00 USD/ngày.

---

## 2. Thứ Tự Phụ Thuộc (Dependency Tree)

```text
[Module 11 Tổng Hợp Bằng Chứng & Báo Cáo SRE Hoàn Tất]
                         │
                         ▼
[12.01 Quy Trình Hủy Tài Nguyên Theo Phụ Thuộc Ngược (Reverse Teardown)]
                         │
                         ▼
[12.02 Kiểm Kê Tồn Dư & Đối Soát Chi Phí Sau Cleanup (Zero Residual)]
```

---

## 3. Danh Mục Bài Lab & Trạng Thái

| Mã Bài | Tên Bài Lab | Nội Dung Kỹ Thuật Chính | Trạng Thái | File Đặc Tả |
| :--- | :--- | :--- | :--- | :--- |
| **12.01** | Reverse Teardown | Quy trình xóa tài nguyên 6 tầng: L7 Ingress -> EKS -> DB/Cache -> Firewalls -> TGW -> Network Base | `READY_TO_RUN` | [01-reverse-dependency-teardown.md](01-reverse-dependency-teardown.md) |
| **12.02** | Residual Verification | Kiểm kê tồn dư trên 6 nhóm dịch vụ AWS qua CLI và đối soát chi phí billing ngày T+1 | `READY_TO_RUN` | [02-zero-residual-verification.md](02-zero-residual-verification.md) |

---

## 4. Danh Mục 6 Tầng Dọn Dẹp (Teardown Tiers Inventory)

| Tầng Dọn Dẹp | Thành Phần Tài Nguyên | Phạm Vi AWS Service | Hành Động Kỹ Thuật |
| :--- | :--- | :--- | :--- |
| **Tầng 1** | L7 Ingress & WAF | ALB, Public ACM Cert, Web ACL | Xóa Ingress K8s, Detach WAF & Xóa Web ACL |
| **Tầng 2** | Workloads & EKS | Managed Node Groups, EKS Control Planes | Xóa Node Groups trước (giải phóng ENI), xóa Clusters |
| **Tầng 3** | Database & Messaging | Aurora Serverless v2, ElastiCache Redis, SQS | Xóa DB cluster, xóa Redis replication group, xóa Queues |
| **Tầng 4** | Firewalls & GWLB | AWS Network Firewall, GWLBe, GWLB, Suricata EC2 | Xóa NFW, xóa GWLB endpoints, terminate EC2 instances |
| **Tầng 5** | Transit Gateway | TGW Attachments, TGW Route Tables, TGW Core | Xóa 4 VPC Attachments, xóa route tables, xóa TGW |
| **Tầng 6** | Network Base & IPs | NAT Gateways, Elastic IPs, IGWs, Subnets, 4 VPCs | Xóa NAT GWs, release Elastic IPs, xóa 4 VPCs |
