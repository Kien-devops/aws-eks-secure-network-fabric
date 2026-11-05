#!/usr/bin/env python3
"""Refactor Module 05 files: Accurate GWLB GENEVE TLV model, 2 Zonal GWLBe endpoints, East-West route cutover & symmetric verification."""

from pathlib import Path

BASE = Path("E:/repo/project6/aws-eks-secure-network-fabric/labs/05-gwlb-suricata-ids-ips")

# 01-suricata-ec2-instances.md
(BASE / "01-suricata-ec2-instances.md").write_text("""# 05.01 — Khởi Tạo 2 Suricata Appliances EC2 & Cấu Hình Xử Lý GENEVE TLV

> **Mã bài lab:** `05.01`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$0.096 USD / giờ (2 instances c6i.large = ~$0.192 USD / giờ)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `fabric-insp-fw-1a`, `fabric-insp-fw-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành hạ tầng mạng Inspection VPC tại [Module 02](../02-ha-tang-mang-co-ban/README.md).
- Subnets `fabric-insp-fw-1a` (`10.70.10.0/24`) và `fabric-insp-fw-1b` (`10.70.11.0/24`) sẵn sàng.

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
        "ec2:RunInstances",
        "ec2:DescribeInstances",
        "ec2:TerminateInstances",
        "ec2:CreateSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:ModifyInstanceAttribute"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** 2 EC2 instances `c6i.large` (tối ưu tính toán cho deep packet inspection) tiêu tốn ~$4.60 USD/ngày.
- **Cảnh báo Kỹ Thuật GWLB GENEVE TLV (Rất quan trọng):** AWS Gateway Load Balancer đóng gói gói tin gốc vào GENEVE tunnel (UDP port 6081) và gắn kèm một header tùy chọn đặc thù: **Type 1 Option 1 TLV** (chứa ENI ID và Flow Cookie). Nếu chỉ sử dụng lệnh `ip link add geneve0` thông thường của Linux, nhân hệ điều hành sẽ loại bỏ TLV metadata này và không thể đóng gói trả ngược về đúng GWLB ENI, dẫn đến đứt gãy luồng mạng. Bắt buộc phải triển khai daemon xử lý tunnel (`aws-gateway-load-balancer-tunnel-handler`) hoặc script Suricata hỗ trợ GWLB GENEVE.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo Security Group Cho Suricata Appliances
Tạo Security Group `fabric-suricata-sg` trong `fabric-inspection-vpc`:
- **Inbound:**
  - UDP port `6081` (GENEVE) từ CIDR Inspection VPC: `10.70.0.0/16`.
  - TCP port `80` (HTTP Health Check) từ CIDR Inspection VPC: `10.70.0.0/16`.
  - TCP port `22` (SSH) hoặc truy cập qua SSM Session Manager.
- **Outbound:** All traffic.

### Bước 2: Khởi Tạo 2 EC2 Instances Suricata Đa AZ
Khởi tạo 2 EC2 instances trên AWS Console:
1. **Instance 1 (`fabric-suricata-1a`):**
   - Subnet: `fabric-insp-fw-1a` (`10.70.10.0/24`)
   - Instance type: `c6i.large`
   - AMI: Amazon Linux 2023 hoặc Ubuntu 22.04 LTS
   - Security Group: `fabric-suricata-sg`
   - IAM Role: Gán role có quyền `AmazonSSMManagedInstanceCore`.
2. **Instance 2 (`fabric-suricata-1b`):**
   - Subnet: `fabric-insp-fw-1b` (`10.70.11.0/24`)
   - Các thông số tương tự Instance 1.

### Bước 3: Cấu Hình User Data Xử Lý GENEVE & Cài Đặt Suricata
Cung cấp đoạn script khởi tạo (User Data) cho instances để tự động biên dịch và chạy `aws-gateway-load-balancer-tunnel-handler` kèm Suricata:
```bash
#!/bin/bash
dnf update -y
dnf install -y git golang suricata iptables nc

# 1. Tải và build GWLB Tunnel Handler chính thức của AWS
cd /opt
git clone https://github.com/aws-samples/aws-gateway-load-balancer-tunnel-handler.git
cd aws-gateway-load-balancer-tunnel-handler
go build -o gwlb-handler main.go

# 2. Cấu hình Tunnel Handler lắng nghe GENEVE UDP 6081 và chuyển tiếp qua Suricata
cat <<'EOF' > /etc/systemd/system/gwlb-handler.service
[Unit]
Description=AWS GWLB Tunnel Handler
After=network.target

[Service]
Type=simple
ExecStart=/opt/aws-gateway-load-balancer-tunnel-handler/gwlb-handler -in udp:6081 -out udp:6081
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now gwlb-handler

# 3. Kích hoạt HTTP Health Check phản hồi port 80 cho GWLB
nohup python3 -m http.server 80 &
```

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái của 2 instances Suricata:
```bash
aws ec2 describe-instances --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-suricata-*" "Name=instance-state-name,Values=running" \
  --query 'Reservations[*].Instances[*].{Name:Tags[?Key==`Name`].Value | [0],Id:InstanceId,AZ:Placement.AvailabilityZone,PrivateIP:PrivateIpAddress,State:State.Name}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Chấm dứt 2 instances Suricata nếu cần triển khai lại:
```bash
instance_ids=$(aws ec2 describe-instances --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-suricata-*" "Name=instance-state-name,Values=running" --query 'Reservations[*].Instances[*].InstanceId' --output text)
if [ -n "$instance_ids" ]; then
  aws ec2 terminate-instances --region ap-southeast-1 --instance-ids $instance_ids
fi
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/05-gwlb/01-suricata-instances.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 2 instances `fabric-suricata-1a` và `fabric-suricata-1b` đều ở trạng thái `running`.
- [ ] Daemon GWLB Tunnel Handler đang chạy và lắng nghe trên UDP port `6081`.
- [ ] Port `80` phản hồi HTTP 200 OK phục vụ cho health check của Target Group.
""", encoding="utf-8")

