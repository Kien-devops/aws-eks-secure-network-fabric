# 03.03 — Khởi Tạo Managed Node Groups Riêng Tư Cho Hai Cụm EKS

> **Mã bài lab:** `03.03`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** ~$0.0416 USD / giờ / instance t3.medium (4 instances = ~$0.166 USD / giờ)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `nodes-1a`, `nodes-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [03.02](02-dual-eks-clusters.md). Cả 2 cụm EKS (`fabric-edge-eks` và `fabric-core-eks`) đang ở trạng thái xanh `ACTIVE`.
- **Yêu cầu kết nối mạng bắt buộc:** Private VPC Endpoints tại lab [02.06](../02-ha-tang-mang-co-ban/06-private-vpc-endpoints.md) (ECR API, ECR DKR, S3 Gateway, STS, EC2, Logs) HOẶC đường Egress NAT qua TGW phải sẵn sàng để các worker nodes bootstrap và join cluster.
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
        "eks:CreateNodegroup",
        "eks:DescribeNodegroup",
        "eks:ListNodegroups",
        "eks:DeleteNodegroup",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole",
        "ec2:RunInstances",
        "ec2:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** 4 EC2 instances `t3.medium` (2 nodes cho Edge cluster, 2 nodes cho Core cluster) tiêu tốn ~$4.00 USD/ngày. Cần chú ý theo dõi ngân sách $50.00 USD.
- **Cảnh báo Node Subnet Placement:** Các worker nodes **CHỈ ĐƯỢC PHÉP ĐẶT TRONG PRIVATE NODE SUBNETS** (`fabric-edge-nodes-1a/b` và `fabric-core-nodes-1a/b`). Tuyệt đối không chọn Public subnets, Data subnets hoặc TGW subnets.
- **Cảnh báo AMI Type:** Khuyến nghị sử dụng **Amazon Linux 2023 (AL2023_x86_64_STANDARD)** là chuẩn AMI tối ưu hóa mới nhất của AWS cho EKS 1.31, hỗ trợ cgroups v2 và container runtime `containerd`.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo IAM Role Cho Worker Nodes (`fabric-eks-node-role`)
1. Mở **IAM Console** (Global service).
2. Tại menu bên trái, chọn **Roles** -> Nhấp nút cam **Create role**.
3. **Select trusted entity:**
   - Trusted entity type: Chọn **AWS service**.
   - Use case: Chọn **EC2** (Cho phép máy ảo EC2 gọi các dịch vụ AWS).
   - Nhấp **Next**.
4. **Add permissions:**
   - Trong ô tìm kiếm chính sách, lần lượt tìm và đánh dấu tích vào 4 AWS Managed Policies:
     1. [x] **`AmazonEKSWorkerNodePolicy`** (Cấp quyền kết nối tới EKS Control Plane).
     2. [x] **`AmazonEC2ContainerRegistryReadOnly`** (Cấp quyền kéo container images từ ECR).
     3. [x] **`AmazonEKS_CNI_Policy`** (Cấp quyền cho VPC CNI cấp phát ENIs và địa chỉ IP cho Pods).
     4. [x] **`AmazonSSMManagedInstanceCore`** (Cấp quyền kết nối SSM Session Manager an toàn, loại bỏ hoàn toàn nhu cầu mở SSH port 22).
   - Nhấp **Next**.
5. **Name, review, and create:**
   - **Role name:** Nhập `fabric-eks-node-role`.
   - **Description:** Nhập `Worker node instance role for fabric EKS clusters in Singapore`.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
   - Nhấp **Create role**.

---

### Bước 2: Tạo Managed Node Group Cho Cụm `fabric-edge-eks`
1. Trên thanh tìm kiếm AWS Console, nhập `EKS` và chọn **Amazon EKS**.
2. Chọn cụm `fabric-edge-eks` trong danh sách Clusters.
3. Chọn tab **Compute** ở giữa màn hình.
4. Tại mục **Node groups**, nhấp nút **Add node group**:

   - **Step 1 — Configure node group:**
     - **Name:** Nhập `fabric-edge-ng-1`.
     - **Node IAM role:** Chọn `fabric-eks-node-role`.
     - **Kubernetes labels:** Nhấp **Add label**:
       - Key: `node.kubernetes.io/tier` | Value: `edge`
       - Key: `environment` | Value: `prod`
     - Nhấp **Next**.

   - **Step 2 — Set compute and scaling configuration:**
     - **AMI type:** Chọn **Amazon Linux 2023 (AL2023_x86_64_STANDARD)**.
     - **Capacity type:** Chọn **On-Demand**.
     - **Instance types:** Chọn `t3.medium` (2 vCPU, 4 GiB Memory - đáp ứng tốt nhu cầu workloads và CNI).
     - **Disk size:** Nhập `20` GiB (loại gp3).
     - **Node group scaling configuration:**
       - **Minimum size:** Nhập `2`.
       - **Maximum size:** Nhập `3`.
       - **Desired size:** Nhập `2`.
     - Nhấp **Next**.

   - **Step 3 — Specify networking:**
     - **Subnets:**
       - Tích chọn: `fabric-edge-nodes-1a` (`10.40.10.0/22`).
       - Tích chọn: `fabric-edge-nodes-1b` (`10.40.14.0/22`).
       - *(Đảm bảo bỏ chọn các subnet khác)*.
     - **Configure SSH access to nodes:** Chọn **Disable** (Kết nối quản trị hoàn toàn thông qua AWS Systems Manager / SSM).
     - Nhấp **Next**.

   - **Step 4 — Review and create:**
     - Kiểm tra lại các thông số và nhấp nút cam **Create**.
     - Node group sẽ chuyển sang trạng thái **Creating** (Mất khoảng 3 đến 5 phút để các máy ảo EC2 khởi chạy và gia nhập cluster).

---

### Bước 3: Tạo Managed Node Group Cho Cụm `fabric-core-eks`
Quay lại trang chi tiết cụm `fabric-core-eks` -> Tab **Compute** -> Nhấp **Add node group**:
1. **Configure node group:**
   - **Name:** Nhập `fabric-core-ng-1`.
   - **Node IAM role:** Chọn `fabric-eks-node-role`.
   - **Kubernetes labels:**
     - Key: `node.kubernetes.io/tier` | Value: `core`
     - Key: `environment` | Value: `prod`
   - Nhấp **Next**.
2. **Set compute and scaling configuration:**
   - **AMI type:** Chọn **Amazon Linux 2023 (AL2023_x86_64_STANDARD)**.
   - **Instance types:** `t3.medium`.
   - **Disk size:** `20` GiB.
   - **Scaling configuration:** Minimum: `2`, Desired: `2`, Maximum: `4`.
   - Nhấp **Next**.
3. **Specify networking:**
   - **Subnets:**
     - Tích chọn: `fabric-core-nodes-1a` (`10.50.10.0/22`).
     - Tích chọn: `fabric-core-nodes-1b` (`10.50.14.0/22`).
   - **SSH access:** Disable.
   - Nhấp **Next**.
4. **Review and create:** Nhấp **Create**.
5. Đợi cho đến khi cả 2 Node Groups (`fabric-edge-ng-1` và `fabric-core-ng-1`) hiển thị trạng thái xanh **`Active`**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái các node groups và xác nhận các Kubernetes worker nodes đã `Ready`:
```bash
# 1. Kiểm tra trạng thái Node Group qua AWS CLI
aws eks describe-nodegroup --region ap-southeast-1 \
  --cluster-name fabric-edge-eks --nodegroup-name fabric-edge-ng-1 \
  --query 'nodegroup.{Name:nodegroupName,Status:status,Desired:scalingConfig.desiredSize,InstanceTypes:instanceTypes[0]}' \
  --output table

