# 02.06 — Cấu Hình Private VPC Endpoints Cho Cụm EKS Riêng Tư (Edge & Core)

> **Mã bài lab:** `02.06`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 35 phút  
> **Chi phí ước tính:** ~$0.01/giờ/endpoint (~$0.14 USD/giờ cho các endpoints thiết yếu)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành toàn bộ các bài lab [02.01](01-four-vpcs-and-subnets.md) đến [02.05](05-vpc-flow-logs-cloudwatch.md).
- Cần thiết để các cụm Private EKS (Edge và Core) tại Module 03 khởi động worker nodes, join cluster và kéo container images mà không bị treo do thiếu kết nối AWS API.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVpcEndpoint",
        "ec2:DescribeVpcEndpoints",
        "ec2:ModifyVpcEndpoint",
        "ec2:DeleteVpcEndpoints",
        "ec2:CreateSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:DescribeSecurityGroups",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Mỗi Interface VPC Endpoint tính phí ~$0.01 USD/giờ tại Singapore. S3 Gateway Endpoint hoàn toàn miễn phí. Để tối ưu chi phí, chỉ khởi tạo các endpoints bắt buộc cho EKS bootstrapping và workloads.
- **Cảnh báo EKS Private Cluster Bootstrapping:** Nếu thiếu `ecr.api`, `ecr.dkr`, `s3` hoặc `sts`, EKS Managed Node Groups sẽ không thể cài đặt `aws-node`, `kube-proxy`, `coredns`, dẫn đến node ở trạng thái `NotReady` vĩnh viễn!
- **Yêu cầu Private DNS:** Bắt buộc phải bật `Enable Private DNS Name` trên các Interface Endpoints để các SDK AWS bên trong Pod tự động phân giải tên miền API về địa chỉ IP riêng của ENI endpoint thay vì đi ra Internet.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo Security Groups Cho VPC Endpoints
Truy cập **VPC Console** tại Singapore `ap-southeast-1`:
1. Tại menu điều hướng bên trái, chọn **Security groups** -> Nhấp nút cam **Create security group**.
2. **Tạo SG cho Edge VPC Endpoints:**
   - **Security group name:** Nhập `fabric-edge-vpce-sg`.
   - **Description:** Nhập `Allows HTTPS 443 inbound to VPC Endpoints from Edge VPC`.
   - **VPC:** Chọn `fabric-edge-vpc`.
   - **Inbound rules:**
     - Nhấp **Add rule**:
       - Type: `HTTPS` | Protocol: `TCP` | Port range: `443`.
       - Source: `Custom` -> Nhập CIDR của Edge VPC: `10.40.0.0/16`.
       - Description: `Allow HTTPS from Edge VPC CIDR`.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
   - Nhấp **Create security group**.

3. **Tạo SG cho Core VPC Endpoints:**
   - Nhấp lại **Create security group**.
   - **Security group name:** Nhập `fabric-core-vpce-sg`.
   - **Description:** Nhập `Allows HTTPS 443 inbound to VPC Endpoints from Core VPC`.
   - **VPC:** Chọn `fabric-core-vpc`.
   - **Inbound rules:**
     - Nhấp **Add rule**:
       - Type: `HTTPS` | Protocol: `TCP` | Port range: `443`.
       - Source: `Custom` -> Nhập CIDR của Core VPC: `10.50.0.0/16`.
       - Description: `Allow HTTPS from Core VPC CIDR`.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
   - Nhấp **Create security group**.

---

### Bước 2: Tạo Gateway Endpoint Cho Amazon S3 (Miễn Phí)
1. Tại menu điều hướng bên trái VPC Console, chọn **Endpoints** -> Nhấp nút cam **Create endpoint**.
2. **Tạo S3 Gateway Endpoint cho Edge VPC:**
   - **Name tag:** Nhập `fabric-edge-s3-endpoint`.
   - **Service category:** Chọn **AWS services**.
   - **Services:** Trong ô tìm kiếm, nhập `s3` -> Chọn dòng có Service Name là `com.amazonaws.ap-southeast-1.s3` với Type là **Gateway**.
   - **VPC:** Chọn `fabric-edge-vpc`.
   - **Route tables:** Đánh dấu tích vào checkbox của:
     - `fabric-edge-private-rt`
   - **Policy:** Chọn **Full access**.
   - Nhấp **Create endpoint**.

3. **Tạo S3 Gateway Endpoint cho Core VPC:**
   - Nhấp lại **Create endpoint**.
   - **Name tag:** Nhập `fabric-core-s3-endpoint`.
   - **Service category:** Chọn **AWS services**.
   - **Services:** Chọn `com.amazonaws.ap-southeast-1.s3` (Type: **Gateway**).
   - **VPC:** Chọn `fabric-core-vpc`.
   - **Route tables:** Đánh dấu tích vào checkbox của:
     - `fabric-core-private-rt`
   - **Policy:** Chọn **Full access**.
   - Nhấp **Create endpoint**.

