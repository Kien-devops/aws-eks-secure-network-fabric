#!/usr/bin/env python3
"""Refactor Module 06 files: Centralized Egress Firewall, Return Path fix via Firewall Endpoint, Egress Appliance Mode."""

from pathlib import Path

BASE = Path("E:/repo/project6/aws-eks-secure-network-fabric/labs/06-centralized-egress-firewall")

# 01-nat-gateways-per-az.md
(BASE / "01-nat-gateways-per-az.md").write_text("""# 06.01 — Khởi Tạo NAT Gateways & Elastic IPs Đa AZ Tại Public Subnets

> **Mã bài lab:** `06.01`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** ~$0.045 USD / giờ / NAT Gateway (~$0.09 USD / giờ cho 2 NAT Gateways)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `fabric-egress-public-1a`, `fabric-egress-public-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành hạ tầng Centralized Egress VPC tại [Module 02](../02-ha-tang-mang-co-ban/README.md).
- Internet Gateway `fabric-egress-igw` đã được gắn vào `fabric-egress-vpc`.

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
        "ec2:AllocateAddress",
        "ec2:CreateNatGateway",
        "ec2:DescribeNatGateways",
        "ec2:ReleaseAddress",
        "ec2:DeleteNatGateway"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** 2 NAT Gateways tiêu tốn ~$2.16 USD/ngày cố định cộng với phí xử lý dữ liệu ($0.045/GB).
- **Cảnh báo FinOps:** NAT Gateway là một trong những thành phần tính phí theo giờ đáng kể nhất. Khi không thực hiện kiểm thử Egress hoặc GameDay, cần lập kế hoạch dọn dẹp hoặc tắt theo Module 12.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Cấp Phát 2 Elastic IPs (EIP)
1. Truy cập **VPC Console** -> **Elastic IP addresses** -> **Allocate Elastic IP address**.
2. Tag: `Name=fabric-nat-eip-1a`, `Project=aws-eks-secure-network-fabric`.
3. Nhấp **Allocate**. Lặp lại cấp phát EIP thứ hai: `fabric-nat-eip-1b`.

### Bước 2: Tạo NAT Gateway Tại AZ-a
1. Truy cập **VPC Console** -> **NAT gateways** -> **Create NAT gateway**:
   - Name: `fabric-nat-gw-1a`
   - Subnet: Chọn `fabric-egress-public-1a` (`10.80.10.0/24`)
   - Connectivity type: `Public`
   - Elastic IP allocation ID: Chọn `fabric-nat-eip-1a`
2. Nhấp **Create NAT gateway**.

### Bước 3: Tạo NAT Gateway Tại AZ-b
Thực hiện tương tự Bước 2 cho AZ-b:
- Name: `fabric-nat-gw-1b`
- Subnet: Chọn `fabric-egress-public-1b` (`10.80.11.0/24`)
- Elastic IP allocation ID: Chọn `fabric-nat-eip-1b`

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái sẵn sàng của 2 NAT Gateways:
```bash
aws ec2 describe-nat-gateways --region ap-southeast-1 \
  --filter "Name=tag:Project,Values=aws-eks-secure-network-fabric" "Name=state,Values=available" \
  --query 'NatGateways[*].{Name:Tags[?Key==`Name`].Value | [0],Id:NatGatewayId,State:State,Subnet:SubnetId,PublicIP:NatGatewayAddresses[0].PublicIp}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa 2 NAT Gateways và giải phóng Elastic IPs:
```bash
for nat_id in $(aws ec2 describe-nat-gateways --region ap-southeast-1 --filter "Name=tag:Project,Values=aws-eks-secure-network-fabric" --query 'NatGateways[*].NatGatewayId' --output text); do
  aws ec2 delete-nat-gateway --region ap-southeast-1 --nat-gateway-id $nat_id
done
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/06-firewall/01-nat-gateways-active.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 2 NAT Gateways (`fabric-nat-gw-1a` và `fabric-nat-gw-1b`) đều ở trạng thái `available`.
- [ ] Mỗi NAT Gateway được đặt trong đúng Public Subnet của AZ tương ứng.
""", encoding="utf-8")

