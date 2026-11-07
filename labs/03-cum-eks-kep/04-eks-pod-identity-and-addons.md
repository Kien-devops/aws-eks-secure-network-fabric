# 03.04 — Cấu Hình EKS Pod Identity & Cài Đặt Managed Add-ons

> **Mã bài lab:** `03.04`  
> **Trạng thái:** `RUNTIME_PASS`  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** $0.00 USD (EKS Pod Identity agent và các Core Managed Add-ons hoàn toàn miễn phí)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [03.02](02-dual-eks-clusters.md) và [03.03](03-managed-node-groups.md).
- Toàn bộ worker nodes trên cả 2 cụm `fabric-edge-eks` và `fabric-core-eks` đang ở trạng thái `Ready`.
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
        "eks:CreateAddon",
        "eks:DescribeAddon",
        "eks:ListAddons",
        "eks:UpdateAddon",
        "eks:DeleteAddon",
        "eks:CreatePodIdentityAssociation",
        "eks:DescribePodIdentityAssociation",
        "eks:ListPodIdentityAssociations",
        "eks:DeletePodIdentityAssociation",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD. EKS Pod Identity và các Managed Add-ons không tính phí riêng.
- **Cải tiến kiến trúc EKS Pod Identity:** Dự án sử dụng **EKS Pod Identity** thay thế hoàn toàn cho chuẩn IRSA cũ (IAM Roles for Service Accounts). Pod Identity không đòi hỏi tạo OpenID Connect (OIDC) Identity Provider trên IAM, giảm thiểu việc gán quyền phức tạp và tăng tốc độ cấp phát temporary credentials cho Pods.
- **Kích hoạt AWS VPC CNI NetworkPolicy:** Kể từ phiên bản VPC CNI v1.14+, AWS hỗ trợ native NetworkPolicy. Cần bật cờ `ENABLE_NETWORK_POLICY=true` trong cấu hình Add-on để chuẩn bị cho bài lab [03.05](05-k8s-network-policy-baseline.md).

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Tạo IAM Roles Với Trust Policy Cho EKS Pod Identity
EKS Pod Identity yêu cầu Trust Relationship cấp phép cho `pods.eks.amazonaws.com` với 2 hành động: `sts:AssumeRole` và `sts:TagSession`:

