# Module 00: Chuẩn Bị Môi Trường & Kiểm Kê Tài Nguyên AWS (Inventory)

## 1. Mục Tiêu & Nguyên Tắc FinOps
- **Mục tiêu:** 
  - Thực hiện kiểm kê toàn diện (Read-only AWS Resource Inventory) trên tài khoản AWS hiện tại trước khi triển khai bất kỳ thành phần nào của Project 6.
  - Xác nhận Region chuẩn: **Singapore (`ap-southeast-1`)** với 2 AZs: `ap-southeast-1a`, `ap-southeast-1b`.
  - Thiết lập ngân sách cảnh báo chi phí (AWS Budget) ở mức **$50.00 USD** để đảm bảo an toàn tài chính.
  - Đảm bảo môi trường hoàn toàn sạch sẽ (Clean State), không bị trùng lặp dải mạng CIDR (`10.40.0.0/16`, `10.50.0.0/16`, `10.70.0.0/16`, `10.80.0.0/16`).
- **Nguyên tắc:**
  - Tuyệt đối không tạo tài nguyên mới trước khi có báo cáo kiểm kê xác nhận không có xung đột dải mạng.
  - Sử dụng công cụ MCP `aws-api-mcp/call_aws` cho mọi lệnh `describe-*`, `list-*`.

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Xác thực Danh tính IAM & Region
Kiểm tra thông tin tài khoản và quyền hạn hiện tại:
```bash
aws sts get-caller-identity --output table
aws configure get region
```

### Bước 2: Kiểm kê Hệ thống VPC & CIDR Hiện Có
Kiểm tra toàn bộ VPC hiện tại trên `ap-southeast-1`:
```bash
aws ec2 describe-vpcs \
  --region ap-southeast-1 \
  --query 'Vpcs[*].{VpcId:VpcId,CidrBlock:CidrBlock,Name:Tags[?Key==`Name`].Value | [0],State:State}' \
  --output table
```
> **Điều kiện đạt:** Không có VPC nào đang chiếm giữ các dải `10.40.0.0/16`, `10.50.0.0/16`, `10.70.0.0/16`, `10.80.0.0/16`.

### Bước 3: Kiểm kê Transit Gateway & Load Balancers Hiện Có
```bash
aws ec2 describe-transit-gateways --region ap-southeast-1 --output table
aws elbv2 describe-load-balancers --region ap-southeast-1 --query 'LoadBalancers[*].{Name:LoadBalancerName,Type:Type,VpcId:VpcId,DNSName:DNSName}' --output table
```

### Bước 4: Thiết lập Ngân Sách AWS Budgets ($50.00 USD)
Khởi tạo cảnh báo ngân sách khi chi phí thực tế hoặc dự báo vượt quá 80% ($40 USD):
- Service: AWS Budgets
- Budget Type: Cost budget
- Amount: $50 USD / month
- Threshold: 80% ($40) & 100% ($50)

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [x] Xác nhận Account ID đã được che giấu (`***` hoặc `123456789012`).
- [x] Báo cáo kiểm kê xác nhận không có VPC hay TGW nào xung đột với thiết kế Project 6 (`evidence/00-inventory/00-environment-inventory.json`).
- [x] Ngân sách Budget $50.00 (`fabric-project6-monthly-budget`) đã được kích hoạt và ở trạng thái HEALTHY.