# 02-network-firewall-rule-groups.md
(BASE / "02-network-firewall-rule-groups.md").write_text("""# 06.02 — Khởi Tạo Rule Groups Cho AWS Network Firewall (Domain Filtering)

> **Mã bài lab:** `06.02`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** $0.00 USD (Rule groups tính kèm theo chi phí Firewall Endpoint)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [06.01](01-nat-gateways-per-az.md).
- Nắm rõ danh sách các domain phục vụ hoạt động của cụm EKS (Allowlist: `.quay.io`, `.github.com`, `.docker.io`, `.amazonaws.com`).

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
        "network-firewall:CreateRuleGroup",
        "network-firewall:CreateFirewallPolicy",
        "network-firewall:DescribeRuleGroup",
        "network-firewall:DescribeFirewallPolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Tạo Rule Group độc lập không tính phí.
- **Cảnh báo Chặn Nhầm Dịch Vụ Cốt Lõi:** Stateful Domain Rule Group nếu không đưa domain của AWS ECR (`*.dkr.ecr.ap-southeast-1.amazonaws.com`) và AWS STS vào danh mục cho phép sẽ khiến các Pod không thể kéo image từ bên ngoài.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo Stateful Rule Group Cho Domain Filtering (Allowlist)
1. Truy cập **VPC Console** -> **Network Firewall rule groups** -> **Create rule group**.
2. **Rule group details:**
   - Name: `fabric-egress-domain-allowlist-rg`
   - Capacity: `100`
   - Type: **Stateful rule group**
3. **Stateful rule group options:**
   - Chọn **Domain list**
   - Actions: `Allow`
   - Targets (FQDN domain list):
     - `.amazonaws.com`
     - `.docker.io`
     - `.quay.io`
     - `.github.com`
     - `.registry-1.docker.io`
   - Target types: `HTTP_HOST` và `TLS_SNI`
4. Nhấp **Create rule group**.

### Bước 2: Tạo Stateful Rule Group Drop Malicious Traffic
1. Tạo Stateful rule group dạng **Suricata compatible rules**:
   - Name: `fabric-egress-malicious-drop-rg`
   - Capacity: `100`
2. Nhập quy tắc Suricata ngăn chặn các kết nối tới port không an toàn hoặc payload nghi vấn:
   ```text
   drop tcp $HOME_NET any -> $EXTERNAL_NET [21,23,25] (msg:"FABRIC DROP Outbound Insecure Port"; sid:1000001; rev:1;)
   ```

### Bước 3: Tạo Firewall Policy
1. Truy cập **Firewall policies** -> **Create firewall policy**:
   - Name: `fabric-egress-fw-policy`
2. **Stateless default actions:**
   - Actions for matching packets: `Forward to stateful rule groups`.
3. **Stateful rule groups:**
   - Thêm 2 rule groups vừa tạo: `fabric-egress-domain-allowlist-rg` và `fabric-egress-malicious-drop-rg`.
4. Nhấp **Create firewall policy**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái Firewall Policy:
```bash
aws network-firewall describe-firewall-policy --region ap-southeast-1 \
  --firewall-policy-name fabric-egress-fw-policy \
  --query 'FirewallPolicyResponse.{Name:FirewallPolicyName,Status:FirewallPolicyStatus,StatefulGroups:FirewallPolicy.StatefulRuleGroupReferences[*].ResourceArn}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa Firewall Policy và Rule Groups:
```bash
aws network-firewall delete-firewall-policy --region ap-southeast-1 --firewall-policy-name fabric-egress-fw-policy
aws network-firewall delete-rule-group --region ap-southeast-1 --rule-group-name fabric-egress-domain-allowlist-rg --type STATEFUL
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/06-firewall/02-firewall-policy.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Firewall Policy `fabric-egress-fw-policy` ở trạng thái `ACTIVE`.
- [ ] Stateful Domain Rule Group cấu hình đúng hành vi `Allow` cho danh sách FQDN.
""", encoding="utf-8")

