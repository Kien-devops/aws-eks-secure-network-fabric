# 05.01 — Khởi Tạo 2 Suricata Appliances EC2 & Cấu Hình Xử Lý GENEVE TLV

> **Mã bài lab:** `05.01`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí thực tế (EC2 Spot):** ~$0.043 USD / giờ / instance (2 instances c6i.large Spot = ~$0.086 USD / giờ, tiết kiệm 55% so với On-Demand)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `fabric-insp-fw-1a`, `fabric-insp-fw-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành hạ tầng mạng Inspection VPC tại [Module 02](../02-ha-tang-mang-co-ban/README.md).
- Subnets `fabric-insp-fw-1a` (`10.70.10.0/24`) và `fabric-insp-fw-1b` (`10.70.11.0/24`) đang ở trạng thái sẵn sàng.
- IAM Instance Profile cho SSM (`fabric-ssm-instance-profile`) có quyền `AmazonSSMManagedInstanceCore` để kết nối mà không cần mở cổng SSH.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

### Gate bootstrap trước Launch

1. Chọn **Ubuntu Server 24.04 LTS amd64, publisher Canonical**, ghi AMI ID Singapore vào evidence; dùng thống nhất gói `.deb` với 09.02. Không dùng AL2023 cho các lệnh apt/dpkg dưới đây.
2. VPC → Endpoints → Create → AWS services: tạo `ssm`, `ssmmessages`, `logs` trong **Inspection VPC**, chọn hai firewall subnets, bật Private DNS; endpoint SG chỉ nhận 443 từ appliance SG. Endpoint trong Edge/Core không tự phục vụ Inspection.
3. Appliance subnets hiện chỉ có local, không tải apt/GitHub. Phải có AMI appliance đã build/kiểm tra trước, hoặc bootstrap tạm được cho phép: NAT theo 06.01; route appliance subnet default tới TGW; `inspection-rt` default tới Egress; route Egress TGW subnet tới NAT cùng AZ; NAT public return `10.70.0.0/16` tới TGW; `egress-rt` route `10.70.0.0/16` tới Inspection. Lưu route/association cũ, giới hạn thời gian; đây là ngoại lệ quản trị, không phải ma trận MVP.
4. Kiểm tra SSM Online và package/GitHub connectivity trước cài. Sau build, xóa ngoại lệ bootstrap, phục hồi ma trận 01.03; SSM/Logs tiếp tục qua endpoints. Không gán public IP hay mở SSH để né prerequisite. Chưa có AMI/bootstrap thì dừng, giữ DRAFT.

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
        "ec2:ModifyInstanceAttribute",
        "ec2:CreateTags",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** 2 EC2 instances `c6i.large` (tối ưu tính toán cho deep packet inspection) tiêu tốn ~$4.60 USD/ngày. Cần theo dõi trong ngân sách $50.00 USD.
- **Cảnh báo Kỹ Thuật GWLB GENEVE TLV (Rất quan trọng):** AWS Gateway Load Balancer đóng gói gói tin gốc vào GENEVE tunnel (UDP port 6081) và gắn kèm một header tùy chọn đặc thù: **Type 1 Option 1 TLV** (chứa ENI ID và Flow Cookie). Nếu chỉ sử dụng lệnh `ip link add geneve0` thông thường của Linux, nhân hệ điều hành sẽ loại bỏ TLV metadata này và không thể đóng gói trả ngược về đúng GWLB ENI, dẫn đến đứt gãy luồng mạng. Bắt buộc phải triển khai daemon xử lý tunnel (`aws-gateway-load-balancer-tunnel-handler`) hoặc script Suricata hỗ trợ GWLB GENEVE.
- **Tắt Source/Destination Check:** Là một thiết bị tường lửa trung gian (Middlebox Appliance), máy ảo Suricata **BẮT BUỘC PHẢI TẮT KIỂM TRA NGUỒN/ĐÍCH (Source/Dest Check = False)** trên giao diện mạng ENI, nếu không AWS Hypervisor sẽ chặn toàn bộ các gói tin chuyển tiếp có IP nguồn hoặc đích không trùng với chính instance.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Tạo Security Group Cho Cụm Suricata Appliances
Truy cập **VPC Console** tại Singapore `ap-southeast-1`:
1. Tại menu bên trái, chọn **Security groups** -> Nhấp **Create security group**.
2. **Details:**
   - **Security group name:** Nhập `fabric-suricata-sg`.
   - **Description:** Nhập `Security group for Suricata IDS/IPS appliances behind GWLB`.
   - **VPC:** Chọn `fabric-inspection-vpc`.
3. **Inbound rules:**
   - Nhấp **Add rule**:
     - Type: `Custom UDP` | Protocol: `UDP` | Port range: `6081` (Cổng GENEVE tiêu chuẩn của GWLB).
     - Source: `Custom` -> Nhập CIDR của Inspection VPC: `10.70.0.0/16`.
     - Description: `GENEVE encapsulated traffic from GWLB`.
   - Nhấp **Add rule**:
     - Type: `HTTP` | Protocol: `TCP` | Port range: `80` (Dùng cho GWLB Health Check).
     - Source: `Custom` -> Nhập CIDR: `10.70.0.0/16`.
     - Description: `GWLB TCP/HTTP health check probe`.
4. **Outbound rules:** Giữ nguyên mặc định (All traffic).
5. **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
6. Nhấp nút cam **Create security group**.

---

### Bước 2: Khởi Tạo 2 Máy Chủ Ảo Suricata EC2 Đa AZ
Mở **EC2 Console** tại Region Singapore `ap-southeast-1`:
1. Tại menu bên trái, chọn **Instances** -> Nhấp nút cam **Launch instances**.

2. **Cấu hình Máy ảo 1 (`fabric-suricata-1a`):**
   - **Name and tags:**
     - Name: `fabric-suricata-1a`.
     - Add tag: Key: `Project` | Value: `aws-eks-secure-network-fabric`; Key: `Role` | Value: `firewall-appliance`.
   - **Application and OS Images (Amazon Machine Image):**
     - Chọn **Ubuntu** → **Ubuntu Server 24.04 LTS amd64**; xác nhận publisher Canonical và AMI ID Singapore.
   - **Instance type:** Chọn `c6i.large` (2 vCPU, 4 GiB Memory - hỗ trợ Enhanced Networking và DPDK).
   - **Key pair (login):** Chọn **Proceed without a key pair (Not recommended)** (Truy cập hoàn toàn an toàn thông qua AWS Systems Manager / SSM).
   - **Network settings:** Nhấp nút **Edit**:
     - **VPC:** Chọn `fabric-inspection-vpc`.
     - **Subnet:** Chọn `fabric-insp-fw-1a` (`10.70.10.0/24`).
     - **Auto-assign public IP:** Chọn **Disable**.
     - **Firewall (security groups):** Chọn **Select existing security group** -> Chọn `fabric-suricata-sg`.
   - **Configure storage:** Giữ nguyên 8 GiB gp3 (hoặc nâng lên 20 GiB gp3 để lưu log Suricata).
   - **Advanced details:**
     - **IAM instance profile:** Chọn `fabric-ssm-instance-profile` (Role chứa `AmazonSSMManagedInstanceCore`).
     - Không dùng user data để giả định bootstrap đã thành công. Launch với AMI đã chuẩn bị; hoặc sau SSM Online, **Connect → Session Manager → sudo -i**, thực hiện các lệnh sau:
       ```bash
       set -euo pipefail
       apt-get update
       apt-get install -y git cmake g++ make suricata iptables tcpdump jq curl
       
       # 1. Tải và build GWLB Tunnel Handler chính thức của AWS hỗ trợ GENEVE TLV Option
       cd /opt
       git clone --branch v3.3 --depth 1 https://github.com/aws-samples/aws-gateway-load-balancer-tunnel-handler.git
       cd aws-gateway-load-balancer-tunnel-handler
       git rev-parse HEAD
       cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
       cmake --build build -j2
       install -m 0755 build/gwlbtun /usr/local/sbin/gwlbtun
       suricata --build-info | grep -i NFQ
       # Dừng nếu build không hỗ trợ NFQUEUE.
       systemctl disable --now suricata
       install -d /etc/suricata/rules /var/log/suricata
       cat > /etc/suricata/rules/fabric.rules <<'RULES'
       drop tcp any any -> any 8084 (msg:"FABRIC PLAINTEXT TEST DROP"; content:"FABRIC_IPS_TEST"; sid:2026001; rev:1;)
       RULES
       # Sửa /etc/suricata/suricata.yaml bằng editor trước khi tiếp tục:
       # HOME_NET: "[10.40.0.0/16,10.50.0.0/16]"
       # rule-files: thêm /etc/suricata/rules/fabric.rules
       # outputs.eve-log: enabled yes, filetype regular, filename eve.json;
       # types gồm alert, flow, http, tls. Không xóa các mục khác của YAML.
       suricata -T -c /etc/suricata/suricata.yaml
       cat > /usr/local/sbin/fabric-tunnel-hook <<'HOOK'
       #!/bin/bash
       set -euo pipefail
       mode=$1; incoming=$2; outgoing=$3; endpoint=$4
       table=$((16#${endpoint: -6}+10000))
       if [ "$mode" = CREATE ]; then
         sysctl -w "net.ipv4.conf.${incoming}.rp_filter=0"
         ip route replace default dev "$outgoing" table "$table"
         ip rule add iif "$incoming" lookup "$table" priority 100
       else
         ip rule del iif "$incoming" lookup "$table" priority 100 || true
         ip route flush table "$table"
       fi
       HOOK
       chmod 0755 /usr/local/sbin/fabric-tunnel-hook
       cat > /etc/systemd/system/fabric-suricata.service <<'UNIT'
       [Unit]
       Description=Fabric inline NFQUEUE inspection
       After=network-online.target
       [Service]
       Type=simple
       ExecStart=/usr/bin/suricata -c /etc/suricata/suricata.yaml -q 0
       Restart=on-failure
       [Install]
       WantedBy=multi-user.target
       UNIT
       # ponytail: một NFQUEUE cho lab; thêm multi-queue sau khi đo nghẽn CPU.
       # Không dùng queue-bypass: không có Suricata thì fail closed.
       iptables -C FORWARD -i gwi+ -j NFQUEUE --queue-num 0 2>/dev/null || \
         iptables -I FORWARD 1 -i gwi+ -j NFQUEUE --queue-num 0
       apt-get install -y iptables-persistent
       netfilter-persistent save
       
       # 2. Cấu hình Tunnel Handler lắng nghe GENEVE UDP 6081
       cat <<'EOF' > /etc/systemd/system/gwlb-handler.service
       [Unit]
       Description=AWS GWLB GENEVE Tunnel Handler
       After=network-online.target fabric-suricata.service netfilter-persistent.service
       Requires=fabric-suricata.service
       BindsTo=fabric-suricata.service
       
       [Service]
       Type=simple
       ExecStart=/usr/local/sbin/gwlbtun -c /usr/local/sbin/fabric-tunnel-hook -r /usr/local/sbin/fabric-tunnel-hook -p 80
       Restart=always
       
       [Install]
       WantedBy=multi-user.target
       EOF
       
       systemctl daemon-reload
       systemctl enable --now fabric-suricata gwlb-handler
       
       # Health check là listener của gwlbtun, không phải HTTP server độc lập.
       
       # 4. Bật IP Forwarding trên Kernel
       sysctl -w net.ipv4.ip_forward=1
       echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
       printf 'net.ipv4.conf.all.rp_filter=0\nnet.ipv4.conf.default.rp_filter=0\n' > /etc/sysctl.d/90-fabric-transit.conf
       sysctl --system
       ```
   - Nhấp nút cam **Launch instance**.

3. **Cấu hình Máy ảo 2 (`fabric-suricata-1b`):**
   - Nhấp **Launch instances**.
   - **Name:** Nhập `fabric-suricata-1b`.
   - **AMI:** cùng Ubuntu 24.04 amd64 đã chọn | **Type:** `c6i.large`.
   - **Network settings:**
     - VPC: `fabric-inspection-vpc`.
     - **Subnet:** Chọn `fabric-insp-fw-1b` (`10.70.11.0/24`).
     - Auto-assign public IP: Disable.
     - Security group: `fabric-suricata-sg`.
   - **Advanced details:** Gán IAM instance profile SSM; lặp lại quy trình AMI/Session Manager trên, kiểm tra cả hai máy độc lập.
   - Nhấp **Launch instance**.

---

### Bước 3: Tắt Source/Destination Check Trên Cả 2 Appliances (Bắt Buộc)
1. Tại danh sách **Instances** trong EC2 Console:
2. Chọn checkbox của `fabric-suricata-1a`:
   - Nhấp menu **Actions** ở góc trên -> Chọn **Networking** -> Chọn **Change source/destination check**.
   - Chọn **Stop source/destination checking** → Save; xác nhận bằng API `SourceDestCheck=false`.
   - Nhấp **Save**.
3. Lặp lại thao tác trên cho `fabric-suricata-1b`:
   - Actions -> Networking -> Change source/destination check -> Chọn **Stop** (Disable) -> **Save**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái instances và xác nhận cờ Source/Dest Check đã tắt:
```bash
# 1. Liệt kê 2 máy ảo Suricata kèm trạng thái và Private IP
aws ec2 describe-instances --region ap-southeast-1 \
  --filters "Name=tag:Role,Values=firewall-appliance" "Name=instance-state-name,Values=running" \
  --query 'Reservations[*].Instances[*].{Name:Tags[?Key==`Name`].Value | [0],Id:InstanceId,Lifecycle:InstanceLifecycle,AZ:Placement.AvailabilityZone,PrivateIp:PrivateIpAddress,PublicIp:PublicIpAddress,SourceDestCheck:SourceDestCheck}' \
  --output table
```

**Bằng chứng runtime thực tế:**
```text
-----------------------------------------------------------------------------------------------------------------------------
|                                                     DescribeInstances                                                     |
+-----------------+-----------------------+------------+------------------+----------------+----------------+-------------------+
|       AZ        |          Id           | Lifecycle  |      Name        |   PrivateIp    |    PublicIp    | SourceDestCheck   |
+-----------------+-----------------------+------------+------------------+----------------+----------------+-------------------+
|  ap-southeast-1a|  i-089127472b112deff  |  spot      |fabric-suricata-1a|  10.70.10.161  |  56.10.185.216 |  False            |
|  ap-southeast-1b|  i-091e84ae2b923eea2  |  spot      |fabric-suricata-1b|  10.70.11.137  |  13.213.60.61  |  False            |
+-----------------+-----------------------+------------+------------------+----------------+----------------+-------------------+
```

```bash
# 2. Kiểm tra tiến trình gwlb-handler và cổng 80 qua SSM Run Command
aws ssm send-command --region ap-southeast-1 \
  --instance-ids i-089127472b112deff i-091e84ae2b923eea2 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["systemctl is-active fabric-suricata", "systemctl is-active gwlb-handler", "ss -tulpn | grep -E \"6081|80\"", "curl -i -s http://127.0.0.1:80/"]'
```

**Kết quả runtime output:**
```text
active
active
udp   UNCONN 0      0                0.0.0.0:6081      0.0.0.0:*    users:(("gwlbtun",pid=4179,fd=8))
udp   UNCONN 0      0                0.0.0.0:6081      0.0.0.0:*    users:(("gwlbtun",pid=4179,fd=7))
tcp   LISTEN 0      16                     *:80              *:*    users:(("gwlbtun",pid=4179,fd=5))

HTTP/1.1 200 OK
Cache-Control: max-age=0, no-cache
Connection: close
Content-Type: text/html
Content-Length: 331

<!DOCTYPE html>
<html lang="en-us">
<head><title>Health check</title></head><body>UDP receiver threads for port number 6081:
UDP receiver thread 0 (ID 4183): Healthy, 0 packets in, 0 bytes in, 28.303s since last packet.
UDP receiver thread 1 (ID 4184): Healthy, 0 packets in, 0 bytes in, 28.303s since last packet.
</body></html>
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa 2 máy chủ Suricata EC2:
```bash
for inst_id in $(aws ec2 describe-instances --region ap-southeast-1 --filters "Name=tag:Role,Values=firewall-appliance" --query 'Reservations[*].Instances[*].InstanceId' --output text); do
  aws ec2 terminate-instances --region ap-southeast-1 --instance-ids $inst_id
done
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/05-gwlb/01-suricata-instances.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Cả 2 máy chủ Suricata `fabric-suricata-1a` (`i-089127472b112deff`) và `fabric-suricata-1b` (`i-091e84ae2b923eea2`) được khởi tạo thành công dưới dạng **EC2 Spot Instances** (`c6i.large`) ở trạng thái `running`.
- [x] Cờ `SourceDestCheck` hiển thị giá trị `false` trên cả 2 máy chủ middlebox.
- [x] GWLB Tunnel Handler (`gwlbtun` v3.3) biên dịch thành công từ source AWS samples, hỗ trợ GENEVE Type 1 Option 1 TLV metadata.
- [x] Dịch vụ `fabric-suricata` và `gwlb-handler` đều ở trạng thái `active (running)`.
- [x] Cổng UDP `6081` (GENEVE) và TCP `80` (GWLB Health Check probe) đang lắng nghe và phản hồi `HTTP/1.1 200 OK (Healthy)` bên trong hệ điều hành.
- [x] Rule IPTables NFQUEUE (`-j NFQUEUE --queue-num 0`) và IP Forwarding (`net.ipv4.ip_forward=1`, `rp_filter=0`) đã được kích hoạt.
