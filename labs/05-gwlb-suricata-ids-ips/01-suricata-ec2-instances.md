# 05.01 — Khởi Tạo 2 Suricata Appliances EC2 & Cấu Hình Xử Lý GENEVE TLV

> **Mã bài lab:** `05.01`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** ~$0.096 USD / giờ (2 instances c6i.large = ~$0.192 USD / giờ)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `fabric-insp-fw-1a`, `fabric-insp-fw-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành hạ tầng mạng Inspection VPC tại [Module 02](../02-ha-tang-mang-co-ban/README.md).
- Subnets `fabric-insp-fw-1a` (`10.70.10.0/24`) và `fabric-insp-fw-1b` (`10.70.11.0/24`) đang ở trạng thái sẵn sàng.
- IAM Instance Profile cho SSM (`fabric-ssm-instance-profile`) có quyền `AmazonSSMManagedInstanceCore` để kết nối mà không cần mở cổng SSH.
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
     - Chọn **Amazon Linux** -> AMI: **Amazon Linux 2023 AMI** (64-bit x86).
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
     - Cuộn xuống ô **User data**, dán toàn bộ script khởi tạo sau:
       ```bash
       #!/bin/bash
       dnf update -y
       dnf install -y git golang suricata iptables tcpdump nc
       
       # 1. Tải và build GWLB Tunnel Handler chính thức của AWS hỗ trợ GENEVE TLV Option
       cd /opt
       git clone https://github.com/aws-samples/aws-gateway-load-balancer-tunnel-handler.git
       cd aws-gateway-load-balancer-tunnel-handler
       go build -o gwlb-handler main.go
       
       # 2. Cấu hình Tunnel Handler lắng nghe GENEVE UDP 6081
       cat <<'EOF' > /etc/systemd/system/gwlb-handler.service
       [Unit]
       Description=AWS GWLB GENEVE Tunnel Handler
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
       
       # 4. Bật IP Forwarding trên Kernel
       sysctl -w net.ipv4.ip_forward=1
       echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
       ```
   - Nhấp nút cam **Launch instance**.

3. **Cấu hình Máy ảo 2 (`fabric-suricata-1b`):**
   - Nhấp **Launch instances**.
   - **Name:** Nhập `fabric-suricata-1b`.
   - **AMI:** Amazon Linux 2023 | **Type:** `c6i.large`.
   - **Network settings:**
     - VPC: `fabric-inspection-vpc`.
     - **Subnet:** Chọn `fabric-insp-fw-1b` (`10.70.11.0/24`).
     - Auto-assign public IP: Disable.
     - Security group: `fabric-suricata-sg`.
   - **Advanced details:** Gán IAM instance profile SSM và dán cùng nội dung User Data ở trên.
   - Nhấp **Launch instance**.

---

### Bước 3: Tắt Source/Destination Check Trên Cả 2 Appliances (Bắt Buộc)
1. Tại danh sách **Instances** trong EC2 Console:
2. Chọn checkbox của `fabric-suricata-1a`:
   - Nhấp menu **Actions** ở góc trên -> Chọn **Networking** -> Chọn **Change source/destination check**.
   - Bỏ chọn checkbox **Stop** (Đảm bảo ô trạng thái hiển thị **Disabled**).
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
  --query 'Reservations[*].Instances[*].{Name:Tags[?Key==`Name`].Value | [0],Id:InstanceId,AZ:Placement.AvailabilityZone,PrivateIp:PrivateIpAddress,SourceDestCheck:SourceDestCheck}' \
  --output table

# 2. Kiểm tra tiến trình gwlb-handler và cổng 80 qua SSM Run Command
SURICATA_1A_ID=$(aws ec2 describe-instances --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-suricata-1a" --query 'Reservations[0].Instances[0].InstanceId' --output text)
aws ssm send-command --region ap-southeast-1 \
  --instance-ids $SURICATA_1A_ID \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["systemctl status gwlb-handler --no-pager", "netstat -tuln | grep -E \"6081|80\""]' \
  --query 'Command.CommandId' --output text
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

- [ ] Cả 2 máy chủ Suricata `fabric-suricata-1a` và `fabric-suricata-1b` ở trạng thái `running`.
- [ ] Cờ `SourceDestCheck` hiển thị giá trị `false` trên cả 2 máy chủ.
- [ ] Cổng UDP `6081` và TCP `80` đang lắng nghe và phản hồi bên trong hệ điều hành.
- [ ] Dịch vụ `gwlb-handler` ở trạng thái `active (running)`.
