# 12.02 — Kiểm Kê Tồn Dư Và Đối Soát Chi Phí Sau Cleanup

> **Mã bài lab:** `12.02`  
> **Trạng thái:** `DRAFT`  
> **Thời gian dự kiến:** 45 phút, đối soát billing bổ sung khi dữ liệu cập nhật  
> **Chi phí ước tính:** phụ thuộc tài nguyên retained và truy vấn billing/logs  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)

## 1. Tiền đề (Prerequisites)

- Hoàn tất [12.01](01-reverse-dependency-teardown.md), lưu inventory IDs, tags, tài nguyên dùng chung, snapshots và dữ liệu cần giữ.
- Có quyền đọc các dịch vụ cần kiểm kê, quyền Cost Explorer và Billing phù hợp. AccessDenied là **chưa kiểm tra được**, không phải số lượng 0.
- Đây là kiểm tra chỉ đọc. Không xóa tài nguyên ngoài dự án để đạt số 0 toàn tài khoản.

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Role audit cần EC2/VPC Describe, ELB Describe, EKS List/Describe, RDS Describe (instances/clusters/snapshots), ElastiCache Describe (replication groups/snapshots), Network Firewall List/Describe, WAF List/Get, SQS List/GetQueueAttributes, Route 53 List/Get, Logs Describe, ECR Describe/List, S3 List/GetBucketLocation, Secrets Manager List/Describe, KMS List/Describe, IAM List/Get và `ce:GetCostAndUsage`. Giới hạn resource/account khi API hỗ trợ; SCP, permission boundary và billing access vẫn áp dụng. Không cấp quyền xóa cho role kiểm kê.

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- Xóa VPC không xóa snapshots, EBS retained, logs, ECR images, S3, Secrets Manager hoặc khóa KMS. EC2 stopped vẫn có thể tốn EBS; EKS node count 0 vẫn tốn control plane.
- NAT, Network Firewall, interface endpoints, public IPv4, TGW attachments và hosted zones có thể tiếp tục tính phí khi không có traffic. Tra giá Singapore hiện hành trên trang pricing từng dịch vụ; không dùng đơn giá cố định để kết luận hóa đơn.
- Billing có độ trễ; chi phí tháng đã phát sinh không trở về $0 sau cleanup. Không chứng nhận chi phí tương lai chính xác $0 từ một lần kiểm kê.

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Chốt Phạm Vi Kiểm Kê

1. Đăng nhập Console → kiểm tra account/role → chọn Singapore.
2. Mở inventory trước cleanup; lập bảng gồm service, resource ID, region, ownership, trạng thái mong đợi, trạng thái thực tế, timestamp và evidence.
3. Dùng `Project=aws-eks-secure-network-fabric` để tìm ứng viên, đối chiếu IDs. Tag thiếu hoặc tên trùng phải kiểm tra ownership; tag-only không đủ chứng minh sạch.
4. Với dịch vụ global như IAM/Route 53, kiểm tra đúng resource của dự án; không giới hạn bằng bộ lọc region rồi bỏ sót.

### Bước 2: EC2, Storage Và Load Balancers

1. EC2 → Instances → bỏ bộ lọc chỉ running → kiểm tra mọi instance ID của lab. `terminated` chấp nhận; stopped/stopping vẫn cần xử lý hoặc ghi retained.
2. EC2 → Volumes → lọc VPC/node/instance inventory và tags; kiểm tra volume detached, reclaim Retain, volume từ appliance. Ghi size, encryption key, lý do giữ và ngày xử lý.
3. EC2 → Snapshots → Owned by me → tìm snapshots dự án; kiểm tra cả AMIs tự tạo và snapshots gắn AMI. Snapshot giữ lại phải có owner/expiry/cost estimate.
4. Elastic IPs → đối chiếu allocation IDs NAT/appliance; không còn public IPv4 allocations của lab ngoài phần được duyệt giữ.
5. Load Balancers/Target Groups → đối chiếu ALB, NLB, GWLB và groups controller tạo. Không còn LB không đồng nghĩa target groups đã sạch.
6. Network Interfaces → lọc **từng VPC ID** và subnet ID trước cleanup, xem Description/Requester managed/owner. ENI chưa xóa: ghi service chủ quản và trạng thái; không tự detach/delete managed ENI.

