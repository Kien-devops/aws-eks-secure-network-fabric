# 04.02 — Cấu Hình Route 53 Private Hosted Zone Cho Nội Bộ Fabric

> **Mã bài lab:** `04.02`  
> **Trạng thái:** `RUNTIME_PASS`  
> **Thời gian dự kiến:** 25 phút  
> **Chi phí ước tính:** ~$0.50 USD / hosted zone / tháng  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành các bài lab tại [Module 02](../02-ha-tang-mang-co-ban/README.md) và [04.01](01-database-and-cache-setup.md).
- Cả `fabric-edge-vpc` và `fabric-core-vpc` đều đã bật 2 thuộc tính: `Enable DNS resolution` và `Enable DNS hostnames`.
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
        "route53:CreateHostedZone",
        "route53:AssociateVPCWithHostedZone",
        "route53:DisassociateVPCFromHostedZone",
        "route53:ChangeResourceRecordSets",
        "route53:GetHostedZone",
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets",
        "route53:DeleteHostedZone"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Route 53 Private Hosted Zone (PHZ) tính phí $0.50 USD/tháng cho mỗi zone và $0.40 USD cho mỗi 1 triệu truy vấn DNS đầu tiên.
- **Cảnh báo liên kết đa VPC (Cross-VPC Association):** PHZ bắt buộc phải được liên kết (associated) đồng thời với cả **Edge VPC** và **Core VPC**. Nếu quên liên kết một trong hai, các Pod tại Edge EKS sẽ không thể phân giải được tên miền nội bộ của Core (`core.fabric.internal`, `db.fabric.internal`), dẫn đến lỗi `Host unresolved` hoặc `Connection refused`.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo Route 53 Private Hosted Zone (`fabric.internal`)
1. Trên thanh tìm kiếm AWS Console, nhập `Route 53` và chọn dịch vụ **Route 53**.
2. Tại menu điều hướng bên trái, chọn **Hosted zones**.
3. Nhấp vào nút cam **Create hosted zone** ở góc trên bên phải.
4. **Hosted zone configuration:**
   - **Domain name:** Nhập `fabric.internal`.
   - **Description:** Nhập `Private DNS hosted zone for AWS EKS Secure Network Fabric internal resolution`.
   - **Type:** Chọn **Private hosted zone**.
5. **VPCs to associate with the hosted zone:**
   - **Region:** Chọn **Asia Pacific (Singapore) (ap-southeast-1)**.
   - **VPC ID:** Tìm và chọn `fabric-edge-vpc`.
6. Nhấp nút cam **Create hosted zone** ở cuối trang.

---

### Bước 2: Liên Kết Thêm Core VPC (`fabric-core-vpc`) Vào Hosted Zone
1. Sau khi zone được khởi tạo thành công, hệ thống chuyển đến trang chi tiết của `fabric.internal`.
2. Mở tab **Hosted zone details** (hoặc cuộn xuống mục **VPCs**).
3. Nhấp nút **Associate VPC**:
   - **Region:** Chọn **Asia Pacific (Singapore) (ap-southeast-1)**.
   - **VPC ID:** Chọn `fabric-core-vpc`.
4. Nhấp **Associate VPC**.
5. Xác nhận trên bảng danh sách VPCs hiển thị cả 2 dòng:
   - `ap-southeast-1` — `fabric-edge-vpc`
   - `ap-southeast-1` — `fabric-core-vpc`

---

### Bước 3: Tạo Các Bản Ghi DNS Nội Bộ Cho Database & Redis (Internal DNS Records)
Tại trang chi tiết `fabric.internal`, nhấp nút cam **Create record** để cấu hình đầy đủ các endpoint đọc/ghi phục vụ kiến trúc High Availability:

1. **Bản ghi Cơ sở dữ liệu Writer (`db.fabric.internal`):**
   - **Record name:** Nhập `db` (Tên đầy đủ: `db.fabric.internal`).
   - **Record type:** Chọn **CNAME**.
   - **Value:** Dán Writer Endpoint của Aurora PostgreSQL (`fabric-core-db.cluster-c1ky6i8iomcn.ap-southeast-1.rds.amazonaws.com`).
   - **TTL (seconds):** Nhập `60`.
   - **Routing policy:** Chọn **Simple routing**.
   - Nhấp **Create records**.

