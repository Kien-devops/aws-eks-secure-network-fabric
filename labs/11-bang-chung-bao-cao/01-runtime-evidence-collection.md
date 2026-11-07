# 11.01 — Thu Thập Bằng Chứng Kỹ Thuật Runtime Kèm Dấu Thời Gian (Timestamp)

> **Mã bài lab:** `11.01`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn tất toàn bộ các bài lab kỹ thuật từ Module 00 đến Module 10.
- Hạ tầng mạng, Dual EKS clusters, GWLB, Suricata, Network Firewall, và WAF đang ở trạng thái hoạt động hoặc vừa hoàn thành GameDay.
- Máy trạm quản trị đã cài đặt `aws-cli`, `kubectl`, `jq`, `curl`.
- Đang mở phiên AWS Management Console tại Singapore (`ap-southeast-1`).

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM read-only cần thiết để thu thập telemetry và cấu hình runtime:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeRouteTables",
        "ec2:DescribeTransitGateways",
        "ec2:DescribeTransitGatewayVpcAttachments",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:SearchTransitGatewayRoutes",
        "ec2:DescribeNetworkInsightsPaths",
        "ec2:DescribeNetworkInsightsAnalyses",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth",
        "network-firewall:DescribeFirewall",
        "network-firewall:DescribeFirewallPolicy",
        "network-firewall:DescribeRuleGroup",
        "wafv2:GetWebACL",
        "eks:DescribeCluster",
        "eks:DescribeNodegroup",
        "logs:FilterLogEvents",
        "logs:GetQueryResults"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Các lệnh Describe/List API và trích xuất log có chi phí $0.00 USD.
- **Nguyên tắc "Zero Fake Data":** Mọi file bằng chứng trong thư mục `evidence/` bắt buộc phải là output runtime thực tế trích xuất trực tiếp từ AWS API hoặc Kubernetes API, có gắn nhãn thời gian chuẩn quốc tế (**ISO 8601 UTC Timestamp**). Tuyệt đối nghiêm cấm tạo dữ liệu mẫu, mock data hoặc copy văn bản giả định.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo Cấu Trúc Thư Mục Bằng Chứng Chuẩn
Mở terminal máy trạm quản trị tại thư mục gốc của dự án `aws-eks-secure-network-fabric`:
```bash
mkdir -p evidence/01-network-topology \
         evidence/02-gwlb-inspection \
         evidence/03-egress-firewall \
         evidence/04-gameday \
         evidence/05-reports
```

---

### Bước 2: Thu Thập Bằng Chứng Hạ Tầng Mạng Trên VPC Console
1. Mở **VPC Console** tại Singapore (`ap-southeast-1`).
2. Mở menu **Your VPCs**:
   - Nhập bộ lọc `fabric-`: Xác nhận 4 VPC hiển thị đầy đủ (`fabric-edge-vpc`, `fabric-core-vpc`, `fabric-inspection-vpc`, `fabric-egress-vpc`).
   - Nhấp vào từng VPC -> Chọn tab **Resource map**: Chụp ảnh màn hình sơ đồ phân bổ subnet nếu cần.
3. Mở menu **Transit gateway route tables**:
   - Chọn bảng `fabric-tgw-edge-rt` -> Tab **Routes** -> Nhấp nút **Actions** -> Chọn **Export to CSV** hoặc copy bảng định tuyến.
   - Lặp lại cho `fabric-tgw-core-rt`, `fabric-tgw-inspection-rt`, `fabric-tgw-egress-rt`.
4. Mở menu **Reachability Analyzer**:
   - Chọn path `fabric-edge-to-core-nlb-path` -> Mở phiên phân tích mới nhất -> Xác nhận trạng thái `Reachable`.

---

### Bước 3: Thu Thập Bằng Chứng GWLB & Suricata Trên EC2 Console
1. Mở **EC2 Console** -> **Load Balancers**:
   - Chọn `fabric-gwlb` -> Xác nhận State: `Active`, Type: `gateway`.
2. Mở **Target Groups**:
   - Chọn `fabric-suricata-tg` -> Tab **Targets**:
   - Xác nhận cả 2 máy chủ `fabric-suricata-1a` và `fabric-suricata-1b` đều hiển thị trạng thái xanh `healthy`.
3. Mở **CloudWatch Logs**:
   - Vào Log Group `/aws/suricata/fabric-inspection-eve`.
   - Chọn stream log mới nhất -> Tải về 50 sự kiện gần nhất (Actions -> Export results to S3 hoặc Copy).

---

### Bước 4: Thu Thập Bằng Chứng AWS Network Firewall & WAF Console
1. Mở **VPC Console** -> **AWS Network Firewall** -> **Firewalls**:
   - Chọn `fabric-egress-nfw` -> Xác nhận Status: `Ready`.
   - Tab **Firewall details** -> Ghi lại Endpoint IDs tại 2 AZs.
2. Mở **WAF & Shield Console** -> **Web ACLs**:
   - Chọn `fabric-edge-web-acl` -> Tab **Rules**:
   - Xác nhận các Rules (`CommonRuleSet`, `KnownBadInputs`, `IpReputation`, `RateLimit`) đang ở trạng thái `Block`.

