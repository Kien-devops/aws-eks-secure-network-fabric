# 05.03 — Tạo Endpoint Service & Hai Zonal GWLB Endpoints Riêng Biệt (AZ-a, AZ-b)

> **Mã bài lab:** `05.03`  
> **Trạng thái:** `COMPLETED`  
> **Thời gian dự kiến:** 30 phút  
> **Chi phí ước tính:** ~$0.01/giờ/endpoint (~$0.02 USD / giờ cho 2 zonal endpoints)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Subnets: `fabric-insp-gwlbe-1a`, `fabric-insp-gwlbe-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [05.02](02-gateway-load-balancer-and-target-group.md). Gateway Load Balancer `fabric-gwlb` đang ở trạng thái `active` với 2 targets `healthy`.
- Subnets `fabric-insp-gwlbe-1a` (`10.70.1.0/28`) và `fabric-insp-gwlbe-1b` (`10.70.1.16/28`) sẵn sàng.
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
        "ec2:CreateVpcEndpointServiceConfiguration",
        "ec2:DescribeVpcEndpointServiceConfigurations",
        "ec2:DeleteVpcEndpointServiceConfigurations",
        "ec2:CreateVpcEndpoint",
        "ec2:DescribeVpcEndpoints",
        "ec2:DeleteVpcEndpoints",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Mỗi GWLB Endpoint tính phí ~$0.01 USD/giờ tại Singapore.
- **Cảnh báo Kiến Trúc Zonal GWLBe (Cực kỳ quan trọng):** GWLB Endpoint là tài nguyên mang tính **cục bộ theo từng Vùng sẵn sàng (Zonal Resource)**. Bạn **KHÔNG THỂ TẠO 1 ENDPOINT CHỨA 2 SUBNET KHÁC NHAU** trên bảng định tuyến. Bắt buộc phải tạo **HAI VPC ENDPOINTS RIÊNG BIỆT**:
  - `fabric-gwlbe-1a` đặt trong subnet `fabric-insp-gwlbe-1a` (AZ-a).
  - `fabric-gwlbe-1b` đặt trong subnet `fabric-insp-gwlbe-1b` (AZ-b).
  Điều này cho phép bảng định tuyến của từng AZ trỏ chính xác về Endpoint tương ứng trong cùng AZ, bảo toàn 100% tính đối xứng của luồng gói tin!

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Khởi Tạo VPC Endpoint Service Cho GWLB
Mở **VPC Console** tại Singapore `ap-southeast-1`:
1. Tại menu điều hướng bên trái, cuộn xuống nhóm **Virtual private cloud** -> Chọn **Endpoint services**.
2. Nhấp vào nút cam **Create endpoint service** ở góc trên bên phải.
3. **Endpoint service settings:**
   - **Name tag:** Nhập `fabric-gwlb-endpoint-service`.
   - **Load balancer type:** Chọn **Gateway**.
   - **Available load balancers:** Tìm và chọn `fabric-gwlb`.
   - **Additional settings:**
     - **Require acceptance for endpoint:** **BỎ CHỌN (Disable)** (Để các endpoint trong VPC tự động được chấp nhận mà không cần thao tác approve thủ công).
     - **Supported IP address types:** Chọn **IPv4**.
   - **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`.
4. Nhấp nút cam **Create endpoint service** ở cuối trang.
5. Tại trang chi tiết Endpoint Service vừa tạo:
   - Sao chép giá trị của trường **Service name** (Có định dạng: `com.amazonaws.vpce.ap-southeast-1.vpce-svc-0xxxxxxxxxxxxxxxxx`).

---

### Bước 2: Tạo GWLB Endpoint Thứ Nhất Tại AZ-a (`fabric-gwlbe-1a`)
Tại menu điều hướng bên trái VPC Console -> Chọn **Endpoints**:
1. Nhấp vào nút cam **Create endpoint** ở góc trên bên phải.
2. **Endpoint settings:**
   - **Name tag:** Nhập `fabric-gwlbe-1a`.
   - **Service category:** Chọn **Other endpoint services**.
   - **Service name:** Dán chuỗi `Service name` vừa sao chép ở Bước 1.
   - Nhấp nút **Verify service** (Xác nhận hiển thị thông báo tích xanh: `Service name verified`).
3. **VPC:**
   - Chọn `fabric-inspection-vpc` (`10.70.0.0/16`).
4. **Subnets (Chọn duy nhất 1 AZ và 1 Subnet):**
   - Tìm dòng Availability Zone **`ap-southeast-1a`**:
     - Đánh dấu tích vào checkbox.
     - Tại ô chọn Subnet, chọn chính xác: **`fabric-insp-gwlbe-1a`** (`10.70.1.0/28`).
   - *(Tuyệt đối không chọn AZ-b tại bước này)*.