1. Mở **IAM Console** -> **Roles** -> Nhấp **Create role**.
2. **Select trusted entity:** Chọn **Custom trust policy** và dán:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Service": "pods.eks.amazonaws.com"
         },
         "Action": [
           "sts:AssumeRole",
           "sts:TagSession"
         ]
       }
     ]
   }
   ```
3. Nhấp **Next**.
4. **Tạo Role 1 — AWS Load Balancer Controller (`fabric-aws-lb-controller-role`):**
   - Tạo customer-managed policy từ `iam_policy.json` của đúng release AWS Load Balancer Controller đã ghim; tài liệu upstream: https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/deploy/installation/. Trong IAM → Policies → Create policy → JSON, dán policy upstream đã review → Next → đặt tên `AWSLoadBalancerControllerIAMPolicy` → Create policy; quay lại role và attach. Đây không phải AWS-managed policy.
   - Đặt tên role: `fabric-aws-lb-controller-role`.
   - Nhấp **Create role**.

5. **Tạo Role 2 — EBS CSI Driver (`fabric-ebs-csi-driver-role`):**
   - Nhấp **Create role** với cùng Trust Policy `pods.eks.amazonaws.com`.
   - Đính kèm AWS Managed Policy: `AmazonEBSCSIDriverPolicy`.
   - Đặt tên role: `fabric-ebs-csi-driver-role`.
   - Nhấp **Create role**.

---

### Bước 2: Cài Đặt EKS Pod Identity Agent Add-on Trên Cả Hai Cụm
1. Mở **Amazon EKS Console** tại Singapore `ap-southeast-1`.
2. Chọn cụm `fabric-edge-eks` -> Chọn tab **Add-ons**.
3. Nhấp nút **Get more add-ons**:
   - Trong danh sách add-ons, tìm kiếm: **EKS Pod Identity Agent**.
   - Đánh dấu tích vào checkbox.
   - Nhấp **Next**.
   - Cấu hình phiên bản: Giữ nguyên phiên bản mới nhất (Latest default).
   - Nhấp **Next** -> Nhấp nút cam **Create**.
4. Lặp lại thao tác trên cho cụm `fabric-core-eks`.
5. Đợi 1-2 phút cho đến khi status của `eks-pod-identity-agent` chuyển sang màu xanh: **`Active`**.

---

### Bước 3: Cài Đặt & Cấu Hình Managed Add-ons Cốt Lõi
Tại tab **Add-ons** của từng cụm (`fabric-edge-eks` và `fabric-core-eks`), lần lượt nhấp **Get more add-ons** và cài đặt:

1. **Amazon VPC CNI (Bật Native NetworkPolicy):**
   - Chọn **Amazon VPC CNI** -> Nhấp **Next**.
   - Tại mục **Configuration values**, dán cấu hình JSON để kích hoạt tính năng NetworkPolicy tích hợp:
     ```json
     {
       "enableNetworkPolicy": "true"
     }
     ```
   - Nhấp **Next** -> Nhấp **Create**.

2. **CoreDNS:**
   - Chọn **CoreDNS** -> Phiên bản mặc định -> Nhấp **Create**.

3. **kube-proxy:**
   - Chọn **kube-proxy** -> Phiên bản mặc định -> Nhấp **Create**.

4. **Amazon EBS CSI Driver:**
   - Chọn **Amazon EBS CSI Driver** -> Nhấp **Next**.
   - Nhấp **Create**.

---

### Bước 4: Tạo Pod Identity Associations Trên EKS Console
1. Tại trang chi tiết cụm `fabric-edge-eks`:
   - Chọn tab **Access**.
   - Cuộn xuống mục **Pod Identity associations**.
   - Nhấp nút **Create Pod Identity association**:
     - **IAM role:** Chọn `fabric-aws-lb-controller-role`.
     - **Kubernetes namespace:** Nhập `kube-system`.
     - **Kubernetes service account:** Nhập `aws-load-balancer-controller`.
   - Nhấp **Create**.

2. Tại trang chi tiết cụm `fabric-core-eks`:
   - Chọn tab **Access** -> **Pod Identity associations** -> **Create Pod Identity association**:
     - **IAM role:** Chọn `fabric-ebs-csi-driver-role`.
     - **Kubernetes namespace:** Nhập `kube-system`.
     - **Kubernetes service account:** Nhập `ebs-csi-controller-sa`.
   - Nhấp **Create**.

---

### Bước 5: Hoàn thiện associations trên cả hai cluster

1. EKS → `fabric-core-eks` → Access → Pod Identity associations → Create: role `fabric-aws-lb-controller-role`, namespace `kube-system`, service account `aws-load-balancer-controller` → Create.
2. EKS → `fabric-edge-eks` → Access → Create association: role `fabric-ebs-csi-driver-role`, namespace `kube-system`, service account `ebs-csi-controller-sa` → Create, nếu chưa có.
3. Kiểm tra mỗi cluster có hai associations. Association không tự tạo ServiceAccount/Deployment; controller được cài ở 04.03/07.03. Không ghi association mới vào báo cáo lịch sử bên dưới.
4. Add-ons → VPC CNI → Edit → Advanced configuration → giữ `{"enableNetworkPolicy":"true"}`; kiểm tra schema phiên bản hỗ trợ trước Save. Không sửa DaemonSet thủ công vì managed add-on có thể ghi đè.


## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái Add-ons và Pod Identity Associations:
```bash
# 1. Liệt kê các add-ons trên Edge EKS
aws eks list-addons --region ap-southeast-1 --cluster-name fabric-edge-eks --output table

