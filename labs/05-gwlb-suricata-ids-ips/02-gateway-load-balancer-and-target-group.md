# 05.02 — Khởi Tạo Gateway Load Balancer (GWLB) & Target Group GENEVE

> **Mã bài lab:** `05.02`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** ~$0.0125 USD / giờ cho GWLB tại Singapore  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [05.01](01-suricata-ec2-instances.md). Cả 2 instances Suricata (`fabric-suricata-1a` và `fabric-suricata-1b`) đang ở trạng thái `running` với Source/Dest Check = False và cổng 80/6081 đang hoạt động.
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
        "elasticloadbalancing:CreateLoadBalancer",
        "elasticloadbalancing:CreateTargetGroup",
        "elasticloadbalancing:RegisterTargets",
        "elasticloadbalancing:DeregisterTargets",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth",
        "elasticloadbalancing:DeleteLoadBalancer",
        "elasticloadbalancing:DeleteTargetGroup",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** GWLB tính phí ~$0.0125 USD/giờ cộng với phí GLCU lưu lượng kiểm tra.
- **Cảnh báo Giao Thức Health Check:** Target Group bắt buộc phải dùng giao thức **GENEVE port 6081** cho Data path, nhưng cơ chế Health Check phải sử dụng **TCP hoặc HTTP port 80** thay vì kiểm tra qua GENEVE. Điều này giúp tách biệt giữa việc giám sát tình trạng sống còn của hệ điều hành và việc băm gói tin tunnel, đồng thời cho phép GWLB phát hiện sự cố và ngắt traffic trong vòng 10 giây.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo Target Group Với Giao Thức GENEVE Port 6081
Mở **EC2 Console** tại Region Singapore `ap-southeast-1`:
1. Tại menu điều hướng bên trái, cuộn xuống nhóm **Load Balancing** -> Chọn **Target Groups**.
2. Nhấp vào nút cam **Create target group** ở góc trên bên phải.
3. **Step 1 — Specify group details:**
   - **Choose a target type:** Chọn **Instances**.
   - **Target group name:** Nhập `fabric-suricata-tg`.
   - **Protocol:** Chọn **GENEVE**.
   - **Port:** Nhập **`6081`** (Cổng tiêu chuẩn của GENEVE encapsulation).
   - **IP address type:** Chọn **IPv4**.
   - **VPC:** Chọn `fabric-inspection-vpc` (`10.70.0.0/16`).
   - **Health checks:**
     - **Health check protocol:** Chọn **HTTP** (hoặc TCP).
     - **Health check path:** Nhập `/`.
   - **Advanced health check settings:**
     - **Port:** Chọn **Override** -> Nhập `80`.
     - **Healthy threshold:** Nhập `2`.
     - **Unhealthy threshold:** Nhập `2`.
     - **Timeout:** Nhập `5` seconds.
     - **Interval:** Nhập `10` seconds (Cấu hình failover nhanh cho GameDay).
     - **Success codes:** Nhập `200`.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
   - Nhấp **Next**.
4. **Step 2 — Register targets:**
   - Trong bảng **Available instances**, tìm và tích chọn cả 2 instances:
     - [x] `fabric-suricata-1a`
     - [x] `fabric-suricata-1b`
   - **Ports for the selected instances:** Mặc định là `6081`.
   - Nhấp nút **Include as pending below**.
   - Xác nhận 2 instances xuất hiện trong bảng Review targets với port 6081.
5. Nhấp nút cam **Create target group** ở cuối trang.

---

### Bước 2: Khởi Tạo Gateway Load Balancer (`fabric-gwlb`)
Tại menu bên trái EC2 Console -> Chọn **Load Balancers**:
1. Nhấp nút cam **Create load balancer**.
2. Tìm khối **Gateway Load Balancer** -> Nhấp nút **Create**.
3. **Basic configuration:**
   - **Load balancer name:** Nhập `fabric-gwlb`.
   - **IP address type:** Chọn **IPv4**.