---

### Bước 5: Chạy Kịch Bản Thu Thập Tự Động Kèm Timestamp (Evidence Harvester)
Để đảm bảo tính nhất quán và tự động hóa 100%, thực thi script thu thập toàn diện qua AWS CLI:

```bash
#!/bin/bash
set -euo pipefail

REGION="ap-southeast-1"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=== Bắt đầu thu thập bằng chứng runtime [$TIMESTAMP] ==="

# 1. Thu thập VPC & Subnets
echo "[*] Thu thập sơ đồ VPCs & Subnets..."
aws ec2 describe-vpcs --region "$REGION" \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query "{Timestamp: \`$TIMESTAMP\`, Vpcs: Vpcs[*].{VpcId:VpcId,Cidr:CidrBlock,Name:Tags[?Key==\`Name\`].Value | [0]}}" \
  > evidence/01-network-topology/vpcs.json

aws ec2 describe-subnets --region "$REGION" \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query "{Timestamp: \`$TIMESTAMP\`, Subnets: Subnets[*].{SubnetId:SubnetId,VpcId:VpcId,Cidr:CidrBlock,Az:AvailabilityZone,Name:Tags[?Key==\`Name\`].Value | [0]}}" \
  > evidence/01-network-topology/subnets.json

# 2. Thu thập TGW Route Tables
echo "[*] Thu thập TGW Route Tables..."
aws ec2 describe-transit-gateway-route-tables --region "$REGION" \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query "{Timestamp: \`$TIMESTAMP\`, RouteTables: TransitGatewayRouteTables[*].{Id:TransitGatewayRouteTableId,Name:Tags[?Key==\`Name\`].Value | [0],State:State}}" \
  > evidence/01-network-topology/tgw-route-tables.json

# 3. Thu thập trạng thái GWLB Target Health
echo "[*] Thu thập GWLB Target Health..."
GWLB_TG_ARN=$(aws elbv2 describe-target-groups --region "$REGION" --names "fabric-suricata-tg" --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null || echo "")
if [ -n "$GWLB_TG_ARN" ]; then
  aws elbv2 describe-target-health --region "$REGION" --target-group-arn "$GWLB_TG_ARN" \
    --query "{Timestamp: \`$TIMESTAMP\`, Targets: TargetHealthDescriptions[*].{Id:Target.Id,Port:Target.Port,State:TargetHealth.State}}" \
    > evidence/02-gwlb-inspection/gwlb-target-health.json
fi

# 4. Thu thập Network Firewall Status
echo "[*] Thu thập AWS Network Firewall..."
aws network-firewall describe-firewall --region "$REGION" --firewall-name "fabric-egress-nfw" \
  --query "{Timestamp: \`$TIMESTAMP\`, Status: FirewallStatus.Status, Endpoints: FirewallStatus.SyncStates}" \
  > evidence/03-egress-firewall/nfw-status.json 2>/dev/null || true

# 5. Thu thập EKS Dual Clusters Status
echo "[*] Thu thập EKS Clusters..."
for cluster in fabric-edge-cluster fabric-core-cluster; do
  aws eks describe-cluster --region "$REGION" --name "$cluster" \
    --query "{Timestamp: \`$TIMESTAMP\`, Name: cluster.name, Version: cluster.version, Status: cluster.status, Endpoint: cluster.endpoint}" \
    > "evidence/01-network-topology/eks-$cluster.json" 2>/dev/null || true
done

echo "[+] Hoàn tất thu thập bằng chứng vào thư mục evidence/ lúc $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
```

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra số lượng và tính hợp lệ của các file bằng chứng vừa thu thập:

```bash
ls -la evidence/01-network-topology/
ls -la evidence/02-gwlb-inspection/
ls -la evidence/03-egress-firewall/

# Kiểm tra trường Timestamp trong file JSON
jq '.Timestamp' evidence/01-network-topology/vpcs.json
jq '.Timestamp' evidence/02-gwlb-inspection/gwlb-target-health.json
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Do hoạt động thu thập bằng chứng là thao tác chỉ đọc (Read-only), không có rủi ro thay đổi trạng thái hạ tầng. Nếu muốn làm sạch thư mục bằng chứng để thu thập lại từ đầu:
```bash
rm -rf evidence/*
mkdir -p evidence/01-network-topology evidence/02-gwlb-inspection evidence/03-egress-firewall evidence/04-gameday evidence/05-reports
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/01-network-topology/vpcs.json`
- `evidence/01-network-topology/subnets.json`
- `evidence/01-network-topology/tgw-route-tables.json`
- `evidence/02-gwlb-inspection/gwlb-target-health.json`
- `evidence/03-egress-firewall/nfw-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Toàn bộ các file trong thư mục `evidence/` chứa cấu trúc JSON hợp lệ.
- [x] 100% file có trường `Timestamp` định dạng chuẩn ISO 8601 UTC.
- [x] Dữ liệu phản ánh chính xác trạng thái runtime của hạ tầng tại `ap-southeast-1`.
- [x] Tuyệt đối không có trường dữ liệu giả lập (Zero Fake Data).
