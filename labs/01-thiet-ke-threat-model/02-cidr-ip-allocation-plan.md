# 01.02 — Kế Hoạch Phân Bổ Dải Mạng (IP Plan) & Quy Hoạch Subnets

> **Mã bài lab:** `01.02`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành phân tích mô hình đe dọa [01.01 — Phân Tích STRIDE](01-stride-threat-analysis.md).
- Đã xác nhận trên AWS Inventory không có VPC nào xung đột các dải mạng `10.40.0.0/16`, `10.50.0.0/16`, `10.70.0.0/16`, `10.80.0.0/16`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để kiểm tra CIDR và hạn ngạch (Quotas) trên AWS Console:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "servicequotas:GetServiceQuota",
        "servicequotas:ListServiceQuotas"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo quan trọng:** Dải mạng CIDR của VPC sau khi tạo không thể thu hẹp. AWS tự động giữ lại 5 địa chỉ IP đầu tiên và cuối cùng trong mỗi subnet (Network address, VPC router, DNS server, AWS future use, Broadcast address). Việc quy hoạch kích thước subnet phải tính toán dự phòng cho địa chỉ IP của Pod (EKS VPC CNI phân bổ IP trực tiếp từ subnet của Node), IP của ENI TGW và IP của VPC Endpoints.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Kiểm Tra Trạng Thái & Hạn Ngạch VPC Trên AWS Console
1. Đăng nhập vào **AWS Management Console**, chọn Region Singapore `ap-southeast-1`.
2. Trên thanh tìm kiếm, nhập `Service Quotas` và chọn **Service Quotas**.
3. Tại menu điều hướng bên trái, chọn **AWS services** -> Nhập `Amazon Virtual Private Cloud (Amazon VPC)`.
4. Kiểm tra các hạn ngạch quan trọng:
   - **VPCs per Region:** Mặc định là 5 (Đủ cho 4 VPCs của Fabric).
   - **Subnets per VPC:** Mặc định là 200 (Thỏa mãn quy hoạch tối đa 8 subnets/VPC).
   - **Transit Gateways per Region:** Mặc định là 5.
   - **Interface VPC endpoints per VPC:** Mặc định là 50.

### Bước 2: Rà Soát Chi Tiết Ma Trận Phân Bổ 4 VPCs & 26 Subnets
Mở **VPC Console** -> Chuẩn bị danh sách tham số để khởi tạo trong Module 02:

#### 1. Edge EKS VPC (`10.40.0.0/16`) — Tổng: 65,536 IPs
- **`ap-southeast-1a`:**
  - `fabric-edge-public-1a`: `10.40.0.0/24` (251 IPs khả dụng — ALB Ingress A)
  - `fabric-edge-nodes-1a`: `10.40.10.0/22` (1,019 IPs khả dụng — EKS Edge Worker Nodes & Frontend Pods)
  - `fabric-edge-vpce-1a`: `10.40.20.0/24` (251 IPs khả dụng — Interface Endpoints)
  - `fabric-edge-tgw-1a`: `10.40.250.0/28` (11 IPs khả dụng — Dedicated TGW Attachment ENI)
- **`ap-southeast-1b`:**
  - `fabric-edge-public-1b`: `10.40.1.0/24` (251 IPs khả dụng — ALB Ingress B)
  - `fabric-edge-nodes-1b`: `10.40.14.0/22` (1,019 IPs khả dụng — EKS Edge Worker Nodes & Auth Pods)
  - `fabric-edge-vpce-1b`: `10.40.21.0/24` (251 IPs khả dụng — Interface Endpoints)
  - `fabric-edge-tgw-1b`: `10.40.250.16/28` (11 IPs khả dụng — Dedicated TGW Attachment ENI)

#### 2. Core EKS VPC (`10.50.0.0/16`) — Tổng: 65,536 IPs
- **`ap-southeast-1a`:**
  - `fabric-core-nodes-1a`: `10.50.10.0/22` (1,019 IPs khả dụng — EKS Core Nodes: Order, Inventory, Payment)
  - `fabric-core-data-1a`: `10.50.20.0/24` (251 IPs khả dụng — Aurora PostgreSQL Primary / Redis AZ-a)
  - `fabric-core-vpce-1a`: `10.50.30.0/24` (251 IPs khả dụng — VPCE ECR, SQS, Logs AZ-a)
  - `fabric-core-tgw-1a`: `10.50.250.0/28` (11 IPs khả dụng — Dedicated TGW Attachment ENI)