# 02-gateway-load-balancer-and-target-group.md
(BASE / "02-gateway-load-balancer-and-target-group.md").write_text("""# 05.02 — Khởi Tạo Gateway Load Balancer (GWLB) & Target Group GENEVE

> **Mã bài lab:** `05.02`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** ~$0.0125 USD / giờ cho GWLB tại Singapore  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [05.01](01-suricata-ec2-instances.md). 2 instances Suricata đang ở trạng thái `running`.

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
        "elasticloadbalancing:CreateLoadBalancer",
        "elasticloadbalancing:CreateTargetGroup",
        "elasticloadbalancing:RegisterTargets",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetHealth"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** GWLB tính phí ~$0.0125 USD/giờ cộng với phí GLCU lưu lượng kiểm tra.
- **Cảnh báo Health Check:** Health check của Target Group phải sử dụng giao thức **TCP hoặc HTTP port 80** thay vì kiểm tra trực tiếp qua GENEVE để đảm bảo độ tin cậy và không làm ngập log của Suricata.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo Target Group Với Giao Thức GENEVE
1. Truy cập **EC2 Console** -> **Target groups** -> **Create target group**.
2. **Basic configuration:**
   - Target type: `Instances`
   - Target group name: `fabric-suricata-tg`
   - Protocol: **`GENEVE`**
   - Port: **`6081`**
   - VPC: Chọn `fabric-inspection-vpc`
3. **Health checks:**
   - Health check protocol: `HTTP`
   - Health check port: `80`
   - Health check path: `/`
   - Healthy threshold: `2`, Unhealthy threshold: `2`, Interval: `10` seconds (failover nhanh).
4. **Register targets:**
   - Chọn cả 2 instances `fabric-suricata-1a` và `fabric-suricata-1b` -> Nhấp **Include as pending below**.
5. Nhấp **Create target group**.

### Bước 2: Khởi Tạo Gateway Load Balancer
1. Truy cập **EC2 Console** -> **Load Balancers** -> **Create load balancer**.
2. Tại mục **Gateway Load Balancer**, nhấp **Create**.
3. **Basic configuration:**
   - Load balancer name: `fabric-gwlb`
   - VPC: `fabric-inspection-vpc`
   - Mappings: Chọn 2 AZs:
     - `ap-southeast-1a`: Chọn subnet `fabric-insp-fw-1a`
     - `ap-southeast-1b`: Chọn subnet `fabric-insp-fw-1b`
4. **Listeners and routing:**
   - Default action: Chọn Target group `fabric-suricata-tg`.
5. Nhấp **Create load balancer**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái của GWLB và sức khỏe của các targets:
```bash
# 1. Kiểm tra trạng thái GWLB
aws elbv2 describe-load-balancers --region ap-southeast-1 --names fabric-gwlb \
  --query 'LoadBalancers[0].{Name:LoadBalancerName,State:State.Code,VpcId:VpcId,Type:Type}' --output table

# 2. Kiểm tra Target Health của 2 Suricata appliances
tg_arn=$(aws elbv2 describe-target-groups --region ap-southeast-1 --names fabric-suricata-tg --query 'TargetGroups[0].TargetGroupArn' --output text)
aws elbv2 describe-target-health --region ap-southeast-1 --target-group-arn $tg_arn --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa GWLB và Target Group khi cần hoàn tác:
```bash
gwlb_arn=$(aws elbv2 describe-load-balancers --region ap-southeast-1 --names fabric-gwlb --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null)
if [ -n "$gwlb_arn" ]; then
  aws elbv2 delete-load-balancer --region ap-southeast-1 --load-balancer-arn $gwlb_arn
fi
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/05-gwlb/02-gwlb-targets-health.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Gateway Load Balancer `fabric-gwlb` đạt trạng thái `active`.
- [ ] Cả 2 Suricata targets đều đạt trạng thái `healthy` trong Target Group.
""", encoding="utf-8")

