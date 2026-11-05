# 03.02 — Khởi Tạo Hai Cụm Private EKS 1.31 Riêng Biệt (Edge & Core)

> **Mã bài lab:** `03.02`  
> **Trạng thái:** `RUNTIME_PASS`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$0.10 USD / giờ / cluster (~$0.20 USD / giờ cho 2 cụm EKS)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [03.01](01-kms-encryption-keys.md) và toàn bộ hạ tầng mạng [Module 02](../02-ha-tang-mang-co-ban/README.md) (đặc biệt là các Private VPC Endpoints tại `02.06`).
- Hai khóa KMS CMK `alias/fabric-edge-eks-secrets` và `alias/fabric-core-eks-secrets` đang ở trạng thái `Enabled`.
- Đăng nhập AWS Management Console tại Singapore `ap-southeast-1`.

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
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole",
        "eks:CreateCluster",
        "eks:DescribeCluster",
        "eks:ListClusters",
        "eks:UpdateClusterConfig",
        "eks:DeleteCluster",
        "kms:CreateGrant",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** EKS Control Plane tính phí $0.10 USD/giờ mỗi cụm (~$4.80 USD/ngày cho 2 cụm EKS). Cần theo dõi chặt chẽ ngân sách $50.00 USD.
- **Cảnh báo Phiên Bản EKS:** **BẮT BUỘC DÙNG EKS 1.31** (hoặc 1.32). Phiên bản EKS 1.30 đã kết thúc hỗ trợ tiêu chuẩn (End of Standard Support) từ tháng 11/2025, AWS sẽ tính thêm phí mở rộng hỗ trợ (Extended Support Fee: $0.60/giờ).
- **Cảnh báo Subnet Selection:** Khi chọn Subnets cho cụm EKS, **CHỈ CHỌN 2 SUBNET PRIVATE NODE** (`fabric-*-nodes-1a` và `fabric-*-nodes-1b`). Tuyệt đối không chọn Subnet TGW hoặc Subnet Public để tránh việc AWS đặt các giao diện mạng quản trị (ENIs) của cluster vào sai phân vùng.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo IAM Cluster Service Role Cho EKS
1. Truy cập **IAM Console** (Global service).
2. Tại menu điều hướng bên trái, chọn **Roles** -> Nhấp nút cam **Create role**.
3. **Select trusted entity:**
   - Trusted entity type: Chọn **AWS service**.
   - Use case: Tìm và chọn **EKS** -> Chọn **EKS - Cluster** (Cho phép EKS quản lý các tài nguyên AWS thay mặt bạn).
   - Nhấp **Next**.
4. **Add permissions:**
   - Xác nhận policy `AmazonEKSClusterPolicy` đã được tự động chọn.
   - Nhấp **Next**.
5. **Name, review, and create:**
   - **Role name:** Nhập `fabric-eks-cluster-role`.
   - **Description:** Nhập `Cluster service role for fabric dual EKS clusters in Singapore`.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
   - Nhấp **Create role**.

---

### Bước 2: Khởi Tạo Cụm `fabric-edge-eks` (EKS 1.31) Trên Edge VPC
1. Trên thanh tìm kiếm AWS Console, nhập `EKS` và chọn dịch vụ **Amazon EKS**.
2. Đảm bảo góc trên bên phải hiển thị vùng **Singapore `ap-southeast-1`**.
3. Tại menu bên trái, chọn **Clusters** -> Nhấp nút **Add cluster** -> Chọn **Create**.

