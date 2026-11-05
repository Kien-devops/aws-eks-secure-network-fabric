# 02.06 — Cấu Hình Private VPC Endpoints Cho Cụm EKS Riêng Tư (Edge & Core)

> **Mã bài lab:** `02.06`  
> **Trạng thái:** `RUNTIME_PASS`  
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
   - **Security group name:** Nhập `fabric-edge-vpce-sg` (`sg-0dba5df9206abd189`).
   - **Description:** Nhập `Allows HTTPS 443 inbound to VPC Endpoints from Edge VPC`.
   - **VPC:** Chọn `fabric-edge-vpc` (`vpc-0468b18dddd1d4d2d`).
   - **Inbound rules:**
     - Nhấp **Add rule**:
       - Type: `HTTPS` | Protocol: `TCP` | Port range: `443`.
       - Source: `Custom` -> Nhập CIDR của Edge VPC: `10.40.0.0/16`.
       - Description: `Allow HTTPS from Edge VPC CIDR`.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`, Key: `Environment` | Value: `prod`, Key: `ManagedBy` | Value: `console-lab`.
   - Nhấp **Create security group**.

3. **Tạo SG cho Core VPC Endpoints:**
   - Nhấp lại **Create security group**.
   - **Security group name:** Nhập `fabric-core-vpce-sg` (`sg-06dab7dd4b56070ad`).
   - **Description:** Nhập `Allows HTTPS 443 inbound to VPC Endpoints from Core VPC`.
   - **VPC:** Chọn `fabric-core-vpc` (`vpc-09888cc991104c959`).
   - **Inbound rules:**
     - Nhấp **Add rule**:
       - Type: `HTTPS` | Protocol: `TCP` | Port range: `443`.
       - Source: `Custom` -> Nhập CIDR của Core VPC: `10.50.0.0/16`.
       - Description: `Allow HTTPS from Core VPC CIDR`.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`, Key: `Environment` | Value: `prod`, Key: `ManagedBy` | Value: `console-lab`.
   - Nhấp **Create security group**.

---

### Bước 2: Tạo Gateway Endpoint Cho Amazon S3 (Miễn Phí)
1. Tại menu điều hướng bên trái VPC Console, chọn **Endpoints** -> Nhấp nút cam **Create endpoint**.
2. **Tạo S3 Gateway Endpoint cho Edge VPC:**
   - **Name tag:** Nhập `fabric-edge-s3-endpoint` (`vpce-070fde8e6898adf2e`).
   - **Service category:** Chọn **AWS services**.
   - **Services:** Trong ô tìm kiếm, nhập `s3` -> Chọn dòng có Service Name là `com.amazonaws.ap-southeast-1.s3` với Type là **Gateway**.
   - **VPC:** Chọn `fabric-edge-vpc` (`vpc-0468b18dddd1d4d2d`).
   - **Route tables:** Đánh dấu tích vào checkbox của:
     - `fabric-edge-private-rt` (`rtb-00cd096fd0d4a2615`)
   - **Policy:** Chọn **Full access**.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`, Key: `Environment` | Value: `prod`, Key: `ManagedBy` | Value: `console-lab`.
   - Nhấp **Create endpoint**.

3. **Tạo S3 Gateway Endpoint cho Core VPC:**
   - Nhấp lại **Create endpoint**.
   - **Name tag:** Nhập `fabric-core-s3-endpoint` (`vpce-00792527fbc00b8a6`).
   - **Service category:** Chọn **AWS services**.
   - **Services:** Chọn `com.amazonaws.ap-southeast-1.s3` (Type: **Gateway**).
   - **VPC:** Chọn `fabric-core-vpc` (`vpc-09888cc991104c959`).
   - **Route tables:** Đánh dấu tích vào checkbox của:
     - `fabric-core-private-rt` (`rtb-00ac268964554cc7e`)
   - **Policy:** Chọn **Full access**.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`, Key: `Environment` | Value: `prod`, Key: `ManagedBy` | Value: `console-lab`.
   - Nhấp **Create endpoint**.