# 03-network-firewall-deployment.md
(BASE / "03-network-firewall-deployment.md").write_text("""# 06.03 — Triển Khai AWS Network Firewall Tại Egress VPC & Bật Appliance Mode

> **Mã bài lab:** `06.03`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** ~$0.395 USD / giờ / endpoint (~$0.79 USD / giờ cho 2 AZ endpoints)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `fabric-egress-fw-1a`, `fabric-egress-fw-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [06.01](01-nat-gateways-per-az.md) và [06.02](02-network-firewall-rule-groups.md).
- Subnets `fabric-egress-fw-1a` (`10.80.1.0/28`) và `fabric-egress-fw-1b` (`10.80.1.16/28`) sẵn sàng.

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
        "network-firewall:CreateFirewall",
        "network-firewall:DescribeFirewall",
        "network-firewall:UpdateLoggingConfiguration",
        "ec2:ModifyTransitGatewayVpcAttachment"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** AWS Network Firewall tính phí ~$0.395 USD/giờ cho mỗi endpoint ở Singapore (~$18.96 USD/ngày cho 2 AZs). Đây là thành phần chi phí lớn nhất của lab.
- **Cảnh báo TGW Egress Attachment Appliance Mode:** Bắt buộc phải xác nhận cờ `ApplianceModeSupport = enable` trên `fabric-egress-tgw-attachment`. Nếu không, luồng ra và luồng vào của một phiên kết nối sẽ bị phân tán sang 2 firewall endpoint khác nhau, gây ra tình trạng TCP reset.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo AWS Network Firewall
1. Truy cập **VPC Console** -> **Network Firewall** -> **Firewalls** -> Nhấp **Create firewall**.
2. **Firewall details:**
   - Name: `fabric-egress-nfw`
   - Firewall policy: Chọn `fabric-egress-fw-policy`
   - VPC: Chọn `fabric-egress-vpc`
3. **Subnet mappings:**
   - `ap-southeast-1a`: Chọn subnet `fabric-egress-fw-1a`
   - `ap-southeast-1b`: Chọn subnet `fabric-egress-fw-1b`
4. Nhấp **Create firewall**. Quá trình provisioning mất khoảng 5-8 phút.

### Bước 2: Cấu Hình Ghi Nhật Ký (Alert & Flow Logging)
1. Tại chi tiết firewall `fabric-egress-nfw`, cuộn xuống tab **Logging**.
2. Bật ghi log cho 2 loại:
   - **Alert log:** Gửi về CloudWatch Log Group `/aws/nfw/fabric-egress-alerts`.
   - **Flow log:** Gửi về CloudWatch Log Group `/aws/nfw/fabric-egress-flows`.

### Bước 3: Xác Thực Cờ Appliance Mode Trên Egress TGW Attachment
Kiểm tra Attachment của Egress VPC trên Transit Gateway:
```bash
aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-egress-tgw-attachment" \
  --query 'TransitGatewayVpcAttachments[0].Options.ApplianceModeSupport' --output text
```
*Nếu hiển thị `disable`, lập tức chỉnh sửa sang `enable`:*
```bash
att_id=$(aws ec2 describe-transit-gateway-vpc-attachments --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-egress-tgw-attachment" --query 'TransitGatewayVpcAttachments[0].TransitGatewayAttachmentId' --output text)
aws ec2 modify-transit-gateway-vpc-attachment --region ap-southeast-1 --transit-gateway-attachment-id $att_id --options ApplianceModeSupport=enable
```

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái Firewall và các Endpoints ID:
```bash
aws network-firewall describe-firewall --region ap-southeast-1 \
  --firewall-name fabric-egress-nfw \
  --query 'FirewallStatus.{Status:Status,SyncStates:SyncStates}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa AWS Network Firewall:
```bash
aws network-firewall delete-firewall --region ap-southeast-1 --firewall-name fabric-egress-nfw
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/06-firewall/03-firewall-endpoints.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] AWS Network Firewall `fabric-egress-nfw` đạt trạng thái `READY`.
- [ ] 2 Firewall Endpoints được cấp phát thành công tại 2 AZs `ap-southeast-1a` và `ap-southeast-1b`.
- [ ] Cờ `ApplianceModeSupport` của `fabric-egress-tgw-attachment` hiển thị `enable`.
""", encoding="utf-8")

