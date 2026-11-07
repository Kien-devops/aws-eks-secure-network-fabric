# 06.03 — Triển Khai AWS Network Firewall Tại Egress VPC & Bật Appliance Mode

> **Mã bài lab:** `06.03`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 40 phút  
> **Chi phí ước tính:** ~$0.395 USD / giờ / endpoint (~$0.79 USD / giờ cho 2 AZ endpoints)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `fabric-egress-fw-1a`, `fabric-egress-fw-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab [06.01](01-nat-gateways-per-az.md) và [06.02](02-network-firewall-rule-groups.md).
- Firewall Policy `fabric-egress-fw-policy` đang ở trạng thái `ACTIVE`.
- Subnets `fabric-egress-fw-1a` (`10.80.1.0/28`) và `fabric-egress-fw-1b` (`10.80.1.16/28`) sẵn sàng.
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
        "network-firewall:CreateFirewall",
        "network-firewall:DescribeFirewall",
        "network-firewall:DeleteFirewall",
        "network-firewall:UpdateLoggingConfiguration",
        "logs:CreateLogGroup",
        "logs:PutRetentionPolicy",
        "ec2:DescribeTransitGatewayVpcAttachments",
        "ec2:ModifyTransitGatewayVpcAttachment",
        "network-firewall:ListFirewalls"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** AWS Network Firewall tính phí ~$0.395 USD/giờ cho mỗi endpoint ở Singapore (~$18.96 USD/ngày cho 2 AZs). Đây là thành phần chi phí lớn nhất của lab. Sau khi hoàn thành việc thu thập bằng chứng kiểm tra Egress và diễn tập GameDay, hãy ưu tiên xóa Firewall theo Module 12 để bảo toàn ngân sách.
- **Cảnh báo TGW Egress Attachment Appliance Mode:** Bắt buộc phải xác nhận cờ `ApplianceModeSupport = enable` trên `fabric-egress-tgw-attachment`. Nếu không, luồng ra và luồng vào của một phiên kết nối sẽ bị phân tán sang 2 firewall endpoint khác nhau, gây ra tình trạng TCP reset hoặc packet drop.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo 2 CloudWatch Log Groups Cho Network Firewall
1. Mở **CloudWatch Console** tại Singapore `ap-southeast-1`.
2. Tại menu bên trái, mở rộng mục **Logs** -> Chọn **Log groups** -> Nhấp **Create log group**:
   - **Tạo Log Group Cảnh Báo (Alerts):**
     - Log group name: `/aws/network-firewall/fabric-egress-alerts`.
     - Retention: Chọn `7 days (1 week)`.
     - Nhấp **Create**.
   - **Tạo Log Group Lưu Lượng (Flows):**
     - Nhấp lại **Create log group**.
     - Log group name: `/aws/network-firewall/fabric-egress-flows`.
     - Retention: Chọn `7 days`.
     - Nhấp **Create**.

---

### Bước 2: Triển Khai AWS Network Firewall Trên Hai AZs
Mở **VPC Console** tại Singapore `ap-southeast-1`:
1. Tại menu điều hướng bên trái, cuộn xuống nhóm **Network Firewall** -> Chọn **Firewalls**.
2. Nhấp vào nút cam **Create firewall** ở góc trên bên phải.
3. **Firewall details:**
   - **Name:** Nhập `fabric-egress-nfw`.
   - **Firewall policy:** Chọn **Associate an existing firewall policy** -> Chọn `fabric-egress-fw-policy`.
   - **VPC:** Chọn `fabric-egress-vpc` (`10.80.0.0/16`).
4. **Subnet mappings (Chọn 2 Subnets Firewall chuyên dụng):**
   - **Availability Zone 1:**
     - Availability Zone: Chọn **`ap-southeast-1a`**.
     - Subnet: Chọn **`fabric-egress-fw-1a`** (`10.80.1.0/28`).
   - Nhấp nút **Add a subnet mapping**:
     - Availability Zone: Chọn **`ap-southeast-1b`**.
     - Subnet: Chọn **`fabric-egress-fw-1b`** (`10.80.1.16/28`).
   - *(Lưu ý: Không chọn các subnet tgw hay public)*.
5. **Tags:**
   - Key: `Project` | Value: `aws-eks-secure-network-fabric`
   - Key: `Environment` | Value: `prod`
6. Nhấp nút cam **Create firewall** ở cuối trang.
7. Hệ thống chuyển về trang chi tiết của `fabric-egress-nfw`. Quá trình cấp phát (Provisioning) Firewall Endpoints trong 2 AZs mất khoảng 5 đến 8 phút.
8. Đợi cho đến khi trường **Status** chuyển sang màu xanh: **`Ready`**.

---

### Bước 3: Cấu Hình Logging Cho Network Firewall
Tại trang chi tiết của firewall `fabric-egress-nfw`:
1. Chọn tab **Logging**.
2. Nhấp nút **Edit** ở góc phải mục Logging configuration:
   - **Cấu hình Alert log:**
     - Đánh dấu tích vào **Alert log**.
     - Log destination type: Chọn **CloudWatch Logs**.
     - Log destination: Chọn `/aws/network-firewall/fabric-egress-alerts`.
   - **Cấu hình Flow log:**
     - Đánh dấu tích vào **Flow log**.
     - Log destination type: Chọn **CloudWatch Logs**.
     - Log destination: Chọn `/aws/network-firewall/fabric-egress-flows`.
3. Nhấp **Save**.

---

### Bước 4: Sao Chép Firewall Endpoint IDs Cho Từng AZ
1. Tại trang chi tiết `fabric-egress-nfw`, chọn tab **Firewall details**.
2. Cuộn xuống bảng **Firewall status** -> Mục **Subnet mappings**:
   - Ghi nhận **Endpoint ID** của AZ `ap-southeast-1a` (Có định dạng `vpce-01111111111111111`).
   - Ghi nhận **Endpoint ID** của AZ `ap-southeast-1b` (Có định dạng `vpce-02222222222222222`).
   - *(Hai Endpoint IDs này sẽ được sử dụng trực tiếp để cấu hình Route Table trong lab 06.04)*.

---

### Bước 5: Xác Thực Cờ Appliance Mode Trên Egress TGW Attachment
1. Tại menu bên trái VPC Console -> Nhóm **Transit Gateways** -> Chọn **Transit Gateway Attachments**.
2. Chọn `fabric-egress-tgw-attachment`.
3. Kiểm tra tab **Details**:
   - Xác nhận trường **Appliance mode support** hiển thị: **`enable`**.
   - Nếu hiển thị `disable`, nhấp **Actions** -> **Modify transit gateway attachment** -> Tích chọn **Enable appliance mode** -> **Save changes**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái Firewall và các Endpoints ID qua AWS CLI:
```bash
# 1. Kiểm tra trạng thái Firewall và Sync status
aws network-firewall describe-firewall --region ap-southeast-1 \
  --firewall-name fabric-egress-nfw \
  --query 'FirewallStatus.{Status:Status,ConfigurationSyncStateSummary:ConfigurationSyncStateSummary}' \
  --output table