### Bước 3: VPC Và Các Dịch Vụ Mạng

1. VPC → Your VPCs → tìm 4 IDs Edge/Core/Inspection/Egress. Không yêu cầu toàn tài khoản chỉ còn Default VPC.
2. NAT gateways → kiểm tra IDs inventory ở mọi trạng thái; pending/deleting chưa phải hoàn tất. Chờ deleted và kiểm tra EIPs riêng.
3. Transit gateways, attachments, route tables → xác nhận đúng IDs đã xóa, không còn pending/deleting hoặc attachments dùng chung bị xóa nhầm.
4. Endpoints → kiểm tra interface/gateway/GWLB endpoints theo VPC IDs; Endpoint services → kiểm tra service GWLB đã xóa.
5. Network Firewall → Firewalls, policies, rule groups → đối chiếu inventory. Xác nhận firewall endpoints đã được dịch vụ giải phóng.
6. WAF → Regional Singapore → kiểm tra Web ACL của lab; ACM → certificate của app → kiểm tra association/ownership trước kết luận.
7. Route 53 → Hosted zones → kiểm tra private zone `fabric.internal`, public app records, resolver endpoints/rules nếu từng tạo. Hosted zone dùng chung giữ nguyên và ghi phạm vi ngoại lệ.

### Bước 4: EKS, Database, Cache Và Messaging

1. EKS → Clusters → không còn `fabric-edge-eks`, `fabric-core-eks`; đối chiếu node instances/ASGs/volumes ở Bước 2, không chỉ nhìn cluster count.
2. RDS → Databases → kiểm tra cả Aurora cluster và writer/readers. Snapshots/Automated backups → ghi mọi bản sao còn giữ, ngày hết hạn và khóa KMS cần giữ để restore.
3. ElastiCache → Redis OSS caches → kiểm tra replication group `fabric-core-redis`; Backups → đối chiếu snapshots. Không chỉ kiểm tra Serverless caches.
4. SQS → kiểm tra `fabric-order-events` và DLQ theo queue URLs inventory; không còn message dữ liệu cần lưu bị bỏ sót.

### Bước 5: Tài Nguyên Ngoài VPC Và Quyền Truy Cập

1. CloudWatch → Log groups → kiểm tra VPC/TGW/NFW/EVE/EKS/WAF groups, retained bytes và retention. Lưu evidence trước khi quyết định xóa; giữ logs đồng nghĩa còn phí storage có thể phát sinh.
2. ECR → Private repositories → kiểm tra images, signatures, attestations của 5 services; S3 → buckets dự án → kiểm tra versions, delete markers, multipart uploads và replication nếu có. Không xóa bucket evidence khi chưa có bản lưu được duyệt.
3. Secrets Manager → Secrets → bật hiển thị scheduled deletion; ghi tên, ngày xóa và recovery window. Không in secret value vào evidence.
4. KMS → Customer managed keys → ghi key IDs và state. Pending deletion chưa là deleted; không lên lịch xóa khóa còn dùng cho backup/evidence hoặc ngoài dự án.
5. IAM → Roles/Policies/Identity providers → đối chiếu Pod Identity roles, EC2 profile, CI OIDC roles/provider. Ghi dependencies; chỉ xử lý tài nguyên riêng lab theo 12.01, không xóa provider dùng chung.
6. Billing → Budgets → kiểm tra budget/action/notification riêng của lab; giữ budget dùng chung của tài khoản. Kiểm tra dashboard/alarm/rules đã tạo nếu có.

### Bước 6: Đối Soát Billing