aws eks describe-nodegroup --region ap-southeast-1 \
  --cluster-name fabric-core-eks --nodegroup-name fabric-core-ng-1 \
  --query 'nodegroup.{Name:nodegroupName,Status:status,Desired:scalingConfig.desiredSize,InstanceTypes:instanceTypes[0]}' \
  --output table

# 2. Chuyển context sang fabric-edge và kiểm tra danh sách Node (Tất cả phải Ready)
aws eks update-kubeconfig --region ap-southeast-1 --name fabric-edge-eks --alias fabric-edge
kubectl get nodes -o wide

# 3. Chuyển context sang fabric-core và kiểm tra danh sách Node
aws eks update-kubeconfig --region ap-southeast-1 --name fabric-core-eks --alias fabric-core
kubectl get nodes -o wide
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa Node Groups trước khi xóa cụm EKS:
```bash
aws eks delete-nodegroup --region ap-southeast-1 --cluster-name fabric-edge-eks --nodegroup-name fabric-edge-ng-1
aws eks delete-nodegroup --region ap-southeast-1 --cluster-name fabric-core-eks --nodegroup-name fabric-core-ng-1
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/03-nodes-ready.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 2 Node Groups `fabric-edge-ng-1` và `fabric-core-ng-1` đạt trạng thái `ACTIVE`.
- [ ] Lệnh `kubectl get nodes` hiển thị đủ 4 worker nodes (2 nodes per cluster) ở trạng thái `Ready`.
- [ ] Địa chỉ IP nội bộ của Node nằm trọn vẹn trong dải `10.40.10.0/22` (Edge) và `10.50.10.0/22` (Core).
- [ ] Các Add-on pods cốt lõi (`aws-node`, `coredns`, `kube-proxy`) chạy ổn định `Running`.