# 04-egress-routing-and-domain-filtering-test.md
(BASE / "04-egress-routing-and-domain-filtering-test.md").write_text("""# 06.04 — Cấu Hình Bảng Định Tuyến Egress Return Path & Kiểm Thử Lọc Tên Miền

> **Mã bài lab:** `06.04`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [06.01](01-nat-gateways-per-az.md), [06.02](02-network-firewall-rule-groups.md), [06.03](03-network-firewall-deployment.md).
- Lấy được 2 Endpoint IDs (`vpce-...`) của AWS Network Firewall tại AZ-a và AZ-b.

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
        "ec2:CreateRoute",
        "ec2:ReplaceRoute",
        "ec2:DescribeRouteTables"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **CẢNH BÁO QUAN TRỌNG NHẤT VỀ RETURN PATH (Tránh Bypass Tường Lửa):**
  Lưu lượng phản hồi từ Internet về NAT Gateway sẽ mang IP đích là CIDR của Edge (`10.40.0.0/16`) hoặc Core (`10.50.0.0/16`). Bảng định tuyến của **Public NAT Subnet BẮT BUỘC PHẢI TRỎ `10.40.0.0/16` và `10.50.0.0/16` VỀ NETWORK FIREWALL ENDPOINT (`vpce-...`) TRONG CÙNG AZ**. 
  **TUYỆT ĐỐI KHÔNG ĐƯỢC TRỎ TRỰC TIẾP VỀ TGW!** Nếu trỏ trực tiếp về TGW, lưu lượng chiều về sẽ bypass hoàn toàn tường lửa, khiến Network Firewall ngắt kết nối do không thấy gói tin ACK trở về.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Trích Xuất 2 VPC Endpoint IDs Của Firewall
Chạy CLI để lấy chính xác ID của 2 endpoint:
```bash
vpce_1a=$(aws network-firewall describe-firewall --region ap-southeast-1 --firewall-name fabric-egress-nfw --query 'FirewallStatus.SyncStates."ap-southeast-1a".Attachment.EndpointId' --output text)
vpce_1b=$(aws network-firewall describe-firewall --region ap-southeast-1 --firewall-name fabric-egress-nfw --query 'FirewallStatus.SyncStates."ap-southeast-1b".Attachment.EndpointId' --output text)
```

### Bước 2: Cấu Hình Định Tuyến Chiều Đi (Forward Path)
1. **TGW Subnet RT AZ-a (`fabric-egress-tgw-rt-1a`):**
   - Route `0.0.0.0/0` -> trỏ tới `vpce_1a`
2. **TGW Subnet RT AZ-b (`fabric-egress-tgw-rt-1b`):**
   - Route `0.0.0.0/0` -> trỏ tới `vpce_1b`
3. **Firewall Subnet RT AZ-a (`fabric-egress-fw-rt-1a`):**
   - Route `0.0.0.0/0` -> trỏ tới NAT Gateway `fabric-nat-gw-1a`
4. **Firewall Subnet RT AZ-b (`fabric-egress-fw-rt-1b`):**
   - Route `0.0.0.0/0` -> trỏ tới NAT Gateway `fabric-nat-gw-1b`

### Bước 3: Cấu Hình Định Tuyến Chiều Về (Return Path Bắt Buộc)
1. **Public NAT Subnet RT AZ-a (`fabric-egress-public-rt-1a`):**
   - Route `0.0.0.0/0` -> Internet Gateway (`fabric-egress-igw`)
   - **Route `10.40.0.0/16` -> trỏ tới `vpce_1a`** (Bảo toàn đi qua Firewall)
   - **Route `10.50.0.0/16` -> trỏ tới `vpce_1a`** (Bảo toàn đi qua Firewall)
2. **Public NAT Subnet RT AZ-b (`fabric-egress-public-rt-1b`):**
   - Route `0.0.0.0/0` -> Internet Gateway (`fabric-egress-igw`)
   - **Route `10.40.0.0/16` -> trỏ tới `vpce_1b`**
   - **Route `10.50.0.0/16` -> trỏ tới `vpce_1b`

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

### 1. Kiểm Thử Truy Cập Tên Miền Trong Allowlist (Kỳ vọng: Thành công)
Từ một Pod trong Core EKS (`fabric-core-eks`), chạy lệnh kiểm tra truy cập domain cho phép:
```bash
# Kiểm tra truy cập domain trong danh mục
kubectl run egress-test --rm -it --image=curlimages/curl -n fabric-apps -- curl -Iv https://github.com --connect-timeout 5
```

### 2. Kiểm Thử Truy Cập Tên Miền Bị Chặn (Kỳ vọng: Connection timed out / Dropped)
Chạy lệnh kiểm tra truy cập domain ngoài allowlist:
```bash
kubectl run egress-block-test --rm -it --image=curlimages/curl -n fabric-apps -- curl -Iv https://example.com --connect-timeout 5 || echo "Egress Firewall DROP confirmed!"
```

### 3. Kiểm Tra Log Drop/Alert Trên CloudWatch Logs
```bash
aws logs filter-log-events --region ap-southeast-1 \
  --log-group-name /aws/nfw/fabric-egress-alerts \
  --query 'events[*].message' --output text
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp phát sinh lỗi định tuyến khiến không truy cập được Internet, xóa các route return path và kiểm tra lại liên kết Endpoint.

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/06-firewall/04-egress-domain-filter-test.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Return path tại Public NAT Subnet trỏ chính xác về Firewall Endpoint (`vpce-*`).
- [ ] Truy cập tới `github.com` và `quay.io` thành công với mã phản hồi HTTP hợp lệ.
- [ ] Truy cập tới domain ngoài allowlist bị ngắt kết nối và ghi nhận log trong CloudWatch Logs.
""", encoding="utf-8")