1. Billing and Cost Management → Cost Explorer → chọn khoảng ngày gồm trước và sau cleanup → Granularity **Daily** → Group by Service/Region.
2. Nếu cost allocation tag dự án đã được kích hoạt, lọc đúng tag; tag không hồi tố đầy đủ và tài nguyên thiếu tag cần đối chiếu usage/resource IDs. Không quy toàn bộ hóa đơn account cho lab.
3. Ghi timestamp cleanup, timestamp báo cáo, currency, estimated/final và ngày usage mới nhất. So sánh usage sau cleanup khi dữ liệu đã cập nhật; chưa có dữ liệu thì ghi **PENDING_BILLING**.
4. Phí storage retained, snapshots hoặc KMS phải được giải thích riêng. Khi còn phí chưa rõ, mở Bills → Service → Region → Usage type; truy ngược inventory, không tự xóa tài nguyên khác để giảm số liệu.

### Bước 7: Lưu Báo Cáo Thật

Lưu `evidence/05-reports/ZERO-RESIDUAL-CERTIFICATE.md` với timestamp thật, người kiểm tra, account đã che, phạm vi, raw outputs và bảng sau. Tên file giữ để tương thích; đây là báo cáo giới hạn phạm vi, không phải bảo đảm hóa đơn bằng 0.

| Nhóm | IDs đã kiểm tra | Kết quả thực tế | Retained/pending và owner | Evidence |
|---|---|---|---|---|
| Compute/EKS/LB | Điền từ inventory | NOT_CHECKED trước khi chạy | Điền nếu có | Đường dẫn log |
| VPC/TGW/NAT/endpoints/NFW | Điền từ inventory | NOT_CHECKED | Điền nếu có | Đường dẫn log |
| Database/cache/queues | Điền từ inventory | NOT_CHECKED | Backup/expiry | Đường dẫn log |
| Storage/logs/ECR/S3 | Điền từ inventory | NOT_CHECKED | Bytes/retention/cost | Đường dẫn log |
| DNS/IAM/secrets/KMS/budgets | Điền từ inventory | NOT_CHECKED | Recovery/deletion dates | Đường dẫn log |
| Billing sau cleanup | Khoảng usage đã cập nhật | PENDING_BILLING | Phí chưa giải thích | Export Cost Explorer |

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Các lệnh chỉ đọc sau hỗ trợ Console, không thay thế toàn bộ checklist. Không tạo script kiểm kê hoặc tự chuyển PASS từ ba số đếm:

```bash
aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'Vpcs[].VpcId'
aws eks list-clusters --region ap-southeast-1 --query 'clusters[?starts_with(@, `fabric-`)]'
aws elasticache describe-replication-groups --region ap-southeast-1 --query 'ReplicationGroups[].{ID:ReplicationGroupId,State:Status}'
aws rds describe-db-instances --region ap-southeast-1 --query 'DBInstances[].{ID:DBInstanceIdentifier,Cluster:DBClusterIdentifier,State:DBInstanceStatus}'
```

Chỉ lưu các rows của dự án; lỗi quyền/API hoặc tag thiếu phải ghi rõ. Không coi danh sách toàn tài khoản là danh sách được phép xóa.

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Audit không thay đổi tài nguyên. Tồn dư phát hiện được chuyển về 12.01 theo ownership và quyết định giữ/xóa; pending hoặc AccessDenied giữ trạng thái chưa hoàn tất.

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/05-reports/ZERO-RESIDUAL-CERTIFICATE.md`: phạm vi, kết quả thật, ngoại lệ và billing window.
- `evidence/05-reports/zero-residual-audit-output.txt`: raw read-only outputs đã che thông tin nhạy cảm.
- `evidence/05-reports/cleanup-billing-export.csv`: export chi phí với timestamp và filters.

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Mọi resource ID của dự án đã đối chiếu; không suy luận sạch từ tag-only hoặc toàn account count.
- [ ] Compute/network đã xóa hoặc ghi ngoại lệ có owner/expiry; không bỏ qua deleting/AccessDenied.
- [ ] Storage/backups/logs/ECR/S3/secrets/KMS/DNS/IAM đã kiểm kê, retained costs được ghi rõ.
- [ ] Evidence có timestamp thật; billing ghi khoảng usage đã cập nhật hoặc PENDING_BILLING.
- [ ] Tài nguyên ngoài dự án giữ nguyên; không cam kết chi phí tài khoản chính xác $0.