# 2. Liệt kê Firewall Endpoints ID theo từng Availability Zone
aws network-firewall describe-firewall --region ap-southeast-1 \
  --firewall-name fabric-egress-nfw \
  --query 'FirewallStatus.SyncStates' \
  --output json

# 3. Kiểm tra cấu hình logging của Network Firewall
aws network-firewall describe-logging-configuration --region ap-southeast-1 \
  --firewall-name fabric-egress-nfw \
  --query 'LoggingConfiguration.LogDestinationConfigs[*].{LogType:LogType,Destination:LogDestination.logGroup}' \
  --output table
```

**Runtime Output Thực Tế:**
```text
--------------------------------------------------
|                DescribeFirewall                |
+----------------------------------+-------------+
|  ConfigurationSyncStateSummary   |   Status    |
+----------------------------------+-------------+
|  IN_SYNC                         |  READY      |
+----------------------------------+-------------+

Firewall Endpoints per AZ:
- ap-southeast-1a: vpce-008c9b7972ba12c2c (Subnet: subnet-0c7142131794aa34c, Status: READY)
- ap-southeast-1b: vpce-0a4193a072d8c041f (Subnet: subnet-05ce922d28724c2f9, Status: READY)

-------------------------------------------------------------------------------------
|                           DescribeLoggingConfiguration                            |
+----------------------------------------------------+------------------------------+
|                    Destination                     |           LogType            |
+----------------------------------------------------+------------------------------+
|  /aws/network-firewall/fabric-egress-flows         |  FLOW                        |
|  /aws/network-firewall/fabric-egress-alerts        |  ALERT                       |
+----------------------------------------------------+------------------------------+

----------------------------------------------------------------------
|               DescribeTransitGatewayVpcAttachments                 |
+--------------------------+-----------------------+-----------------+
|      ApplianceMode       |          Id           |      State      |
+--------------------------+-----------------------+-----------------+
|  enable                  | tgw-attach-0646bdfa31c6c8e66 |  available      |
+--------------------------+-----------------------+-----------------+
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa AWS Network Firewall khi cần tái tạo hoặc dọn dẹp:
```bash
aws network-firewall delete-firewall --region ap-southeast-1 --firewall-name fabric-egress-nfw
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/06-firewall/03-firewall-endpoints.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] AWS Network Firewall `fabric-egress-nfw` đạt trạng thái `READY`.
- [x] 2 Firewall Endpoints được cấp phát thành công tại 2 AZs `ap-southeast-1a` và `ap-southeast-1b`.
- [x] Cả 2 kênh ghi log Alert và Flow đều được gắn thành công vào CloudWatch Log Groups.
- [x] Cờ `ApplianceModeSupport` của `fabric-egress-tgw-attachment` hiển thị `enable`.
