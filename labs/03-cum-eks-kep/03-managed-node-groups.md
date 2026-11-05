# 03.03 — Khởi Tạo Managed Node Groups Đa AZ Trên Hệ Điều Hành Amazon Linux 2023

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Khởi tạo cụm máy chủ worker nodes chạy trên Private Subnets cho cả 2 cụm EKS.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo IAM Role `fabric-eks-nodegroup-role` cho Worker Nodes.
- Khởi tạo 2 Managed Node Groups:
  1. `fabric-edge-ng` trên `fabric-edge-eks`.
  2. `fabric-core-ng` trên `fabric-core-eks`.
- Đặt Worker Nodes trong các Private Subnets, trải đều trên 2 AZs (`ap-southeast-1a`, `ap-southeast-1b`).
- Sử dụng AMI chuẩn doanh nghiệp: **Amazon Linux 2023 (AL2023_x86_64_STANDARD)**.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Khởi Tạo IAM Role Cho Node Group
1. Mở dịch vụ **IAM** -> Tạo Role với Trusted Entity là `ec2.amazonaws.com`.
2. Gắn 3 policy bắt buộc của AWS:
   - `AmazonEKSWorkerNodePolicy`
   - `AmazonEKS_CNI_Policy`
   - `AmazonEC2ContainerRegistryReadOnly`
3. Đặt tên Role: `fabric-eks-nodegroup-role`.

---

### Bước 2: Tạo Node Group Cho `fabric-edge-eks`
1. Tại dịch vụ **EKS Console**, chọn cụm `fabric-edge-eks`.
2. Mở tab **Compute** -> Tại mục **Node groups**, nhấp nút **Add node group**.
3. **Configure node group:**
   - **Name:** `fabric-edge-ng`
   - **Node IAM Role:** Chọn `fabric-eks-nodegroup-role`.
   - Nhấp **Next**.
4. **Set compute and scaling configuration:**
   - **AMI type:** Chọn `Amazon Linux 2023 (AL2023_x86_64_STANDARD)`.
   - **Capacity type:** `On-Demand`.
   - **Instance types:** `t3.medium` (hoặc `c6i.large` cho workload lớn).
   - **Disk size:** `30 GiB` gp3.
   - **Scaling configuration:** Minimum: `2`, Maximum: `4`, Desired: `2`.
   - Nhấp **Next**.
5. **Specify networking:**
   - **Subnets:** Chọn đúng 2 Private Node Subnets: `fabric-edge-node-1a` và `fabric-edge-node-1b`.
   - **Configure SSH access:** Tắt (`Disable`).
   - Nhấp **Next** -> Nhấp **Create**.

---

### Bước 3: Tạo Node Group Cho `fabric-core-eks`
Thực hiện tương tự trên cụm `fabric-core-eks`:
- **Name:** `fabric-core-ng`
- **Subnets:** Chọn `fabric-core-node-1a` và `fabric-core-node-1b`.
- **Instance types:** `t3.medium` / `c6i.large`.
- **Desired/Min/Max:** `2` / `2` / `4`.
- Nhấp **Create**.

---

## 3. Xác Minh (Verification)

Kiểm tra trạng thái Node Group qua AWS CLI:
```bash
aws eks describe-nodegroup \
  --cluster-name fabric-edge-eks \
  --nodegroup-name fabric-edge-ng \
  --region ap-southeast-1 \
  --query 'nodegroup.{Name:nodegroupName,Status:status,Subnets:subnets,DesiredSize:scalingConfig.desiredSize}' \
  --output table
```
> Kết quả: `Status = ACTIVE`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Cả 2 Node Groups đều chuyển sang trạng thái `ACTIVE`.
- [ ] Worker Nodes chỉ được cấp IP riêng tư thuộc dải Private Subnet (`10.40.10.0/22` và `10.50.10.0/22`), không có Public IP.
