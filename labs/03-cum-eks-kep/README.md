# Module 03: Triển Khai Cụm Kubernetes EKS Kép (Dual Private EKS Clusters)

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Khởi tạo 2 cụm Amazon EKS độc lập, hoàn toàn riêng tư (Private-only API endpoint):
    1. `fabric-edge-eks`: Nằm trong `fabric-edge-vpc` (`10.40.0.0/16`).
    2. `fabric-core-eks`: Nằm trong `fabric-core-vpc` (`10.50.0.0/16`).
  - Sử dụng Kubernetes v1.30+ với AL2023 Managed Node Groups.
  - Kích hoạt mã hóa envelope encryption cho Kubernetes Secrets bằng AWS KMS Customer Managed Key (CMK).
  - Cấu hình EKS Pod Identity Agent cho phân quyền least-privilege.
  - Cài đặt Argo CD phục vụ GitOps và áp dụng bộ quy tắc Kubernetes `NetworkPolicy` mặc định chặn toàn bộ (Default Deny).

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Tạo Khóa KMS CMK Cho Từng Cụm EKS
Tạo KMS Key riêng biệt để mã hóa Secrets:
```bash
aws kms create-key \
  --description "KMS key for EKS Secret Envelope Encryption" \
  --tags TagKey=Project,TagValue=fabric-network \
  --region ap-southeast-1
```

### Bước 2: Khởi tạo Cụm EKS Hoàn Toàn Riêng Tư (Private Cluster)
- Cấu hình Endpoint Access:
  - `endpointPublicAccess = false`
  - `endpointPrivateAccess = true`
- Chọn Private Subnets tương ứng cho Node Groups.
- Gắn KMS CMK ARN vào cấu hình `encryptionConfig` của EKS.

### Bước 3: Cài đặt EKS Add-ons Thiết Yếu
Triển khai các add-on chuẩn qua EKS API:
1. `vpc-cni` (bật Pod Identity support)
2. `coredns`
3. `kube-proxy`
4. `eks-pod-identity-agent`

### Bước 4: Cài đặt Argo CD & NetworkPolicy Mặc Định
1. Cài đặt Argo CD namespace trên cả hai cluster hoặc triển khai theo mô hình Hub-Spoke.
2. Thiết lập chính sách bảo mật mạng mặc định:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

---

## 3. Xác Minh (Verification)
Kiểm tra trạng thái cluster và KMS encryption:
```bash
aws eks describe-cluster \
  --name fabric-edge-eks \
  --region ap-southeast-1 \
  --query 'cluster.{Name:name,Status:status,EndpointAccess:resourcesVpcConfig.endpointPublicAccess,KMS:encryptionConfig[0].provider.keyArn}' \
  --output table
```

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Cả 2 cụm EKS ở trạng thái `ACTIVE` với API endpoint hoàn toàn Private (`endpointPublicAccess = false`).
- [ ] Khóa KMS CMK được liên kết thành công để mã hóa Kubernetes Secrets.
- [ ] EKS Pod Identity Agent add-on đã được kích hoạt.
- [ ] Chính sách NetworkPolicy Default Deny được áp dụng thành công.
