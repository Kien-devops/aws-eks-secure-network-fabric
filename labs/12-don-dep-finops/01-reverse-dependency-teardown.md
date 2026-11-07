# 12.01 — Quy Trình Hủy Tài Nguyên Theo Thứ Tự Phụ Thuộc Ngược (Reverse Teardown)

> **Mã bài lab:** `12.01`  
> **Trạng thái:** `DRAFT`  
> **Thời gian dự kiến:** 60 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn tất toàn bộ các bài lab thực hành và kịch bản GameDay từ Module 00 đến Module 10.
- Đã hoàn tất việc thu thập bằng chứng kỹ thuật và báo cáo tại [Module 11](../11-bang-chung-bao-cao/01-runtime-evidence-collection.md).
- Có quyền quản trị AWS IAM Administrator trên Region Singapore (`ap-southeast-1`).
- Đang mở phiên AWS Management Console.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để hủy toàn bộ tài nguyên theo thứ tự phụ thuộc ngược:
Danh sách dưới là các delete actions chính, chưa phải policy đầy đủ cho mọi thao tác Console. Cần quyền Describe/List, Kubernetes RBAC, WAF disassociate, protection updates, ElastiCache `DeleteReplicationGroup`, Route 53, EBS/snapshots, logs/ECR/S3/secrets/IAM/KMS theo đúng tài nguyên được phép ở inventory. Không gắn policy rộng này vào workload; dùng role cleanup có kiểm soát và chỉ trong cửa sổ được phép.
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DeleteNodegroup",
        "eks:DeleteCluster",
        "rds:DeleteDBCluster",
        "rds:DeleteDBInstance",
        "elasticache:DeleteServerlessCache",
        "elasticache:DeleteCacheCluster",
        "sqs:DeleteQueue",
        "network-firewall:DeleteFirewall",
        "network-firewall:DeleteFirewallPolicy",
        "network-firewall:DeleteRuleGroup",
        "elasticloadbalancing:DeleteLoadBalancer",
        "elasticloadbalancing:DeleteTargetGroup",
        "ec2:TerminateInstances",
        "ec2:DeleteVpcEndpoints",
        "ec2:DeleteTransitGateway",
        "ec2:DeleteTransitGatewayVpcAttachment",
        "ec2:DeleteTransitGatewayRouteTable",
        "ec2:DeleteNatGateway",
        "ec2:ReleaseAddress",
        "ec2:DetachInternetGateway",
        "ec2:DeleteInternetGateway",
        "ec2:DeleteRouteTable",
        "ec2:DeleteSubnet",
        "ec2:DeleteVpc",
        "wafv2:DeleteWebACL",
        "acm:DeleteCertificate"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **CẢNH BÁO HỦY DIỆT KHÔNG THỂ PHỤC HỒI (DESTRUCTIVE ACTION):**
  - Quá trình Teardown sẽ xóa vĩnh viễn toàn bộ cấu hình mạng, máy chủ ảo, cụm EKS, dữ liệu cơ sở dữ liệu và chứng chỉ.
  - **Bắt buộc phải kiểm tra xác nhận:** Thư mục `evidence/` đã lưu trữ đầy đủ các tệp báo cáo và bằng chứng trước khi thực hiện bước này.
- **Tránh Lỗi DependencyViolation & Kẹt ENI:**
  - Không thể xóa VPC khi còn tồn tại Subnet; không thể xóa Subnet khi còn tồn tại ENI; không thể xóa ENI khi còn Load Balancer hoặc EKS Node. Do đó, việc tuân thủ nghiêm ngặt **Thứ Tự Phụ Thuộc Ngược 6 Tầng (Reverse 6-Tier Order)** là điều kiện tiên quyết để việc dọn dẹp diễn ra trôi chảy.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

```text
[Tầng 1: L7 & Ingress]       --> Xóa ALB Ingress, ACM Certificate, Web ACL WAF
         |
         v
[Tầng 2: Workloads & EKS]     --> Xóa EKS Node Groups, EKS Clusters
         |
         v
[Tầng 3: Database & Cache]    --> Xóa Aurora Serverless v2, ElastiCache Redis, SQS
         |
         v
[Tầng 4: Firewalls & GWLB]    --> Xóa AWS Network Firewall, GWLBe, GWLB, Suricata EC2
         |
         v
[Tầng 5: Transit Gateway]     --> Xóa TGW Route Tables, TGW VPC Attachments, TGW
         |
         v
[Tầng 6: Network Base & IPs]  --> Nhả Elastic IPs, xóa NAT GW, IGW, Subnets, VPCs
```