---

### Bước 3: Tạo Các Interface Endpoints Thiết Yếu Cho Edge VPC
Tại màn hình **Endpoints** -> Nhấp **Create endpoint**:

1. **Endpoint `ecr.api` (Edge):**
   - **Name tag:** `fabric-edge-ecr-api-ep` (`vpce-08d3d806215f9494b`).
   - **Service category:** `AWS services` -> Tìm `com.amazonaws.ap-southeast-1.ecr.api`.
   - **VPC:** Chọn `fabric-edge-vpc` (`vpc-0468b18dddd1d4d2d`).
   - **Subnets:**
     - Tại `ap-southeast-1a`: Chọn subnet `fabric-edge-vpce-1a` (`subnet-01aa1d8c163dffca5`).
     - Tại `ap-southeast-1b`: Chọn subnet `fabric-edge-vpce-1b` (`subnet-06c83b89e45f47650`).
   - **Security groups:** Bỏ chọn default SG, chọn `fabric-edge-vpce-sg` (`sg-0dba5df9206abd189`).
   - **Additional settings:** Đảm bảo ô **Enable DNS name** đã được chọn tích (`true`).
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`, Key: `Environment` | Value: `prod`, Key: `ManagedBy` | Value: `console-lab`.
   - Nhấp **Create endpoint**.

2. **Endpoint `ecr.dkr` (Edge):**
   - **Name tag:** `fabric-edge-ecr-dkr-ep` (`vpce-08a6cc353238fab6b`).
   - Service: `com.amazonaws.ap-southeast-1.ecr.dkr` | Subnets: `fabric-edge-vpce-1a/b` | SG: `fabric-edge-vpce-sg` | Private DNS: `true`.

3. **Endpoint `sts` (Edge - Phục vụ Pod Identity):**
   - **Name tag:** `fabric-edge-sts-ep` (`vpce-0194dfc20963168a3`).
   - Service: `com.amazonaws.ap-southeast-1.sts` | Subnets: `fabric-edge-vpce-1a/b` | SG: `fabric-edge-vpce-sg` | Private DNS: `true`.

4. **Endpoint `logs` (Edge - Phục vụ CloudWatch Logging):**
   - **Name tag:** `fabric-edge-logs-ep` (`vpce-09fed82b9d4cb5ba3`).
   - Service: `com.amazonaws.ap-southeast-1.logs` | Subnets: `fabric-edge-vpce-1a/b` | SG: `fabric-edge-vpce-sg` | Private DNS: `true`.

5. **Endpoint `ec2` (Edge - Phục vụ Node registration):**
   - **Name tag:** `fabric-edge-ec2-ep` (`vpce-06984174467986962`).
   - Service: `com.amazonaws.ap-southeast-1.ec2` | Subnets: `fabric-edge-vpce-1a/b` | SG: `fabric-edge-vpce-sg` | Private DNS: `true`.

6. **Endpoint `eks-auth` (Edge - BẮT BUỘC Cho EKS Pod Identity Agent):**
   - **Name tag:** `fabric-edge-eks-auth-ep` (`vpce-0e7c2d2e7f5304f31`).
   - Service: `com.amazonaws.ap-southeast-1.eks-auth` | Subnets: `fabric-edge-vpce-1a/b` | SG: `fabric-edge-vpce-sg` | Private DNS: `true`.
   - *(Lưu ý phân biệt: `eks-auth` là endpoint độc quyền phục vụ DaemonSet `eks-pod-identity-agent` trao đổi thông tin danh tính của Pods với Control Plane EKS; trong khi `sts` dùng để giả định IAM Role)*.

---

### Bước 4: Tạo Các Interface Endpoints Thiết Yếu Cho Core VPC
Thực hiện tương tự trong `fabric-core-vpc` (`vpc-09888cc991104c959`) với Subnets `fabric-core-vpce-1a` (`subnet-053d2f1c4cf3235c6`) / `fabric-core-vpce-1b` (`subnet-0f4c9a2c5bcf93261`) và Security Group `fabric-core-vpce-sg` (`sg-06dab7dd4b56070ad`), bật **Enable DNS name** (`true`):

1. **`ecr.api` (Core):** `fabric-core-ecr-api-ep` (`vpce-02d5093117359d335`).
2. **`ecr.dkr` (Core):** `fabric-core-ecr-dkr-ep` (`vpce-07412943700801a22`).
3. **`sts` (Core):** `fabric-core-sts-ep` (`vpce-08dd4cbe87782adab`).
4. **`logs` (Core):** `fabric-core-logs-ep` (`vpce-01f94a5f8e27d4506`).
5. **`ec2` (Core):** `fabric-core-ec2-ep` (`vpce-0ae30e3f67eda2fa2`).
6. **`sqs` (Core):** `fabric-core-sqs-ep` (`vpce-00d3e313427f82af1`) *(BẮT BUỘC cho `payment-worker` lắng nghe hàng đợi AWS SQS nội bộ)*.
7. **`eks-auth` (Core):** `fabric-core-eks-auth-ep` (`vpce-094f91c485535f84b`) *(BẮT BUỘC cho EKS Pod Identity Agent xác thực Pods Core: Order, Inventory, Payment)*.

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

- [x] S3 Gateway Endpoint (`fabric-edge-s3-endpoint`: `vpce-070fde8e6898adf2e`, `fabric-core-s3-endpoint`: `vpce-00792527fbc00b8a6`) được liên kết tự động với Route Tables của Edge (`fabric-edge-private-rt`) và Core (`fabric-core-private-rt`) VPCs (Prefix List `pl-6fa54006`).
- [x] Toàn bộ 13 Interface Endpoints (`ecr.api`, `ecr.dkr`, `sts`, `logs`, `ec2`, `sqs`, và `eks-auth`) đều ở trạng thái `available`.
- [x] Tính năng Private DNS Name hiển thị `true` trên tất cả 13 Interface Endpoints.
- [x] Endpoint `com.amazonaws.ap-southeast-1.eks-auth` đã được tạo và kích hoạt cho cả Edge và Core VPC để phục vụ EKS Pod Identity.
- [x] Security Groups (`fabric-edge-vpce-sg`: `sg-0dba5df9206abd189`, `fabric-core-vpce-sg`: `sg-06dab7dd4b56070ad`) chặn toàn bộ lưu lượng ngoại trừ cổng 443 từ nội bộ dải VPC CIDR.

### Trạng Thái Thực Thi Runtime (All 15 VPC Endpoints Completed)
- **Thời gian hoàn thành:** `2026-11-05T17:52:00Z`
- **Công cụ thực thi:** MCP `aws-api-mcp/call_aws`
- **15 VPC Endpoints Đã Tạo & Hoạt Động:**
  - **Edge VPC (7 Endpoints):**
    - S3 Gateway: `vpce-070fde8e6898adf2e`
    - `ecr.api`: `vpce-08d3d806215f9494b`
    - `ecr.dkr`: `vpce-08a6cc353238fab6b`
    - `sts`: `vpce-0194dfc20963168a3`
    - `logs`: `vpce-09fed82b9d4cb5ba3`
    - `ec2`: `vpce-06984174467986962`
    - `eks-auth`: `vpce-0e7c2d2e7f5304f31`
  - **Core VPC (8 Endpoints):**
    - S3 Gateway: `vpce-00792527fbc00b8a6`
    - `ecr.api`: `vpce-02d5093117359d335`
    - `ecr.dkr`: `vpce-07412943700801a22`
    - `sts`: `vpce-08dd4cbe87782adab`
    - `logs`: `vpce-01f94a5f8e27d4506`
    - `ec2`: `vpce-0ae30e3f67eda2fa2`
    - `sqs`: `vpce-00d3e313427f82af1`
    - `eks-auth`: `vpce-094f91c485535f84b`
- **File bằng chứng:** `evidence/02-network/06-vpc-endpoints.json`