# Update README.md for Module 06
(BASE / "README.md").write_text("""# Module 06: Centralized Egress Firewall (AWS Network Firewall & NAT)

Module này hướng dẫn triển khai kiến trúc tường lửa ra Internet tập trung (Centralized Egress) sử dụng AWS Network Firewall kết hợp 2 NAT Gateways đa AZ, cấu hình Domain Allowlist Stateful Rules, kích hoạt TGW Appliance Mode và khắc phục triệt để lỗi Return Path để bảo toàn tính toàn vẹn của tường lửa.

## Danh Sách Bài Lab

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **06.01** | **NAT Gateways & Elastic IPs:** 2 NAT Gateways tại Public Subnets AZ-a và AZ-b. | `DRAFT` | [01-nat-gateways-per-az.md](01-nat-gateways-per-az.md) |
| **06.02** | **Network Firewall Rule Groups:** Stateful Domain Allowlist và Suricata Drop rules. | `DRAFT` | [02-network-firewall-rule-groups.md](02-network-firewall-rule-groups.md) |
| **06.03** | **Network Firewall Deployment:** Triển khai NFW Endpoints, bật Egress Appliance Mode. | `DRAFT` | [03-network-firewall-deployment.md](03-network-firewall-deployment.md) |
| **06.04** | **Egress Return Path & Domain Test:** Cấu hình chuẩn Return Path và xác minh Allow/Block. | `DRAFT` | [04-egress-routing-and-domain-filtering-test.md](04-egress-routing-and-domain-filtering-test.md) |
""", encoding="utf-8")

print("Module 06 rewritten successfully.")