---

### Tầng 1: Xóa Lớp Ingress & An Ninh Biên L7
1. **Dừng reconcile rồi xóa ALB/NLB qua Kubernetes khi controllers còn chạy:**
   - Kiểm kê tài nguyên theo IDs/tags của dự án; không xóa chỉ vì trùng prefix. Lưu manifests, dữ liệu và snapshot cần giữ; xác nhận quyền hủy môi trường.
   - Mở Argo CD của **từng cluster** → Applications → App details → Sync policy → tắt automated sync, prune và selfHeal. Dừng pipeline promotion. Xóa Ingress/Service khỏi desired manifests hoặc ngừng quản lý app; nếu xóa Application, đọc kỹ lựa chọn cascade và finalizer.
   - EKS Console → cluster → Resources → namespace `fabric-apps`: xác định Ingress Edge và LoadBalancer Service Core. Nếu Console không hỗ trợ Delete, dùng `kubectl delete ingress <tên-thật> -n fabric-apps --context fabric-edge` và `kubectl delete service <tên-thật> -n fabric-apps --context fabric-core` từ máy quản trị.
   - Giữ AWS Load Balancer Controller, nodes và IAM associations hoạt động đến khi ALB/NLB, target groups và ENIs do controller tạo đã biến mất trong EC2 Console. Không xóa finalizer để bỏ qua lỗi; xem controller logs/events, IAM và deletion protection khi kẹt.
2. **Xóa Web ACL AWS WAF v2:**
   - Mở **AWS WAF & Shield Console** -> **Web ACLs**.
   - Chọn `fabric-edge-web-acl` -> Nhấp **Delete** -> Nhập `delete` để xác nhận.
3. **Xóa Chứng Chỉ ACM:**
   - Mở **AWS Certificate Manager** → chọn đúng public certificate dùng tại 07.01 → kiểm tra không còn association và không dùng chung → Delete. Không tìm public ACM certificate cho private `.internal`.
4. **Storage và DNS trước khi xóa cluster:**
   - Dừng workload/migration writers, lưu dữ liệu cần giữ. EKS → Resources → PVC/PV: ghi reclaim policy; xóa PVC do lab tạo khi EBS CSI còn chạy, kiểm tra volume đã xóa hoặc ghi rõ volume retained cần xử lý tại 12.02.
   - Route 53 → Hosted zones → `fabric.internal`: xóa records của lab rồi zone nếu do lab sở hữu và không dùng chung; không xóa public zone dùng chung. Xóa đúng public app record của 07.01. Ghi IDs/tên DNS đã xử lý.

---

### Tầng 2: Xóa Cụm EKS Kép & Managed Node Groups
1. Mở **Amazon EKS Console** tại Singapore (`ap-southeast-1`) -> Chọn **Clusters**.
2. **Xóa Node Groups trước:**
   - Nhấp vào cụm `fabric-edge-eks` → Compute → chọn `fabric-edge-ng-1` → Delete → nhập đúng tên xác nhận.
   - Lặp với `fabric-core-eks` và `fabric-core-ng-1`. Đối chiếu inventory nếu tên đã thay đổi; không chọn node group khác.
   - *Thời gian chờ:* Khoảng 3 - 5 phút để CloudFormation hủy Auto Scaling Groups và các máy chủ EC2 worker nodes.
3. **Xóa EKS Clusters:**
   - Sau khi các Node Groups chuyển sang trạng thái biến mất (Deleted):
   - Chọn `fabric-edge-eks` → Delete cluster → xác nhận.
   - Chọn `fabric-core-eks` → Delete cluster → xác nhận.
   - *Thời gian chờ:* Khoảng 5 - 8 phút để hủy Control Planes.

---

