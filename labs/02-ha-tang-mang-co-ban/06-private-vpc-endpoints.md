# 02.06 — Đặc Tả Private VPC Endpoints Cho Cụm EKS Riêng Tư (Edge & Core)

> **Mã bài lab:** `02.06`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`
> **File bằng chứng:** `evidence/02-network/06-vpc-endpoints.json`

---

## 1. Mục Tiêu (Objective)

Thiết lập hệ thống 15 AWS Private VPC Endpoints (2 Gateway S3 và 13 Interface Endpoints kèm Private DNS) đặt tại các subnet riêng của Edge VPC và Core VPC nhằm đảm bảo cụm EKS hoàn toàn riêng tư có thể khởi động node, kéo container images và giao tiếp AWS API an toàn mà không cần mở kết nối Internet.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Vị Trí / Subnet / AZ | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-edge-vpce-sg` | `AWS::EC2::SecurityGroup` | `fabric-edge-vpc` | `sg-0dba5df9206abd189` |
| `fabric-core-vpce-sg` | `AWS::EC2::SecurityGroup` | `fabric-core-vpc` | `sg-06dab7dd4b56070ad` |
| `fabric-edge-s3-endpoint` | `AWS::EC2::VPCEndpoint` (Gateway) | `fabric-edge-vpc` (`fabric-edge-private-rt`) | `vpce-070fde8e6898adf2e` |
| `fabric-core-s3-endpoint` | `AWS::EC2::VPCEndpoint` (Gateway) | `fabric-core-vpc` (`fabric-core-private-rt`) | `vpce-00792527fbc00b8a6` |
| `fabric-edge-ecr-api-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-edge-vpce-1a`, `1b` | `vpce-08d3d806215f9494b` |
| `fabric-edge-ecr-dkr-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-edge-vpce-1a`, `1b` | `vpce-08a6cc353238fab6b` |
| `fabric-edge-sts-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-edge-vpce-1a`, `1b` | `vpce-0194dfc20963168a3` |
| `fabric-edge-logs-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-edge-vpce-1a`, `1b` | `vpce-09fed82b9d4cb5ba3` |
| `fabric-edge-ec2-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-edge-vpce-1a`, `1b` | `vpce-06984174467986962` |
| `fabric-edge-eks-auth-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-edge-vpce-1a`, `1b` | `vpce-0e7c2d2e7f5304f31` |
| `fabric-core-ecr-api-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-core-vpce-1a`, `1b` | `vpce-02d5093117359d335` |
| `fabric-core-ecr-dkr-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-core-vpce-1a`, `1b` | `vpce-07412943700801a22` |
| `fabric-core-sts-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-core-vpce-1a`, `1b` | `vpce-08dd4cbe87782adab` |
| `fabric-core-logs-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-core-vpce-1a`, `1b` | `vpce-01f94a5f8e27d4506` |
| `fabric-core-ec2-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-core-vpce-1a`, `1b` | `vpce-0ae30e3f67eda2fa2` |
| `fabric-core-sqs-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-core-vpce-1a`, `1b` | `vpce-00d3e313427f82af1` |
| `fabric-core-eks-auth-ep` | `AWS::EC2::VPCEndpoint` (Interface) | `fabric-core-vpce-1a`, `1b` | `vpce-094f91c485535f84b` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-*-ep` / `fabric-*-sg` | Toàn bộ VPC Endpoints và Security Groups |
| `Project` | `aws-eks-secure-network-fabric` | Toàn bộ VPC Endpoints và Security Groups |
| `Environment` | `prod` | Toàn bộ VPC Endpoints và Security Groups |
| `ManagedBy` | `manual` | Quản trị hạ tầng VPC Endpoints thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Security Groups Phục Vụ Endpoints

- **`fabric-edge-vpce-sg` (`sg-0dba5df9206abd189`):**
  - Inbound: Cho phép `TCP 443` (HTTPS) từ nguồn Edge VPC CIDR (`10.40.0.0/16`). Chặn toàn bộ cổng khác.
  - Outbound: Mặc định cho phép ra ngoài nội bộ.
- **`fabric-core-vpce-sg` (`sg-06dab7dd4b56070ad`):**
  - Inbound: Cho phép `TCP 443` (HTTPS) từ nguồn Core VPC CIDR (`10.50.0.0/16`). Chặn toàn bộ cổng khác.
  - Outbound: Mặc định cho phép ra ngoài nội bộ.

### 4.2 S3 Gateway Endpoints (Miễn Phí)

- Cấu hình route tự động tới Prefix List S3 (`pl-6fa54006`) trên các bảng định tuyến:
  - `fabric-edge-private-rt` (`rtb-00cd096fd0d4a2615`) -> Target: `vpce-070fde8e6898adf2e`
  - `fabric-core-private-rt` (`rtb-00ac268964554cc7e`) -> Target: `vpce-00792527fbc00b8a6`
- **Chính sách:** Full access nội bộ.

### 4.3 Interface VPC Endpoints (Có Tính Phí, Bật Private DNS)

- **Tham số chung:**
  - `PrivateDnsEnabled: true` (Bắt buộc để các AWS SDK trong Pod tự động giải mã tên miền AWS API thành IP của ENI cục bộ).
  - Phân bổ cân bằng trên 2 Availability Zones (`1a` và `1b`).
- **Danh sách dịch vụ:**
  1. `com.amazonaws.ap-southeast-1.ecr.api`: Kéo metadata manifest container images.
  2. `com.amazonaws.ap-southeast-1.ecr.dkr`: Kéo các image layer blobs từ ECR.
  3. `com.amazonaws.ap-southeast-1.sts`: Giả định vai trò IAM (AssumeRoleWithWebIdentity) cho EKS workloads.
  4. `com.amazonaws.ap-southeast-1.logs`: Đẩy nhật ký cụm và ứng dụng về CloudWatch Logs.
  5. `com.amazonaws.ap-southeast-1.ec2`: Giao tiếp node registration và ENI attachment cho VPC CNI.
  6. `com.amazonaws.ap-southeast-1.eks-auth`: Độc quyền phục vụ daemon `eks-pod-identity-agent` xác thực danh tính Pods.
  7. `com.amazonaws.ap-southeast-1.sqs` *(chỉ tạo trên Core VPC)*: Phục vụ `core-service` lắng nghe hàng đợi SQS nội bộ.

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.01`: Các subnet `fabric-*-vpce-1a/1b` và VPCs phải sẵn sàng.
- Phụ thuộc vào `02.04`: Các Route Table `fabric-edge-private-rt` và `fabric-core-private-rt` phải tồn tại để gán S3 Gateway Endpoint routes.
- Điều kiện tiên quyết bắt buộc trước khi tạo EKS Cluster và Managed Node Groups tại [Module 03](../03-cum-eks-kep/README.md).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng thái 15 Endpoints** | `aws ec2 describe-vpc-endpoints --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric"` | Toàn bộ 15 endpoints đều có `State: available`. |
| **Private DNS Status** | Kiểm tra trường `PrivateDnsEnabled` của 13 Interface Endpoints | Toàn bộ đều đạt giá trị `true`. |
| **S3 Route Table association** | `aws ec2 describe-route-tables --filters "Name=tag:Name,Values=fabric-core-private-rt"` | Xuất hiện route với `DestinationPrefixListId: pl-6fa54006` trỏ tới `vpce-00792527fbc00b8a6`. |
| **Bảo vệ Security Groups** | `aws ec2 describe-security-groups --group-ids sg-0dba5df9206abd189 sg-06dab7dd4b56070ad` | Chỉ mở port 443 từ VPC CIDR tương ứng. |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Cảnh báo EKS Bootstrapping:** Nếu bất kỳ Interface Endpoint nào bị thiếu hoặc lỗi Private DNS, các worker node của cụm EKS tại Module 03 sẽ rơi vào trạng thái `NotReady` vĩnh viễn do không kết nối được ECR hoặc STS.
- **Cảnh báo chi phí:** Mỗi Interface VPC Endpoint tính phí ~$0.01 USD/giờ tại Singapore. Cần dọn dẹp khi ngừng lab.
- **Quy trình Rollback:**
  ```bash
  # Xóa toàn bộ 15 VPC Endpoints
  for ep_id in $(aws ec2 describe-vpc-endpoints --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'VpcEndpoints[*].VpcEndpointId' --output text); do
    aws ec2 delete-vpc-endpoints --region ap-southeast-1 --vpc-endpoint-ids $ep_id
  done

  # Xóa Security Groups sau khi ENI endpoints đã bị hủy
  aws ec2 delete-security-group --region ap-southeast-1 --group-id sg-0dba5df9206abd189
  aws ec2 delete-security-group --region ap-southeast-1 --group-id sg-06dab7dd4b56070ad
  ```