5. **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`; Key: `AZ` | Value: `ap-southeast-1a`.
6. Nhấp nút cam **Create endpoint** ở cuối trang.
7. Ghi nhận lại **Endpoint ID** của AZ-a (Ví dụ: `vpce-0aaa1111222233334`).

---

### Bước 3: Tạo GWLB Endpoint Thứ Hai Tại AZ-b (`fabric-gwlbe-1b`)
Tại danh sách **Endpoints**, tiếp tục nhấp nút cam **Create endpoint**:
1. **Endpoint settings:**
   - **Name tag:** Nhập `fabric-gwlbe-1b`.
   - **Service category:** Chọn **Other endpoint services**.
   - **Service name:** Dán lại cùng chuỗi `Service name` của GWLB Endpoint Service.
   - Nhấp nút **Verify service**.
2. **VPC:**
   - Chọn `fabric-inspection-vpc`.
3. **Subnets (Chọn duy nhất AZ-b):**
   - Tìm dòng Availability Zone **`ap-southeast-1b`**:
     - Đánh dấu tích vào checkbox.
     - Tại ô chọn Subnet, chọn chính xác: **`fabric-insp-gwlbe-1b`** (`10.70.1.16/28`).
   - *(Bỏ chọn AZ-a)*.
4. **Tags:** Key: `Project` | Value: `aws-eks-secure-network-fabric`; Key: `AZ` | Value: `ap-southeast-1b`.
5. Nhấp nút cam **Create endpoint**.
6. Ghi nhận lại **Endpoint ID** của AZ-b (Ví dụ: `vpce-0bbb5555666677778`).
7. Quan sát danh sách Endpoints: Đợi khoảng 1-2 phút cho đến khi cả 2 endpoints `fabric-gwlbe-1a` và `fabric-gwlbe-1b` chuyển sang trạng thái xanh **`Available`**.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trạng thái cả 2 Zonal GWLB Endpoints và các Subnet liên kết:
```bash
# 1. Liệt kê 2 GWLB Endpoints trong Inspection VPC
INSP_VPC_ID=$(aws ec2 describe-vpcs --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-inspection-vpc" --query 'Vpcs[0].VpcId' --output text)

aws ec2 describe-vpc-endpoints --region ap-southeast-1 \
  --filters "Name=vpc-id,Values=$INSP_VPC_ID" "Name=vpc-endpoint-type,Values=GatewayLoadBalancer" \
  --query 'VpcEndpoints[*].{Name:Tags[?Key==`Name`].Value | [0],Id:VpcEndpointId,State:State,SubnetId:SubnetIds[0]}' \
  --output table
```

**Bằng chứng runtime thực tế:**
```text
-----------------------------------------------------------------------------------------
|                                  DescribeVpcEndpoints                                 |
+-----------------------+-------------------+------------+------------------------------+
|          Id           |       Name        |   State    |           SubnetId           |
+-----------------------+-------------------+------------+------------------------------+
|  vpce-0f16354ca5bb55c14 | fabric-gwlbe-1a | available  |  subnet-0aebf9d83c8118058    |
|  vpce-0b48242bff7b44479 | fabric-gwlbe-1b | available  |  subnet-0a1a561fe99bcc9fd    |
+-----------------------+-------------------+------------+------------------------------+
```

```bash
# 2. Kiểm tra chi tiết subnet và AZ của từng Endpoint
aws ec2 describe-subnets --region ap-southeast-1 \
  --subnet-ids subnet-0aebf9d83c8118058 subnet-0a1a561fe99bcc9fd \
  --query 'Subnets[*].{SubnetId:SubnetId,Name:Tags[?Key==`Name`].Value | [0],AZ:AvailabilityZone,Cidr:CidrBlock}' \
  --output table
```

**Bằng chứng runtime thực tế:**
```text
-----------------------------------------------------------------------------------------
|                                    DescribeSubnets                                    |
+-----------------+----------------+-----------------------+----------------------------+
|       AZ        |     Cidr       |         Name          |          SubnetId          |
+-----------------+----------------+-----------------------+----------------------------+
|  ap-southeast-1a|  10.70.1.0/28  |  fabric-insp-gwlbe-1a |  subnet-0aebf9d83c8118058   |
|  ap-southeast-1b|  10.70.1.16/28 |  fabric-insp-gwlbe-1b |  subnet-0a1a561fe99bcc9fd   |
+-----------------+----------------+-----------------------+----------------------------+
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Xóa 2 GWLB Endpoints và Endpoint Service:
```bash
# Xóa các GWLB Endpoints
for ep_id in $(aws ec2 describe-vpc-endpoints --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-gwlbe-*" --query 'VpcEndpoints[*].VpcEndpointId' --output text); do
  aws ec2 delete-vpc-endpoints --region ap-southeast-1 --vpc-endpoint-ids $ep_id
done

# Xóa Endpoint Service
svc_id=$(aws ec2 describe-vpc-endpoint-service-configurations --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-gwlb-endpoint-service" --query 'ServiceConfigurations[0].ServiceId' --output text 2>/dev/null)
if [ -n "$svc_id" ] && [ "$svc_id" != "None" ]; then
  aws ec2 delete-vpc-endpoint-service-configurations --region ap-southeast-1 --service-ids $svc_id
fi
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/05-gwlb/03-zonal-gwlbe-active.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] VPC Endpoint Service cho GWLB được tạo thành công với cấu hình `AcceptanceRequired = false`.
- [x] Cả 2 Zonal GWLB Endpoints (`fabric-gwlbe-1a` và `fabric-gwlbe-1b`) đều ở trạng thái `available`.
- [x] `fabric-gwlbe-1a` gắn duy nhất vào subnet `fabric-insp-gwlbe-1a` trong `ap-southeast-1a`.
- [x] `fabric-gwlbe-1b` gắn duy nhất vào subnet `fabric-insp-gwlbe-1b` trong `ap-southeast-1b`.