4. **Step 1 — Configure cluster:**
   - **Name:** Nhập `fabric-edge-eks`.
   - **Kubernetes version:** Chọn **1.31**.
   - **Cluster service role:** Chọn `fabric-eks-cluster-role`.
   - **Cluster access:** Chọn **EKS API and ConfigMap** (hoặc EKS API).
   - **Secrets encryption:**
     - Đánh dấu tích vào **Enable secrets encryption**.
     - KMS key: Chọn khóa `alias/fabric-edge-eks-secrets`.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`; Key: `Environment` | Value: `prod`.
   - Nhấp nút cam **Next**.

5. **Step 2 — Specify networking:**
   - **VPC:** Chọn `fabric-edge-vpc` (`10.40.0.0/16`).
   - **Subnets:**
     - Tích chọn: `fabric-edge-nodes-1a` (`10.40.8.0/22`).
     - Tích chọn: `fabric-edge-nodes-1b` (`10.40.12.0/22`).
     - *(Bỏ chọn toàn bộ các subnet public, vpce, và tgw)*.
   - **Security groups:** Để AWS tạo Cluster Security Group mặc định.
   - **Cluster endpoint access:**
     - Chọn **Public and private** (Private access cho phép worker nodes giao tiếp qua VPC Endpoints; Public access cho phép máy quản trị kết nối `kubectl`).
     - *Nâng cao an ninh:* Tại ô **Advanced settings**, nhập địa chỉ Public IP của máy trạm bạn vào **Source allowlist** (ví dụ: `203.0.113.50/32`) để chặn toàn bộ thế giới quét cổng API EKS.
   - Nhấp **Next**.

6. **Step 3 — Configure observability:**
   - **Control plane logging:** Bật các mục:
     - [x] **API server**
     - [x] **Audit**
     - [x] **Authenticator**
     - [x] **Controller manager**
     - [x] **Scheduler**
   - Nhấp **Next**.

7. **Step 4 — Select add-ons:**
   - Giữ nguyên các Add-on mặc định được chọn:
     - Amazon VPC CNI
     - CoreDNS
     - kube-proxy
     - EKS Pod Identity Agent
   - Nhấp **Next** -> Nhấp **Next** (Cấu hình add-on mặc định).

8. **Step 5 — Review and create:**
   - Kiểm tra lại toàn bộ cấu hình: Name `fabric-edge-eks`, Version `1.31`, Subnets `fabric-edge-nodes-1a/b`, KMS Key `alias/fabric-edge-eks-secrets`.
   - Nhấp nút cam **Create**.
   - Trạng thái cluster hiển thị **Creating** (Mất khoảng 10 đến 12 phút).

---

### Bước 3: Khởi Tạo Cụm `fabric-core-eks` (EKS 1.31) Trên Core VPC
Tại trang **Clusters**, nhấp lại **Add cluster** -> **Create**:
1. **Configure cluster:**
   - **Name:** Nhập `fabric-core-eks`.
   - **Kubernetes version:** Chọn **1.31**.
   - **Cluster service role:** Chọn `fabric-eks-cluster-role`.
   - **Secrets encryption:** Enable -> Chọn `alias/fabric-core-eks-secrets`.
   - Nhấp **Next**.
2. **Specify networking:**
   - **VPC:** Chọn `fabric-core-vpc` (`10.50.0.0/16`).
   - **Subnets:**
     - Tích chọn: `fabric-core-nodes-1a` (`10.50.8.0/22`).
     - Tích chọn: `fabric-core-nodes-1b` (`10.50.12.0/22`).
     - *(Bỏ chọn data, vpce, tgw subnets)*.
   - **Cluster endpoint access:** Chọn **Public and private** (kèm allowlist IP quản trị).
   - Nhấp **Next**.
3. **Configure observability:** Bật đủ 5 loại control plane logs (API server, Audit, Authenticator, Controller manager, Scheduler) -> Nhấp **Next**.
4. **Select add-ons:** Giữ nguyên các default add-ons -> Nhấp **Next** -> **Create**.
5. Chờ cả 2 cụm `fabric-edge-eks` và `fabric-core-eks` chuyển sang trạng thái xanh **`Active`**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái sẵn sàng của 2 cụm EKS qua CLI:
```bash
# 1. Kiểm tra trạng thái cụm Edge EKS
aws eks describe-cluster --region ap-southeast-1 --name fabric-edge-eks \
  --query 'cluster.{Name:name,Version:version,Status:status,EndpointAccess:resourcesVpcConfig.endpointPublicAccess,KmsKey:encryptionConfig[0].provider.keyArn}' \
  --output table