4. **Network mapping:**
   - **VPC:** Chọn `fabric-inspection-vpc`.
   - **Mappings (Availability Zones):**
     - Tại **`ap-southeast-1a`**: Chọn Subnet `fabric-insp-fw-1a` (`10.70.10.0/24`).
     - Tại **`ap-southeast-1b`**: Chọn Subnet `fabric-insp-fw-1b` (`10.70.11.0/24`).
     - *(Lưu ý: Không chọn các subnet tgw hoặc gwlbe)*.
5. **Listeners and routing:**
   - Default action: Chọn **Forward to** -> Chọn Target group: `fabric-suricata-tg`.
6. **Tags:**
   - Key: `Project` | Value: `aws-eks-secure-network-fabric`
   - Key: `Environment` | Value: `prod`
7. Nhấp nút cam **Create load balancer** ở cuối trang.
8. Trạng thái của GWLB sẽ chuyển từ `Provisioning` sang **`Active`** (Mất khoảng 2-3 phút).

---

### Bước 3: Xác Nhận Trạng Thái Health Check Của Cụm Tường Lửa
1. Tại menu bên trái EC2 Console, chọn lại **Target Groups**.
2. Nhấp vào tên `fabric-suricata-tg`.
3. Chọn tab **Targets** ở nửa dưới màn hình:
   - Quan sát bảng **Registered targets**:
     - `fabric-suricata-1a` | Port: 6081 | Health status: **`healthy`** (Dấu tích xanh).
     - `fabric-suricata-1b` | Port: 6081 | Health status: **`healthy`** (Dấu tích xanh).
   - Nếu hiển thị `unhealthy`, hãy kiểm tra lại xem tiến trình Python HTTP server port 80 trên instances có đang chạy hay không và Security Group có cho phép Inbound 80 hay chưa.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái của GWLB và sức khỏe của các targets:
```bash
# 1. Kiểm tra trạng thái GWLB
aws elbv2 describe-load-balancers --region ap-southeast-1 --names fabric-gwlb \
  --query 'LoadBalancers[0].{Name:LoadBalancerName,State:State.Code,VpcId:VpcId,Type:Type,Arn:LoadBalancerArn}' \
  --output table

# 2. Kiểm tra Target Health của 2 Suricata appliances
TG_ARN=$(aws elbv2 describe-target-groups --region ap-southeast-1 --names fabric-suricata-tg --query 'TargetGroups[0].TargetGroupArn' --output text)
aws elbv2 describe-target-health --region ap-southeast-1 --target-group-arn $TG_ARN \
  --query 'TargetHealthDescriptions[*].{InstanceId:Target.Id,Port:Target.Port,HealthStatus:TargetHealth.State,Reason:TargetHealth.Reason}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa GWLB và Target Group khi cần hoàn tác:
```bash
gwlb_arn=$(aws elbv2 describe-load-balancers --region ap-southeast-1 --names fabric-gwlb --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null)
if [ -n "$gwlb_arn" ] && [ "$gwlb_arn" != "None" ]; then
  aws elbv2 delete-load-balancer --region ap-southeast-1 --load-balancer-arn $gwlb_arn
fi

tg_arn=$(aws elbv2 describe-target-groups --region ap-southeast-1 --names fabric-suricata-tg --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)
if [ -n "$tg_arn" ] && [ "$tg_arn" != "None" ]; then
  aws elbv2 delete-target-group --region ap-southeast-1 --target-group-arn $tg_arn
fi
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/05-gwlb/02-gwlb-healthy.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Target Group `fabric-suricata-tg` sử dụng protocol `GENEVE` trên port `6081`.
- [ ] Cả 2 máy chủ Suricata đều đạt trạng thái `healthy` trên cổng kiểm tra HTTP 80.
- [ ] Gateway Load Balancer `fabric-gwlb` đạt trạng thái `active` trên 2 Subnets `fabric-insp-fw-1a/b`.
- [ ] Listener tự động forward toàn bộ lưu lượng sang `fabric-suricata-tg`.