# 03-gwlb-endpoints-creation.md
(BASE / "03-gwlb-endpoints-creation.md").write_text("""# 05.03 — Tạo Endpoint Service & Hai Zonal GWLB Endpoints Riêng Biệt (AZ-a, AZ-b)

> **Mã bài lab:** `05.03`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** ~$0.01/giờ/endpoint (~$0.02 USD / giờ cho 2 zonal endpoints)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `fabric-insp-gwlbe-1a`, `fabric-insp-gwlbe-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [05.02](02-gateway-load-balancer-and-target-group.md). GWLB `fabric-gwlb` đang ở trạng thái `active`.

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
        "ec2:CreateVpcEndpointServiceConfiguration",
        "ec2:CreateVpcEndpoint",
        "ec2:DescribeVpcEndpointServices",
        "ec2:DescribeVpcEndpoints"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Mỗi GWLB Endpoint tính phí ~$0.01 USD/giờ.
- **Cảnh báo Kiến Trúc Zonal GWLBe (Cực kỳ quan trọng):** GWLB Endpoint là tài nguyên mang tính **cục bộ theo từng Vùng sẵn sàng (Zonal Resource)**. Bạn **KHÔNG THỂ TẠO 1 ENDPOINT CHỨA 2 SUBNET KHÁC NHAU** trên bảng định tuyến. Bắt buộc phải tạo **HAI VPC ENDPOINTS RIÊNG BIỆT**:
  - `fabric-gwlbe-1a` đặt trong subnet `fabric-insp-gwlbe-1a` (AZ-a)
  - `fabric-gwlbe-1b` đặt trong subnet `fabric-insp-gwlbe-1b` (AZ-b)
  Điều này cho phép bảng định tuyến của từng AZ trỏ chính xác về Endpoint tương ứng trong cùng AZ, bảo toàn 100% tính đối xứng của luồng gói tin!

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Tạo VPC Endpoint Service Cho GWLB
1. Truy cập **VPC Console** -> **Endpoint services** -> **Create endpoint service**.
2. Name: `fabric-gwlb-endpoint-service`.
3. Load balancer type: `Gateway`.
4. Available load balancers: Chọn `fabric-gwlb`.
5. Require acceptance for endpoint: Bỏ chọn (`false` - tự động chấp nhận kết nối).
6. Nhấp **Create**. Ghi lại `Service name` (dạng `com.amazonaws.vpce.ap-southeast-1.vpce-svc-...`).

### Bước 2: Tạo GWLB Endpoint Thứ Nhất Tại AZ-a (`fabric-gwlbe-1a`)
1. Truy cập **VPC Console** -> **Endpoints** -> **Create endpoint**.
2. Name: `fabric-gwlbe-1a`.
3. Service category: Chọn **Other endpoint services**.
4. Service name: Dán chuỗi `Service name` vừa sao chép ở Bước 1 -> Nhấp **Verify service**.
5. VPC: Chọn `fabric-inspection-vpc`.
6. Subnets: Chọn AZ `ap-southeast-1a` và subnet `fabric-insp-gwlbe-1a` (`10.70.1.0/28`).
7. Nhấp **Create endpoint**.

### Bước 3: Tạo GWLB Endpoint Thứ Hai Tại AZ-b (`fabric-gwlbe-1b`)
Thực hiện tương tự Bước 2 cho AZ-b:
- Name: `fabric-gwlbe-1b`.
- VPC: `fabric-inspection-vpc`.
- Subnets: Chọn AZ `ap-southeast-1b` và subnet `fabric-insp-gwlbe-1b` (`10.70.1.16/28`).
- Nhấp **Create endpoint**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra cả 2 GWLB Endpoints:
```bash
aws ec2 describe-vpc-endpoints --region ap-southeast-1 \
  --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-inspection-vpc" --query 'Vpcs[0].VpcId' --output text)" \
  --query 'VpcEndpoints[*].{Name:Tags[?Key==`Name`].Value | [0],Id:VpcEndpointId,State:State,Type:VpcEndpointType,Subnet:SubnetIds[0]}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa 2 GWLB Endpoints và Endpoint Service:
```bash
for ep_id in $(aws ec2 describe-vpc-endpoints --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-gwlbe-*" --query 'VpcEndpoints[*].VpcEndpointId' --output text); do
  aws ec2 delete-vpc-endpoints --region ap-southeast-1 --vpc-endpoint-ids $ep_id
done
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/05-gwlb/03-zonal-gwlbe-active.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Cả 2 Zonal GWLB Endpoints (`fabric-gwlbe-1a` và `fabric-gwlbe-1b`) đều ở trạng thái `available`.
- [ ] Mỗi endpoint được gắn duy nhất vào một subnet tương ứng trong AZ của nó.
""", encoding="utf-8")