- **`ap-southeast-1b`:**
  - `fabric-core-nodes-1b`: `10.50.14.0/22` (1,019 IPs khả dụng — EKS Core Nodes AZ-b)
  - `fabric-core-data-1b`: `10.50.21.0/24` (251 IPs khả dụng — Aurora PostgreSQL Replica / Redis AZ-b)
  - `fabric-core-vpce-1b`: `10.50.31.0/24` (251 IPs khả dụng — VPCE AZ-b)
  - `fabric-core-tgw-1b`: `10.50.250.16/28` (11 IPs khả dụng — Dedicated TGW Attachment ENI)

#### 3. Inspection VPC (`10.70.0.0/16`) — Tách Biệt 3 Tầng Cho An Toàn GWLB
- **`ap-southeast-1a`:**
  - `fabric-insp-tgw-1a`: `10.70.0.0/28` (11 IPs khả dụng — TGW Attachment ENI, Appliance Mode = ENABLED)
  - `fabric-insp-gwlbe-1a`: `10.70.1.0/28` (11 IPs khả dụng — Điểm cuối GWLB Endpoint AZ-a)
  - `fabric-insp-fw-1a`: `10.70.10.0/24` (251 IPs khả dụng — Suricata EC2 Instance A GENEVE 6081)
- **`ap-southeast-1b`:**
  - `fabric-insp-tgw-1b`: `10.70.0.16/28` (11 IPs khả dụng — TGW Attachment ENI AZ-b)
  - `fabric-insp-gwlbe-1b`: `10.70.1.16/28` (11 IPs khả dụng — Điểm cuối GWLB Endpoint AZ-b)
  - `fabric-insp-fw-1b`: `10.70.11.0/24` (251 IPs khả dụng — Suricata EC2 Instance B GENEVE 6081)

#### 4. Centralized Egress VPC (`10.80.0.0/16`) — Tường Lửa Ra Ngoài Tập Trung
- **`ap-southeast-1a`:**
  - `fabric-egress-tgw-1a`: `10.80.0.0/28` (11 IPs khả dụng — TGW Attachment ENI AZ-a)
  - `fabric-egress-fw-1a`: `10.80.1.0/28` (11 IPs khả dụng — AWS Network Firewall Endpoint AZ-a)
  - `fabric-egress-public-1a`: `10.80.10.0/24` (251 IPs khả dụng — NAT Gateway A & Internet Gateway)
- **`ap-southeast-1b`:**
  - `fabric-egress-tgw-1b`: `10.80.0.16/28` (11 IPs khả dụng — TGW Attachment ENI AZ-b)
  - `fabric-egress-fw-1b`: `10.80.1.16/28` (11 IPs khả dụng — AWS Network Firewall Endpoint AZ-b)
  - `fabric-egress-public-1b`: `10.80.11.0/24` (251 IPs khả dụng — NAT Gateway B & Internet Gateway)

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra xác nhận không có dải mạng nào trùng lặp trên tài khoản:
```bash
# 1. Liệt kê toàn bộ CIDR block hiện có trong Region Singapore
aws ec2 describe-vpcs --region ap-southeast-1 \
  --query 'Vpcs[*].{VpcId:VpcId,CidrBlock:CidrBlock,State:State,Name:Tags[?Key==`Name`].Value | [0]}' \
  --output table

# 2. Kiểm tra hạn ngạch VPC hiện tại
aws service-quotas get-service-quota --region ap-southeast-1 \
  --service-code vpc \
  --quota-code L-F678F165 \
  --query 'Quota.{Name:QuotaName,Value:Value}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong giai đoạn thiết kế, mọi cập nhật dải CIDR được ghi nhận bằng văn bản và điều chỉnh lại bảng phân bổ trước khi áp dụng vào Module 02. Không có tài nguyên đám mây nào cần xóa bỏ.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/01-threat-model/02-ip-plan-audit.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Toàn bộ 4 VPCs hoàn toàn không chồng lấn CIDR (`10.40/16`, `10.50/16`, `10.70/16`, `10.80/16`).
- [ ] Subnet TGW và Subnet Endpoints có kích thước tối thiểu `/28` theo khuyến nghị AWS Best Practices.
- [ ] Subnet Private Nodes có kích thước `/22` đáp ứng hơn 1,000 Pod IPs cho cụm EKS.
- [ ] Tách biệt hoàn toàn 3 lớp subnet trong từng AZ tại Inspection VPC để phục vụ GWLB.
