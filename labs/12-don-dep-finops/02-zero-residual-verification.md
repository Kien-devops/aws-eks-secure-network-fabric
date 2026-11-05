# 12.02 — Kiểm Kê Tồn Dư Tự Động & Chứng Minh Hóa Đơn Chi Phí Về Đúng $0.00

> **Mã bài lab:** `12.02`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã thực thi hoàn tất quy trình hủy tài nguyên 6 tầng theo thứ tự phụ thuộc ngược tại [Lab 12.01](01-reverse-dependency-teardown.md).
- Có quyền đọc (Read-only / Describe) toàn diện trên mọi dịch vụ AWS tại Region Singapore (`ap-southeast-1`).
- Đang mở phiên AWS Management Console.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các quyền IAM kiểm tra trạng thái tồn dư tài nguyên (Read-Only Audit):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeNatGateways",
        "ec2:DescribeAddresses",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeTransitGateways",
        "ec2:DescribeTransitGatewayVpcAttachments",
        "ec2:DescribeVpcEndpoints",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "eks:ListClusters",
        "rds:DescribeDBClusters",
        "elasticache:DescribeServerlessCaches",
        "elasticache:DescribeCacheClusters",
        "network-firewall:ListFirewalls",
        "wafv2:ListWebACLs"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Rủi Ro Chi Phí Ẩn (Orphaned Billable Resources):**
  - Trong điện toán đám mây AWS, có những tài nguyên tính phí âm thầm hàng giờ ngay cả khi không có lưu lượng, tiêu biểu:
    - **Elastic IP không gắn vào máy chủ:** Tính phí ~$0.005/giờ.
    - **NAT Gateway ở trạng thái available:** Tính phí ~$0.059/giờ.
    - **TGW VPC Attachment còn tồn tại:** Tính phí $0.05/giờ/attachment.
    - **Network Firewall Endpoint:** Tính phí $0.065/giờ/endpoint.
    - **EKS Cluster chưa xóa:** Tính phí $0.10/giờ/cluster.
  - Bài lab này cung cấp bằng chứng pháp lý và kỹ thuật đảm bảo **100% tài nguyên tính phí theo giờ đã biến mất**, đưa chi phí duy trì về chính xác **$0.00 USD/giờ**.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Rà Soát Dịch Vụ Amazon EC2 & Mạng
1. Mở **EC2 Console** tại Region Singapore (`ap-southeast-1`).
2. **Kiểm tra Instances:**
   - Menu **Instances** -> Kiểm tra bộ lọc `Instance state = running`.
   - Xác nhận: **Không có máy chủ ảo nào đang chạy** liên quan đến `fabric-`.
3. **Kiểm tra Elastic IPs:**
   - Menu **Elastic IPs** -> Xác nhận: Danh sách hoàn toàn rỗng (`No Elastic IPs found`).
4. **Kiểm tra Load Balancers:**
   - Menu **Load Balancers** -> Xác nhận: Không còn bất kỳ Load Balancer nào (`fabric-edge-alb`, `fabric-core-internal-nlb`, `fabric-gwlb`).
5. **Kiểm tra Network Interfaces (ENI):**
   - Menu **Network Interfaces** -> Lọc theo từ khóa `fabric-`.
   - Xác nhận: Không còn ENI nào bị kẹt.

---

### Bước 2: Rà Soát Dịch Vụ Amazon VPC
1. Mở **VPC Console** tại Singapore (`ap-southeast-1`).
2. **Kiểm tra Your VPCs:**
   - Xác nhận: Chỉ có duy nhất Default VPC của tài khoản. 4 VPCs dự án đã biến mất.
3. **Kiểm tra NAT Gateways:**
   - Menu **NAT gateways** -> Lọc trạng thái `available`.
   - Xác nhận: 0 NAT Gateways ở trạng thái available (chỉ có thể hiển thị trạng thái `deleted`).
4. **Kiểm tra Transit Gateways:**
   - Menu **Transit gateways** -> Xác nhận: 0 TGW ở trạng thái available.
5. **Kiểm tra Endpoints:**
   - Menu **Endpoints** -> Xác nhận: Không còn VPC Endpoints hoặc GWLB Endpoints nào.

---

### Bước 3: Rà Soát Amazon EKS, CSDL & Tường Lửa
1. **Amazon EKS:**
   - Mở **EKS Console** -> **Clusters** -> Xác nhận: Danh sách hiển thị `0 clusters`.
2. **Amazon RDS:**
   - Mở **RDS Console** -> **Databases** -> Xác nhận: Không còn cụm Aurora DB `fabric-core-db`.
