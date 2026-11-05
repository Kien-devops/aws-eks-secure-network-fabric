# 03.02 — Khởi Tạo 2 Cụm Private EKS Độc Lập (Edge EKS & Core EKS)

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Khởi tạo cụm điều khiển EKS Control Plane cho `fabric-edge-eks` và `fabric-core-eks` với chế độ hoàn toàn riêng tư.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo 2 cụm Kubernetes EKS (phiên bản v1.30):
  1. `fabric-edge-eks` trong `fabric-edge-vpc`.
  2. `fabric-core-eks` trong `fabric-core-vpc`.
- **Cấu hình bảo mật API Server Endpoint:**
  - `endpointPublicAccess`: `false` (Khóa toàn bộ truy cập từ Internet vào API server).
  - `endpointPrivateAccess`: `true` (Chỉ cho phép truy cập qua mạng nội bộ).
- Gắn khóa KMS CMK tương ứng vào cấu hình Envelope Encryption của etcd.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Khởi Tạo IAM Role Cho EKS Cluster
1. Tại dịch vụ **IAM**, tạo Role với Trusted Entity là `eks.amazonaws.com`.
2. Gắn policy: `AmazonEKSClusterPolicy`.
3. Đặt tên: `fabric-eks-cluster-role`.

---

### Bước 2: Tạo Cụm `fabric-edge-eks`
1. Mở dịch vụ **Amazon EKS** tại Region Singapore (`ap-southeast-1`).
2. Chọn **Clusters** -> Nhấp nút cam **Create cluster** -> Chọn **Create standard cluster**.
3. **Configure cluster:**
   - **Name:** `fabric-edge-eks`
   - **Kubernetes version:** Chọn `1.30` (hoặc mới nhất).
   - **Cluster service role:** Chọn `fabric-eks-cluster-role`.
   - Nhấp **Next**.
4. **Specify networking:**
   - **VPC:** Chọn `fabric-edge-vpc`.
   - **Subnets:** Chọn 2 subnets Private Node (`fabric-edge-node-1a` và `fabric-edge-node-1b`).
   - **Cluster endpoint access:** Chọn radio button **Private** (Chỉ truy cập nội bộ).
   - Nhấp **Next**.
5. **Configure observability:**
   - Bật Control plane logging: `API server`, `Audit`, `Authenticator`.
   - Nhấp **Next**.
6. **Configure encryption:**
   - Tại mục **Secrets encryption**: Tích chọn **Enable**.
   - **Key:** Chọn alias `alias/fabric-edge-eks-secrets-key`.
   - Nhấp **Next** -> Nhấp **Create**.

---

### Bước 3: Tạo Cụm `fabric-core-eks`
Lặp lại thao tác tương tự cho cụm thứ 2:
- **Name:** `fabric-core-eks`
- **VPC:** Chọn `fabric-core-vpc`
- **Subnets:** Chọn `fabric-core-node-1a` và `fabric-core-node-1b`.
- **Cluster endpoint access:** Chọn **Private**.
- **Secrets encryption:** Chọn alias `alias/fabric-core-eks-secrets-key`.
- Nhấp **Create**.

---

## 3. Xác Minh (Verification)

Chạy lệnh kiểm tra trạng thái cluster và cấu hình mã hóa:
```bash
aws eks describe-cluster \
  --name fabric-edge-eks \
  --region ap-southeast-1 \
  --query 'cluster.{Name:name,Status:status,PrivateAccess:resourcesVpcConfig.endpointPrivateAccess,PublicAccess:resourcesVpcConfig.endpointPublicAccess,KMS:encryptionConfig[0].provider.keyArn}' \
  --output table
```
> Kết quả: `Status: ACTIVE`, `PrivateAccess: True`, `PublicAccess: False`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Cả 2 cụm EKS chuyển sang trạng thái `ACTIVE`.
- [ ] Truy cập công khai API server bị khóa (`PublicAccess = False`).
- [ ] Cấu hình KMS encryption gắn đúng Key ARN cho từng cluster.