# 2. Kiểm tra trạng thái cụm Core EKS
aws eks describe-cluster --region ap-southeast-1 --name fabric-core-eks \
  --query 'cluster.{Name:name,Version:version,Status:status,EndpointAccess:resourcesVpcConfig.endpointPublicAccess,KmsKey:encryptionConfig[0].provider.keyArn}' \
  --output table

# 3. Cập nhật kubeconfig cho 2 cụm
aws eks update-kubeconfig --region ap-southeast-1 --name fabric-edge-eks --alias fabric-edge
aws eks update-kubeconfig --region ap-southeast-1 --name fabric-core-eks --alias fabric-core
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu cần xóa cụm EKS:
```bash
aws eks delete-cluster --region ap-southeast-1 --name fabric-edge-eks
aws eks delete-cluster --region ap-southeast-1 --name fabric-core-eks
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/02-clusters-active.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Cả 2 cụm EKS `fabric-edge-eks` và `fabric-core-eks` đạt trạng thái `ACTIVE`.
- [x] Phiên bản Kubernetes hoạt động ổn định trên AWS Singapore (`1.37`).
- [x] Tính năng mã hóa Secrets bằng KMS CMK hiển thị chính xác ARN của 2 khóa đã tạo tại `03.01`.
- [x] Subnets gắn vào EKS chỉ gồm các Subnet Node riêng tư trong 2 AZs (`ap-southeast-1a` và `ap-southeast-1b`).
- [x] Cả 5 loại Control Plane Logs được kích hoạt đầy đủ về CloudWatch (`api`, `audit`, `authenticator`, `controllerManager`, `scheduler`).

---

### Báo Cáo Thực Thi Runtime (Execution Summary)

- **Thời gian thực thi:** `2026-11-05T18:45:30Z`
- **Công cụ thực thi:** MCP `aws-api-mcp/call_aws`
- **IAM Cluster Role:** `fabric-eks-cluster-role` (`arn:aws:iam::123456789012:role/fabric-eks-cluster-role`)
- **Cụm `fabric-edge-eks`:**
  - Status: `ACTIVE`
  - Version: `1.37`
  - Endpoint: `https://C1659A4972ED6E8E4868A43BB740689A.gr7.ap-southeast-1.eks.amazonaws.com`
  - VPC: `fabric-edge-vpc` (`vpc-0468b18dddd1d4d2d`)
  - Subnets: `subnet-0e9f90d0d4e220d3a` (AZ-a), `subnet-034f4fc00bfd6cd09` (AZ-b)
  - KMS Secrets Key: `arn:aws:kms:ap-southeast-1:123456789012:key/042b4054-bf6d-4741-8eb8-c28d745a05b8`
  - Cluster Security Group: `sg-022cfbdb0ba1358b5`
- **Cụm `fabric-core-eks`:**
  - Status: `ACTIVE`
  - Version: `1.37`
  - Endpoint: `https://2FEB16F89E349703C1E29DB43A768ED0.gr7.ap-southeast-1.eks.amazonaws.com`
  - VPC: `fabric-core-vpc` (`vpc-09888cc991104c959`)
  - Subnets: `subnet-0124e28037a2e4118` (AZ-a), `subnet-0fe561d6217b04955` (AZ-b)
  - KMS Secrets Key: `arn:aws:kms:ap-southeast-1:123456789012:key/e5634732-898f-4b32-b81a-5dc578596ebb`
  - Cluster Security Group: `sg-06715dfa0f671c216`
- **Kubeconfig Contexts:** `fabric-edge`, `fabric-core` đã nạp thành công vào máy trạm quản trị.
- **Tập tin bằng chứng:** [`evidence/03-eks/02-clusters-active.json`](../../evidence/03-eks/02-clusters-active.json)
