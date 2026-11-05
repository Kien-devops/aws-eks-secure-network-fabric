# 05.03 — Khởi Tạo VPC Endpoint Service & GWLB Endpoints (GWLBe)

> **Trạng thái:** Hướng dẫn thực hành chi tiết trên AWS Management Console (Console-first).  
> **Áp dụng cho:** Xuất bản dịch vụ kiểm tra an ninh mạng qua PrivateLink và tạo các điểm cuối GWLBe trong Inspection VPC.

---

## 1. Mục Tiêu Kỹ Thuật

- Khởi tạo **VPC Endpoint Service** trỏ vào Gateway Load Balancer `fabric-gwlb`.
- Cấu hình quyền truy cập (Acceptance required: `false` để tự động chấp nhận kết nối nội bộ).
- Khởi tạo 2 **GWLB Endpoints (GWLBe)** đặt tại các Subnet chuyên dụng `fabric-inspection-gwlbe-1a` và `fabric-inspection-gwlbe-1b` trong Inspection VPC.
- Thu thập ID của 2 điểm cuối (`gwlbe-a-id` và `gwlbe-b-id`) để chuẩn bị cho bước cấu hình bảng định tuyến.

---

## 2. Các Bước Thực Hiện Chi Tiết Trên AWS Console

### Bước 1: Tạo VPC Endpoint Service
1. Mở dịch vụ **VPC Console** tại Region Singapore (`ap-southeast-1`).
2. Tại menu bên trái, cuộn xuống mục **Virtual private network (VPN)** hoặc nhóm **Endpoints** -> Chọn **Endpoint services**.
3. Nhấp nút cam **Create endpoint service**:
   - **Name tag:** `fabric-gwlb-endpoint-service`.
   - **Load balancer type:** Chọn **Gateway**.
   - **Available load balancers:** Chọn `fabric-gwlb`.
   - **Require acceptance for endpoint:** **BỎ TÍCH** (`No` - Để tự động chấp nhận kết nối từ chính tài khoản).
   - **Supported IP address types:** `IPv4`.
4. Nhấp **Create**.
5. Ghi lại giá trị **Service name** (ví dụ: `com.amazonaws.vpce.ap-southeast-1.vpce-svc-0123456789abcdef0`).

---

### Bước 2: Tạo GWLB Endpoints (GWLBe) Trong Inspection VPC
1. Tại menu bên trái của VPC Console, chọn **Endpoints** -> Nhấp nút cam **Create endpoint**.
2. **Endpoint settings:**
   - **Name tag:** `fabric-inspection-gwlbe`
   - **Service category:** Chọn radio button **Other endpoint services**.
   - **Service name:** Dán chuỗi `Service name` vừa sao chép ở Bước 1 -> Nhấp nút **Verify service** (xác nhận hiển thị màu xanh lá: `Service name verified`).
3. **VPC:**
   - Chọn `fabric-inspection-vpc`.
4. **Subnets:**
   - Chọn cả 2 Availability Zones:
     - `ap-southeast-1a`: Chọn subnet `fabric-inspection-gwlbe-1a`.
     - `ap-southeast-1b`: Chọn subnet `fabric-inspection-gwlbe-1b`.
5. **Tags:** `Project` = `aws-eks-secure-network-fabric`.
6. Nhấp nút cam **Create endpoint**.

---

## 3. Xác Minh (Verification)

Kiểm tra trạng thái của các điểm cuối GWLB Endpoint qua AWS CLI:
```bash
aws ec2 describe-vpc-endpoints \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-inspection-gwlbe" \
  --query 'VpcEndpoints[*].{Id:VpcEndpointId,State:State,Subnets:SubnetIds,Type:VpcEndpointType}' \
  --output table
```
> Kết quả: `State = available`, `Type = GatewayLoadBalancer`.

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Endpoint Service được liên kết chính xác với `fabric-gwlb`.
- [ ] 2 điểm cuối GWLBe chuyển sang trạng thái `available` tại đúng 2 Subnet GWLBe của AZ-a và AZ-b.