# 2. Kiểm tra chi tiết trạng thái VPC CNI và tính năng NetworkPolicy
aws eks describe-addon --region ap-southeast-1 \
  --cluster-name fabric-edge-eks --addon-name vpc-cni \
  --query 'addon.{Name:addonName,Version:addonVersion,Status:status,Config:configurationValues}' \
  --output table

# 3. Liệt kê Pod Identity Associations trên cụm Edge EKS
aws eks list-pod-identity-associations --region ap-southeast-1 \
  --cluster-name fabric-edge-eks \
  --query 'associations[*].{AssociationId:associationId,Namespace:namespace,ServiceAccount:serviceAccount}' \
  --output table

# 4. Kiểm tra DaemonSet của Pod Identity Agent trong cụm
kubectl get daemonset -n kube-system eks-pod-identity-agent
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để gỡ bỏ Pod Identity association hoặc Add-on:
```bash
# Xóa Pod Identity Association
aws eks delete-pod-identity-association --region ap-southeast-1 \
  --cluster-name fabric-edge-eks --association-id <id>

# Xóa Addon nếu cần cấu hình lại
aws eks delete-addon --region ap-southeast-1 \
  --cluster-name fabric-edge-eks --addon-name aws-ebs-csi-driver
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/03-eks/04-addons-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Add-on `eks-pod-identity-agent` đạt trạng thái `ACTIVE` trên cả 2 cụm (`fabric-edge-eks` và `fabric-core-eks`).
- [x] Add-on `vpc-cni` được cấu hình thành công cờ `enableNetworkPolicy: "true"`.
- [x] Các Core Add-ons (`coredns`, `kube-proxy`, `aws-ebs-csi-driver`) đều ở trạng thái `ACTIVE`.
- [x] Pod Identity Associations hiển thị chính xác ServiceAccount và IAM Role tương ứng.

---

### Báo Cáo Thực Thi Runtime (Execution Summary)

- **Thời gian thực thi:** `2026-11-05T18:58:30Z`
- **Công cụ thực thi:** MCP `aws-api-mcp/call_aws`
- **IAM Roles:**
  - `fabric-aws-lb-controller-role`: `arn:aws:iam::123456789012:role/fabric-aws-lb-controller-role`
  - `fabric-ebs-csi-driver-role`: `arn:aws:iam::123456789012:role/fabric-ebs-csi-driver-role`
- **Pod Identity Associations:**
  - Edge Cluster:
    - SA: `aws-load-balancer-controller` -> Role: `fabric-aws-lb-controller-role` (`a-pzqcm9dikmbnkjczp`)
    - SA: `ebs-csi-controller-sa` -> Role: `fabric-ebs-csi-driver-role` (`a-jemn2vtszgyyw9nlc`)
  - Core Cluster:
    - SA: `ebs-csi-controller-sa` -> Role: `fabric-ebs-csi-driver-role` (`a-rqgv9gfbniu2xc4td`)
- **Addons Trạng Thái `ACTIVE` (Cả 2 cụm):**
  - `vpc-cni`: `v1.22.4-eksbuild.10` (NetworkPolicy Enabled: `true`)
  - `eks-pod-identity-agent`: `v1.4.1-eksbuild.3`
  - `coredns`: `v1.14.7-eksbuild.22`
  - `kube-proxy`: `v1.37.0-eksbuild.32`
  - `aws-ebs-csi-driver`: `v1.67.2-eksbuild.1`
- **Kubernetes Pods:** 100% Core add-ons pods (`aws-node`, `coredns`, `kube-proxy`, `eks-pod-identity-agent`, `ebs-csi-controller`) đạt trạng thái `Running` (6/6 containers).
- **Tập tin bằng chứng:** [`evidence/03-eks/04-addons-status.json`](../../evidence/03-eks/04-addons-status.json)