3. **AWS Network Firewall:**
   - Mở **VPC Console** -> **AWS Network Firewall** -> **Firewalls** -> Xác nhận: `0 firewalls`.
4. **AWS WAF v2:**
   - Mở **WAF & Shield Console** -> **Web ACLs** -> Chọn Region Singapore -> Xác nhận: `0 Web ACLs`.

---

### Bước 4: Chạy Kịch Bản Kiểm Kê Tự Động 10 Hạng Mục (Zero-Residual Harvester)
Thực thi script quét tự động toàn bộ 10 phân hệ tài nguyên qua AWS CLI:

```bash
#!/bin/bash
set -euo pipefail

REGION="ap-southeast-1"
echo "======================================================================"
echo "    KIỂM TOÁN TỒN DƯ TÀI NGUYÊN (ZERO RESIDUAL VERIFICATION)         "
echo "    Region: $REGION | Thời gian: $(date -u +"%Y-%m-%dT%H:%M:%SZ")   "
echo "======================================================================"

TOTAL_LEAKS=0

check_service() {
  local name="$1"
  local count="$2"
  if [ "$count" -eq 0 ]; then
    printf "%-35s : %-15s [%s]\n" "$name" "0 tồn dư" "PASSED ✅"
  else
    printf "%-35s : %-15s [%s]\n" "$name" "$count TỒN DƯ!" "FAILED ❌"
    TOTAL_LEAKS=$((TOTAL_LEAKS + count))
  fi
}

# 1. EKS Clusters
EKS_COUNT=$(aws eks list-clusters --region "$REGION" --query 'length(clusters[?contains(@, `fabric`)])' --output text)
check_service "Amazon EKS Clusters" "$EKS_COUNT"

# 2. EC2 Instances (running)
EC2_COUNT=$(aws ec2 describe-instances --region "$REGION" --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" "Name=instance-state-name,Values=running,pending" --query 'length(Reservations[*].Instances[*])' --output text)
check_service "Running EC2 Instances" "$EC2_COUNT"

# 3. NAT Gateways (active)
NAT_COUNT=$(aws ec2 describe-nat-gateways --region "$REGION" --filter "Name=state,Values=available,pending" --query 'length(NatGateways[?contains(Tags[?Key==`Name`].Value | [0], `fabric`)])' --output text)
check_service "Active NAT Gateways" "$NAT_COUNT"

# 4. Elastic IP Addresses (unattached/allocated)
EIP_COUNT=$(aws ec2 describe-addresses --region "$REGION" --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'length(Addresses)' --output text)
check_service "Allocated Elastic IPs" "$EIP_COUNT"

# 5. Load Balancers (ALB/NLB/GWLB)
ELB_COUNT=$(aws elbv2 describe-load-balancers --region "$REGION" --query 'length(LoadBalancers[?contains(LoadBalancerName, `fabric`)])' --output text)
check_service "Load Balancers (ALB/NLB/GWLB)" "$ELB_COUNT"

# 6. Transit Gateways (active)
TGW_COUNT=$(aws ec2 describe-transit-gateways --region "$REGION" --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" "Name=state,Values=available,pending" --query 'length(TransitGateways)' --output text)
check_service "Active Transit Gateways" "$TGW_COUNT"

# 7. TGW VPC Attachments (active)
TGW_ATT_COUNT=$(aws ec2 describe-transit-gateway-vpc-attachments --region "$REGION" --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" "Name=state,Values=available,pending" --query 'length(TransitGatewayVpcAttachments)' --output text)
check_service "TGW VPC Attachments" "$TGW_ATT_COUNT"

# 8. AWS Network Firewall (active)
NFW_COUNT=$(aws network-firewall list-firewalls --region "$REGION" --query 'length(Firewalls[?contains(FirewallName, `fabric`)])' --output text)
check_service "AWS Network Firewalls" "$NFW_COUNT"

# 9. RDS Aurora DB Clusters
RDS_COUNT=$(aws rds describe-db-clusters --region "$REGION" --query 'length(DBClusters[?contains(DBClusterIdentifier, `fabric`)])' --output text)
check_service "Aurora PostgreSQL Clusters" "$RDS_COUNT"

# 10. Project VPCs
VPC_COUNT=$(aws ec2 describe-vpcs --region "$REGION" --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'length(Vpcs)' --output text)
check_service "Project VPCs" "$VPC_COUNT"

echo "======================================================================"
if [ "$TOTAL_LEAKS" -eq 0 ]; then
  echo ">> KẾT LUẬN: ĐẠT CHUẨN ZERO-RESIDUAL FINOPS (HOÀN TOÀN SẠCH TÀI NGUYÊN) <<"
  echo ">> CHI PHÍ DUY TRÌ HẠ TẦNG HIỆN TẠI: $0.00 USD / GIỜ                    <<"
else
  echo ">> CẢNH BÁO: PHÁT HIỆN $TOTAL_LEAKS TÀI NGUYÊN CHƯA HỦY! VUI LÒNG DỌN DẸP TIẾP! <<"
  exit 1
fi
```