2. **Bản ghi Cơ sở dữ liệu Reader/Replica (`dbr.fabric.internal`):**
   - Nhấp **Create record**.
   - **Record name:** Nhập `dbr` (Tên đầy đủ: `dbr.fabric.internal`).
   - **Record type:** Chọn **CNAME**.
   - **Value:** Dán Reader Endpoint của Aurora PostgreSQL (`fabric-core-db.cluster-ro-c1ky6i8iomcn.ap-southeast-1.rds.amazonaws.com`).
   - **TTL (seconds):** Nhập `60`.
   - **Routing policy:** Chọn **Simple routing**.
   - Nhấp **Create records**.

3. **Bản ghi Bộ đệm Cache Primary (`redis.fabric.internal`):**
   - Nhấp **Create record**.
   - **Record name:** Nhập `redis` (Tên đầy đủ: `redis.fabric.internal`).
   - **Record type:** Chọn **CNAME**.
   - **Value:** Dán Primary Endpoint của ElastiCache Redis Cluster (`master.fabric-core-redis.qspmd1.apse1.cache.amazonaws.com`). *(Lưu ý: Chỉ nhập FQDN hostname, không kèm port `:6379`)*.
   - **TTL:** `60`.
   - **Routing policy:** Chọn **Simple routing**.
   - Nhấp **Create records**.

4. **Bản ghi Bộ đệm Cache Replica (`redis-ro.fabric.internal`):**
   - Nhấp **Create record**.
   - **Record name:** Nhập `redis-ro` (Tên đầy đủ: `redis-ro.fabric.internal`).
   - **Record type:** Chọn **CNAME**.
   - **Value:** Dán Reader Endpoint của ElastiCache Redis Cluster (`replica.fabric-core-redis.qspmd1.apse1.cache.amazonaws.com`).
   - **TTL:** `60`.
   - **Routing policy:** Chọn **Simple routing**.
   - Nhấp **Create records**.

5. **Bản ghi Dịch vụ Core Ingress (`core.fabric.internal`):**
   - *(Bản ghi này sẽ được hoàn thiện hoặc cập nhật trỏ tới DNS Name của Internal NLB trong bài lab 04.03)*.
   - Chưa tạo record giả. Khi 04.03 đã có NLB DNS thật, quay lại **Create record** → `core` → CNAME → DNS NLB thật → TTL 60 → Create records.

> **Lưu ý bảo mật & TLS:** Ứng dụng dùng hostname AWS gốc hoặc SAN tương ứng khi kết nối Aurora/Redis với xác thực chứng chỉ đầy đủ. CNAME đóng vai trò service discovery nội bộ. Với `core.fabric.internal`, cấp chứng chỉ backend có SAN đúng tên này ở lab 04.03.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh danh sách VPC liên kết và các bản ghi DNS:
```bash
# 1. Tìm Hosted Zone ID của fabric.internal
ZONE_ID=$(aws route53 list-hosted-zones-by-name --dns-name fabric.internal --query 'HostedZones[0].Id' --output text)
echo "Hosted Zone ID: $ZONE_ID"

# 2. Kiểm tra danh sách VPCs liên kết với Hosted Zone
aws route53 get-hosted-zone --id $ZONE_ID \
  --query '{Name:HostedZone.Name,VPCs:VPCs[*].VPCId}' \
  --output table

# 3. Liệt kê toàn bộ Resource Record Sets trong fabric.internal
aws route53 list-resource-record-sets --hosted-zone-id $ZONE_ID \
  --query 'ResourceRecordSets[*].{Name:Name,Type:Type,TTL:TTL,Value:ResourceRecords[0].Value}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Để xóa Private Hosted Zone:
1. Xóa toàn bộ các bản ghi DNS thủ công đã tạo (ngoại trừ SOA và NS mặc định).
2. Gỡ bỏ association của `fabric-core-vpc`.
3. Xóa Private Hosted Zone qua Console hoặc CLI:
   ```bash
   ZONE_ID=$(aws route53 list-hosted-zones-by-name --dns-name fabric.internal --query 'HostedZones[0].Id' --output text)
   aws route53 delete-hosted-zone --id $ZONE_ID
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/04-workloads/02-route53-phz.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Private Hosted Zone `fabric.internal` được tạo với cấu hình loại Private.
- [x] Cả 2 VPCs `fabric-edge-vpc` và `fabric-core-vpc` đều được liên kết hợp lệ.
- [x] Các bản ghi `db.fabric.internal`, `dbr.fabric.internal`, `redis.fabric.internal` và `redis-ro.fabric.internal` trỏ chính xác về Endpoint tương ứng.
- [x] Hệ thống phân giải DNS nội bộ sẵn sàng phục vụ cho các Pod trong 2 cụm EKS.