---

### Bước 3: Tạo Các Interface Endpoints Thiết Yếu Cho Edge VPC
Tại màn hình **Endpoints** -> Nhấp **Create endpoint**:

1. **Endpoint `ecr.api` (Edge):**
   - **Name tag:** `fabric-edge-ecr-api-ep`.
   - **Service category:** `AWS services` -> Tìm `com.amazonaws.ap-southeast-1.ecr.api`.
   - **VPC:** Chọn `fabric-edge-vpc`.
   - **Subnets:**
     - Tại `ap-southeast-1a`: Chọn subnet `fabric-edge-vpce-1a`.
     - Tại `ap-southeast-1b`: Chọn subnet `fabric-edge-vpce-1b`.
   - **Security groups:** Bỏ chọn default SG, chọn `fabric-edge-vpce-sg`.
   - **Additional settings:** Đảm bảo ô **Enable DNS name** đã được chọn tích.
   - Nhấp **Create endpoint**.

2. **Endpoint `ecr.dkr` (Edge):**
   - Tương tự, chọn service `com.amazonaws.ap-southeast-1.ecr.dkr` | Subnets: `fabric-edge-vpce-1a/b` | SG: `fabric-edge-vpce-sg`.

3. **Endpoint `sts` (Edge - Phục vụ Pod Identity):**
   - Chọn service `com.amazonaws.ap-southeast-1.sts` | Subnets: `fabric-edge-vpce-1a/b` | SG: `fabric-edge-vpce-sg`.

4. **Endpoint `logs` (Edge - Phục vụ CloudWatch Logging):**
   - Chọn service `com.amazonaws.ap-southeast-1.logs` | Subnets: `fabric-edge-vpce-1a/b` | SG: `fabric-edge-vpce-sg`.

5. **Endpoint `ec2` (Edge - Phục vụ Node registration):**
   - Chọn service `com.amazonaws.ap-southeast-1.ec2` | Subnets: `fabric-edge-vpce-1a/b` | SG: `fabric-edge-vpce-sg`.

---

### Bước 4: Tạo Các Interface Endpoints Thiết Yếu Cho Core VPC
Thực hiện tương tự trong `fabric-core-vpc` với Subnets `fabric-core-vpce-1a/b` và Security Group `fabric-core-vpce-sg`:
1. `com.amazonaws.ap-southeast-1.ecr.api`
2. `com.amazonaws.ap-southeast-1.ecr.dkr`
3. `com.amazonaws.ap-southeast-1.sts`
4. `com.amazonaws.ap-southeast-1.logs`
5. `com.amazonaws.ap-southeast-1.ec2`
6. `com.amazonaws.ap-southeast-1.sqs` *(BẮT BUỘC cho `payment-worker` lắng nghe hàng đợi AWS SQS nội bộ)*.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái các VPC Endpoints đã tạo:
```bash
# 1. Liệt kê toàn bộ Interface & Gateway Endpoints trong Core VPC
CORE_VPC_ID=$(aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-core-vpc" --query 'Vpcs[0].VpcId' --output text)
aws ec2 describe-vpc-endpoints --region ap-southeast-1 \
  --filters "Name=vpc-id,Values=$CORE_VPC_ID" \
  --query 'VpcEndpoints[*].{ServiceName:ServiceName,Type:VpcEndpointType,State:State,PrivateDns:PrivateDnsEnabled}' \
  --output table

# 2. Kiểm tra route tới S3 Prefix List trong fabric-core-private-rt
aws ec2 describe-route-tables --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-core-private-rt" \
  --query 'RouteTables[0].Routes[?DestinationPrefixListId!=null].{PrefixList:DestinationPrefixListId,Gateway:GatewayId,State:State}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để xóa VPC Endpoints khi dọn dẹp hoặc cấu hình lại:
1. Mở **VPC Console** -> **Endpoints** -> Chọn các endpoint cần xóa -> Nhấp **Actions** -> Chọn **Delete VPC endpoints**.
2. Xóa các Security Groups liên quan (`fabric-edge-vpce-sg`, `fabric-core-vpce-sg`).
3. Hoặc thực thi qua CLI:
   ```bash
   for ep_id in $(aws ec2 describe-vpc-endpoints --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'VpcEndpoints[*].VpcEndpointId' --output text); do
     aws ec2 delete-vpc-endpoints --region ap-southeast-1 --vpc-endpoint-ids $ep_id
   done
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/06-vpc-endpoints.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] S3 Gateway Endpoint được liên kết tự động với Route Tables của Edge và Core VPCs.
- [ ] Toàn bộ các Interface Endpoints (`ecr.api`, `ecr.dkr`, `sts`, `logs`, `ec2`, `sqs`) đều ở trạng thái `available`.
- [ ] Tính năng Private DNS Name hiển thị `true` trên tất cả Interface Endpoints.
- [ ] Security Groups chặn toàn bộ lưu lượng ngoại trừ cổng 443 từ nội bộ dải VPC CIDR.