---

### Bước 5: Tạo Chứng Nhận Sạch Tài Nguyên (Zero Residual Certificate)
Lưu kết quả kiểm toán vào tệp chứng nhận chính thức `evidence/05-reports/ZERO-RESIDUAL-CERTIFICATE.md`:

```markdown
# CHỨNG CHỈ KIỂM KÊ TỒN DƯ TÀI NGUYÊN (ZERO-RESIDUAL AUDIT CERTIFICATE)

- **Dự án:** `aws-eks-secure-network-fabric`
- **Region kiểm toán:** Singapore (`ap-southeast-1`)
- **Thời gian hoàn thành kiểm kê:** 2026-11-05T14:00:00Z
- **Người thực hiện:** Principal Cloud Architect & FinOps Specialist

## Kết Quả Kiểm Kê Chi Tiết 10 Hạng Mục

| Dịch Vụ AWS Được Kiểm Tra | Bộ Lọc Kiểm Tra | Số Lượng Tồn Dư | Trạng Thái FinOps |
|---|---|---|---|
| **Amazon EKS Clusters** | `fabric-*-cluster` | **0** | **CLEAN** ($0.00/h) ✅ |
| **Running EC2 Instances** | `fabric-suricata-*`, Worker nodes | **0** | **CLEAN** ($0.00/h) ✅ |
| **Active NAT Gateways** | `fabric-nat-gw-*` (`available`) | **0** | **CLEAN** ($0.00/h) ✅ |
| **Elastic IP Addresses** | Project tags | **0** | **CLEAN** ($0.00/h) ✅ |
| **Elastic Load Balancing** | ALB, Core NLB, GWLB | **0** | **CLEAN** ($0.00/h) ✅ |
| **AWS Transit Gateway** | `fabric-tgw` (`available`) | **0** | **CLEAN** ($0.00/h) ✅ |
| **TGW VPC Attachments** | `fabric-*-tgw-attachment` | **0** | **CLEAN** ($0.00/h) ✅ |
| **AWS Network Firewall** | `fabric-egress-nfw` | **0** | **CLEAN** ($0.00/h) ✅ |
| **Amazon Aurora PostgreSQL** | `fabric-core-db` | **0** | **CLEAN** ($0.00/h) ✅ |
| **Project VPCs** | 4 Project VPCs (`10.30/40/50/60`) | **0** | **CLEAN** ($0.00/h) ✅ |

## Tuyên Bố Xác Nhận FinOps (FinOps Affirmation)
Tôi xác nhận rằng toàn bộ các tài nguyên tính phí theo giờ và theo lưu lượng của Project 6 đã được dọn dẹp sạch sẽ 100%. Mọi dịch vụ tính cước đã trở về trạng thái ngừng hoạt động. Chi phí phát sinh trong tương lai của tài khoản liên quan đến dự án này là **chính xác $0.00 USD**.
```

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy lệnh kiểm tra tổng thể một dòng:
```bash
aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'length(Vpcs)'
aws eks list-clusters --region ap-southeast-1 --query 'length(clusters[?contains(@, `fabric`)])'
aws elbv2 describe-load-balancers --region ap-southeast-1 --query 'length(LoadBalancers[?contains(LoadBalancerName, `fabric`)])'
```

*Kỳ vọng:* Cả 3 lệnh đều trả về số `0`.

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Bài lab này là bước kiểm toán nghiệm thu cuối cùng (Audit Only), không thực hiện bất kỳ hành động xóa bỏ nào nữa.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/05-reports/ZERO-RESIDUAL-CERTIFICATE.md`: Báo cáo chứng nhận sạch tài nguyên 100%.
- `evidence/05-reports/zero-residual-audit-output.txt`: Raw log xuất từ script kiểm kê 10 hạng mục.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Script kiểm toán tự động 10 hạng mục đạt kết quả 10/10 PASSED.
- [ ] Số lượng EKS Clusters = 0.
- [ ] Số lượng EC2 running = 0.
- [ ] Số lượng NAT Gateways active = 0.
- [ ] Số lượng Load Balancers (ALB/NLB/GWLB) = 0.
- [ ] Số lượng TGW Attachments = 0.
- [ ] Số lượng Elastic IPs = 0.
- [ ] Chứng chỉ `ZERO-RESIDUAL-CERTIFICATE.md` được ký duyệt và lưu trữ thành công.