### Tầng 3: Xóa Cơ Sở Dữ Liệu, Bộ Nhớ Đệm & Hàng Đợi
1. **Xóa Aurora Serverless v2:**
   - Mở **Amazon RDS Console** -> **Databases**.
   - Mở cluster `fabric-core-db`; tắt deletion protection nếu được phép hủy. Xóa **reader instances trước, writer instance sau**, chờ instances biến mất rồi mới xóa cluster.
   - Actions → Delete; chọn final snapshot/retained backups theo quyết định lưu dữ liệu đã xác nhận. Snapshot còn giữ tiếp tục tính phí; ghi ID/expiry vào 12.02. Chỉ bỏ backup khi đã chấp nhận mất dữ liệu.
   - Đánh dấu chọn ô *I acknowledge that upon deleting this cluster...*.
   - Nhập chuỗi `delete me` -> Nhấp **Delete**.
2. **Xóa ElastiCache replication group:**
   - ElastiCache → Redis OSS caches → chọn replication group `fabric-core-redis` theo 04.01 → Delete. Quyết định final backup trước khi xác nhận; không dùng quy trình Serverless cho replication group provisioned.
3. **Xóa Hàng Đợi SQS:**
   - SQS → chọn `fabric-order-events` và DLQ đã ghi ở 04.01 → kiểm tra messages cần giữ → Delete → xác nhận từng queue.

---

### Tầng 4: Xóa Tường Lửa, GWLB & Máy Chủ Suricata EC2
1. **Xóa AWS Network Firewall:**
   - Mở **VPC Console** -> **AWS Network Firewall** -> **Firewalls**.
   - Chọn `fabric-egress-nfw` -> Nhấp **Delete** -> Nhập tên firewall để xác nhận.
   - *Lưu ý:* Quá trình xóa Firewall Endpoints mất khoảng 3 - 5 phút.
   - Nếu bật delete protection, tắt sau khi xác nhận hủy. Chờ endpoint xóa xong → Firewall policies → xóa `fabric-egress-fw-policy` → Rule groups → xóa đúng groups ghi trong inventory, kiểm tra không dùng chung.
2. **Xóa Gateway Load Balancer Endpoints (GWLBe) & VPC Endpoints:**
   - Mở **VPC Console** -> **Endpoints**.
   - Chọn toàn bộ các VPC Endpoints có tên prefix `fabric-` (`fabric-gwlbe-1a`, `fabric-gwlbe-1b`, S3 Endpoint, ECR Endpoints).
   - Nhấp **Actions** -> Chọn **Delete VPC endpoints** -> Xác nhận xóa.
3. **Xóa Endpoint Service và Gateway Load Balancer:**
   - VPC → Endpoint services → chọn service gắn `fabric-gwlb` → xác nhận không còn endpoint connections → Delete. Không xóa service dùng chung.
   - Mở **EC2 Console** -> **Load Balancers**.
   - Chọn `fabric-gwlb` → Actions → Delete load balancer. Core NLB phải đã được controller xóa ở Tầng 1; nếu còn, điều tra ownership trước khi xóa tay.
   - Target Groups → xóa group GWLB đã ghi ở 05.02 sau khi LB biến mất; kiểm tra không còn target groups của lab.
4. **Hủy Máy Chủ Suricata EC2:**
   - Mở **EC2 Console** -> **Instances**.
   - Chọn cả 2 máy chủ: `fabric-suricata-1a` và `fabric-suricata-1b`.
   - Nhấp menu **Instance state** -> Chọn **Terminate instance** -> Xác nhận Terminate.

---

### Tầng 5: Xóa Transit Gateway & Các Attachments
1. **Xóa Transit Gateway VPC Attachments:**
   - Mở **VPC Console** -> **Transit gateway attachments**.
   - Chọn đồng thời 4 attachments:
     - `fabric-edge-tgw-attachment`
     - `fabric-core-tgw-attachment`
     - `fabric-insp-tgw-attachment`
     - `fabric-egress-tgw-attachment`
   - Nhấp **Actions** -> Chọn **Delete transit gateway attachment** -> Xác nhận xóa.
   - Chờ khoảng 1 - 2 phút cho đến khi tất cả attachments chuyển sang trạng thái `deleted`.
2. **Xóa Transit Gateway Route Tables:**
   - Mở **Transit gateway route tables**.
   - Chọn và xóa lần lượt: `fabric-tgw-edge-rt`, `fabric-tgw-core-rt`, `fabric-tgw-inspection-rt`, `fabric-tgw-egress-rt`.
3. **Xóa Transit Gateway:**
   - Mở **Transit gateways**.
   - Chọn `fabric-tgw` -> Nhấp **Actions** -> Chọn **Delete transit gateway** -> Xác nhận xóa.

---