# 04-inspection-routing-and-symmetric-verification.md
(BASE / "04-inspection-routing-and-symmetric-verification.md").write_text("""# 05.04 — Cắt Chuyển Định Tuyến East-West Qua GWLB & Xác Minh Luồng Đối Xứng

> **Mã bài lab:** `05.04`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành [05.01](01-suricata-ec2-instances.md), [05.02](02-gateway-load-balancer-and-target-group.md), [05.03](03-gwlb-endpoints-creation.md).
- Cả 2 Suricata appliances đang healthy và 2 Zonal GWLBe đang `available`.

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
        "ec2:DescribeRouteTables",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:ReplaceTransitGatewayRoute"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** $0.00 USD.
- **Cảnh báo Gián Đoạn Mạng (Cutover Window):** Đây là bước cắt chuyển chính thức lưu lượng East-West giữa Edge và Core. Nếu định tuyến trong Inspection VPC sai, toàn bộ kết nối giữa Frontend và Backend sẽ bị mất. Cần chuẩn bị sẵn lệnh rollback.

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

### Bước 1: Cấu Hình Định Tuyến Subnet Trong Inspection VPC
1. **Bảng định tuyến TGW Subnet AZ-a (`fabric-insp-tgw-rt-1a`):**
   - Route `10.40.0.0/16` -> trỏ tới `fabric-gwlbe-1a` (`vpce-...`)
   - Route `10.50.0.0/16` -> trỏ tới `fabric-gwlbe-1a` (`vpce-...`)
2. **Bảng định tuyến TGW Subnet AZ-b (`fabric-insp-tgw-rt-1b`):**
   - Route `10.40.0.0/16` -> trỏ tới `fabric-gwlbe-1b` (`vpce-...`)
   - Route `10.50.0.0/16` -> trỏ tới `fabric-gwlbe-1b` (`vpce-...`)
3. **Bảng định tuyến GWLBe Subnets (`fabric-insp-gwlbe-rt`):**
   - Gắn với cả 2 subnets `fabric-insp-gwlbe-1a` và `fabric-insp-gwlbe-1b`.
   - Route `10.0.0.0/8` -> trỏ về Transit Gateway (`fabric-tgw`).

### Bước 2: Cắt Chuyển Tuyến Đường Trên TGW Route Tables
Truy cập **Transit Gateway Route Tables**:
1. Tại bảng **`fabric-tgw-edge-rt`**:
   - Chỉnh sửa route `10.50.0.0/16`: Chuyển target từ `fabric-core-tgw-attachment` sang **`fabric-insp-tgw-attachment`**.
2. Tại bảng **`fabric-tgw-core-rt`**:
   - Chỉnh sửa route `10.40.0.0/16`: Chuyển target từ `fabric-edge-tgw-attachment` sang **`fabric-insp-tgw-attachment`**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

### 1. Xác Minh Lưu Lượng Thông Suốt (End-to-End Connectivity)
Từ một Pod hoặc máy test trong Edge VPC (`10.40.10.x`), gửi request sang Core Internal NLB:
```bash
curl -Iv https://order.fabric.internal/health --connect-timeout 5
```

### 2. Xác Minh Tính Đối Xứng Của Luồng (Symmetric Flow Verification)
Mở 2 phiên kết nối SSM vào 2 Suricata appliances (`fabric-suricata-1a` và `fabric-suricata-1b`). Chạy `tcpdump` bắt gói tin GENEVE:
```bash
sudo tcpdump -ni any 'udp port 6081' -vv
```
**Bằng chứng đối xứng đạt chuẩn:**
- Khi request xuất phát từ AZ-a, cả gói Request và gói Response đều xuất hiện trên màn hình `tcpdump` của `fabric-suricata-1a`.
- Không có hiện tượng chỉ thấy gói SYN ở 1a còn gói SYN-ACK lại chạy qua 1b (chứng minh TGW Appliance Mode hoạt động chính xác).

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Hoàn tác chuyển tuyến TGW về kết nối trực tiếp:
```bash
aws ec2 replace-transit-gateway-route --transit-gateway-route-table-id <edge-rt-id> --destination-cidr-block 10.50.0.0/16 --transit-gateway-attachment-id <core-att-id>
aws ec2 replace-transit-gateway-route --transit-gateway-route-table-id <core-rt-id> --destination-cidr-block 10.40.0.0/16 --transit-gateway-attachment-id <edge-att-id>
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/05-gwlb/04-symmetric-tcpdump-trace.log`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Edge gọi sang Core thành công qua cổng 443 thông qua GWLB và Suricata.
- [ ] Ghi nhận `tcpdump` chứng minh 100% Request và Response của cùng 1 flow đi qua cùng 1 Suricata appliance trong cùng AZ.
- [ ] Suricata ghi nhận traffic trong file `/var/log/suricata/eve.json`.
""", encoding="utf-8")