### Tầng 6: Xóa Cổng NAT, Nhả Elastic IP & Xóa Toàn Bộ VPC
1. **Xóa NAT Gateways:**
   - Mở **VPC Console** -> **NAT gateways**.
   - Chọn `fabric-nat-gw-1a` và `fabric-nat-gw-1b`.
   - Nhấp **Actions** -> Chọn **Delete NAT gateway** -> Nhập `delete` để xác nhận.
   - Chờ trạng thái chuyển sang `deleted` (khoảng 2 phút).
2. **Nhả (Release) Elastic IP Addresses:**
   - Mở **Elastic IPs**.
   - Chọn tất cả Elastic IPs đã cấp phát cho NAT Gateways.
   - Nhấp **Actions** -> Chọn **Release Elastic IP addresses** -> Xác nhận.
3. **Tách & Xóa Internet Gateways:**
   - Mở **Internet gateways**.
   - Chọn `fabric-edge-igw` -> Nhấp **Actions** -> Chọn **Detach from VPC** -> Xác nhận -> Nhấp **Delete internet gateway**.
   - Lặp lại tương tự cho `fabric-egress-igw`.
4. **Xóa 4 Virtual Private Clouds (VPCs):**
   - Mở **Your VPCs**.
   - Chọn `fabric-edge-vpc` -> Nhấp **Actions** -> Chọn **Delete VPC** -> Nhập chuỗi `delete` -> Nhấp **Delete**.
   - Khi xóa VPC, AWS sẽ tự động xóa sạch các Subnets, Route Tables phụ, Network ACLs, và Security Groups mặc định đi kèm.
   - Lặp lại quy trình xóa cho:
     - `fabric-core-vpc`
     - `fabric-inspection-vpc`
     - `fabric-egress-vpc`
5. Xác nhận **4 VPC IDs của dự án** không còn; giữ nguyên mọi VPC ngoài dự án. Nếu DependencyViolation, xem ENI owner/service, xóa tài nguyên chủ quản; không force-delete ENI do AWS quản lý.
6. Hoàn tất inventory tồn dư ở 12.02: CloudWatch logs, snapshots/EBS, ECR, S3, Secrets Manager, IAM roles/policies, KMS, budgets. Chỉ xóa tài nguyên riêng của lab sau khi lưu evidence; KMS pending deletion và secrets recovery window phải ghi ngày kết thúc, không ghi CLEAN ngay.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra xác nhận toàn bộ các tài nguyên tính phí quan trọng đã sạch bóng qua AWS CLI:

```bash
# Kiểm tra VPC
aws ec2 describe-vpcs --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'Vpcs[*].VpcId' --output text

# Kiểm tra EKS Clusters
aws eks list-clusters --region ap-southeast-1 \
  --query 'clusters[?contains(@, `fabric`)]' --output text

# Kiểm tra Load Balancers
aws elbv2 describe-load-balancers --region ap-southeast-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `fabric`)].LoadBalancerName' --output text

# Kiểm tra NAT Gateways đang chạy
aws ec2 describe-nat-gateways --region ap-southeast-1 \
  --filter "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output text
```

*Kỳ vọng:* Toàn bộ các lệnh trên không trả về bất kỳ ID nào (danh sách trống).

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Quy trình Teardown là bước hủy vĩnh viễn môi trường. Nếu người dùng cần tái thiết lập lại toàn bộ hạ tầng dự án từ đầu:
- Không có rollback tức thì sau xóa. Khôi phục dữ liệu cần snapshot/backup đã giữ và khóa KMS còn dùng được. Dựng lại theo dependency trong `labs/README.md`; repo hiện chưa có Terraform/pipeline để giả định chạy tự động.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/05-reports/teardown-execution.log`: Toàn văn nhật ký các lệnh hủy tài nguyên theo 6 tầng.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Hoàn thành hủy toàn bộ 6 tầng theo đúng thứ tự phụ thuộc ngược.
- [ ] Không gặp bất kỳ lỗi `DependencyViolation` hoặc kẹt ENI nào trong suốt quá trình xóa.
- [ ] 2 cụm EKS, Aurora DB, Network Firewall, 2 NAT GWs và các Elastic IPs được xóa sạch.
- [ ] 4 VPC IDs dự án đã xóa; tài nguyên ngoài phạm vi giữ nguyên; phần retained/pending được ghi rõ tại 12.02.