# Update README.md for Module 05
(BASE / "README.md").write_text("""# Module 05: GWLB & Suricata IDS/IPS (East-West Traffic Inspection)

Module này hướng dẫn triển khai hệ thống kiểm duyệt lưu lượng nội bộ giữa Edge và Core (East-West) sử dụng AWS Gateway Load Balancer, 2 Zonal GWLB Endpoints độc lập theo từng AZ, cụm Suricata EC2 xử lý GENEVE TLV options và kích hoạt TGW Appliance Mode để đảm bảo định tuyến đối xứng tuyệt đối (Symmetric Flow).

## Danh Sách Bài Lab

| Mã Lab | Tên Bài Lab & Nội Dung Trọng Tâm | Trạng Thái | File Hướng Dẫn |
|---|---|:---:|---|
| **05.01** | **Suricata EC2 Appliances:** 2 instances c6i.large xử lý GENEVE TLV trên UDP 6081. | `DRAFT` | [01-suricata-ec2-instances.md](01-suricata-ec2-instances.md) |
| **05.02** | **GWLB & Target Group:** Giao thức GENEVE 6081, HTTP port 80 health checks. | `DRAFT` | [02-gateway-load-balancer-and-target-group.md](02-gateway-load-balancer-and-target-group.md) |
| **05.03** | **Zonal GWLB Endpoints:** Khởi tạo 2 endpoints riêng biệt tại AZ-a và AZ-b. | `DRAFT` | [03-gwlb-endpoints-creation.md](03-gwlb-endpoints-creation.md) |
| **05.04** | **Cutover East-West & Symmetric Flow:** Chuyển tuyến TGW, bắt tcpdump kiểm chứng đối xứng. | `DRAFT` | [04-inspection-routing-and-symmetric-verification.md](04-inspection-routing-and-symmetric-verification.md) |
""", encoding="utf-8")

print("Module 05 rewritten successfully.")
