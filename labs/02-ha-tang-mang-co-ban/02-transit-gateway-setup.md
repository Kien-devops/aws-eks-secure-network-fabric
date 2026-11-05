# 02.02 — Cấu Hình AWS Transit Gateway (TGW) Tắt Mặc Định Propagation

> **Mã bài lab:** `02.02`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 20 phút  
> **Chi phí ước tính:** ~$0.07 USD/giờ cho Transit Gateway tại Singapore (`ap-southeast-1`)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành bài lab [02.01 — Khởi Tạo 4 VPCs & Hệ Thống Subnets](01-four-vpcs-and-subnets.md).
- Hiểu rõ nguyên tắc phân đoạn miền định tuyến (Route Domain Segmentation) và triết lý fail-closed an ninh mạng.
- Đang mở phiên AWS Console tại Singapore (`ap-southeast-1`).

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
        "ec2:CreateTransitGateway",
        "ec2:DescribeTransitGateways",
        "ec2:CreateTags",
        "ec2:ModifyTransitGateway",
        "ec2:DeleteTransitGateway"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** AWS Transit Gateway tính phí khoảng $0.07 USD/giờ ($1.68 USD/ngày). Cần theo dõi sát sao trên AWS Budgets để không vượt ngưỡng $50.00 USD.
- **Cảnh báo kiến trúc an ninh sống còn:** **BẮT BUỘC BỎ CHỌN (DISABLE)** cả hai tùy chọn:
  1. `Default route table association`
  2. `Default route table propagation`
  Nếu để mặc định (enable), mọi VPC kết nối vào TGW sẽ tự động nhìn thấy và giao tiếp với nhau mà không qua tường lửa, phá vỡ hoàn toàn thiết kế an ninh của dự án.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Mở Bảng Điều Khiển Transit Gateway
1. Đăng nhập vào **AWS Management Console**, đảm bảo góc trên bên phải hiển thị vùng **Singapore `ap-southeast-1`**.
2. Trên thanh tìm kiếm chính, nhập `Transit Gateway` hoặc `VPC`.
3. Tại menu điều hướng bên trái của VPC Console, cuộn xuống nhóm **Transit Gateways**.
4. Nhấp chọn mục **Transit Gateways**.
5. Nhấp vào nút cam **Create transit gateway** ở góc trên bên phải.

### Bước 2: Thiết Lập Tham Số Cốt Lõi Cho Transit Gateway
Tại giao diện **Create transit gateway**, điền chính xác các trường sau:

1. **General configuration:**
   - **Name tag:** Nhập `fabric-tgw`.
   - **Description:** Nhập `Central Transit Gateway for AWS EKS Secure Network Fabric Singapore`.
   - **Amazon side Autonomous System Number (ASN):** Nhập `64512` (Sử dụng dải Private ASN 64512–65534 theo khuyến nghị của RFC 6996).

2. **Cấu hình tùy chọn nâng cao (Advanced configuration - Cực kỳ quan trọng):**
   - **DNS support:** Chọn checkbox **Enable** (Cho phép phân giải tên miền riêng giữa các VPC kết nối qua TGW).
   - **VPN ECMP support:** Chọn checkbox **Enable** (Hỗ trợ Equal-Cost Multi-Path).
   - **Default route table association:** **BỎ CHỌN (Disable)**.
   - **Default route table propagation:** **BỎ CHỌN (Disable)**.
   - **Auto accept shared attachments:** Chọn **Disable** (Ngăn chặn việc tự động nhận attachment từ các tài khoản khác).
   - **Multicast support:** Để mặc định **Disable**.
   - **CIDR blocks:** Để trống (Không sử dụng TGW CIDR).

3. **Tags:**
   - Nhấp **Add new tag**:
     - Key: `Project` | Value: `aws-eks-secure-network-fabric`
   - Nhấp **Add new tag**:
     - Key: `Environment` | Value: `prod`
   - Nhấp **Add new tag**:
     - Key: `ManagedBy` | Value: `console-lab`

4. Nhấp nút cam **Create transit gateway** ở cuối trang.

### Bước 3: Theo Dõi Quá Trình Khởi Tạo & Kiểm Tra Trạng Thái
1. Hệ thống sẽ chuyển hướng về bảng danh sách **Transit Gateways**.
2. Tìm dòng có Name là `fabric-tgw`.
3. Quan sát cột **State**: Trạng thái ban đầu sẽ là `pending`. Quá trình này AWS mất khoảng 2 đến 4 phút để cấp phát các thành phần định tuyến phân tán trong 2 AZs.
4. Nhấn nút làm mới (Refresh icon hình mũi tên vòng) ở góc trên bảng danh sách cho đến khi cột **State** chuyển sang màu xanh: **`available`**.
5. Nhấp vào ID của `fabric-tgw` để mở trang chi tiết:
   - Chọn tab **Details**:
     - Xác nhận `Amazon side ASN`: `64512`.
     - Xác nhận `Default route table association`: `False`.
     - Xác nhận `Default route table propagation`: `False`.
     - Xác nhận `DNS support`: `True`.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái TGW qua AWS CLI hoặc MCP Server (`aws-api-mcp/call_aws`):
```bash
# Kiểm tra chi tiết cấu hình và trạng thái của fabric-tgw
aws ec2 describe-transit-gateways --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-tgw" \
  --query 'TransitGateways[*].{Id:TransitGatewayId,State:State,ASN:Options.AmazonSideAsn,DefaultAssoc:Options.DefaultRouteTableAssociation,DefaultProp:Options.DefaultRouteTablePropagation,DnsSupport:Options.DnsSupport}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Nếu cấu hình sai ASN hoặc lỡ bật Default Association/Propagation, cần xóa TGW và tạo lại:
1. Tại VPC Console -> **Transit Gateways** -> Chọn checkbox trước `fabric-tgw`.
2. Nhấp menu **Actions** -> Chọn **Delete transit gateway**.
3. Nhập từ khóa `delete` vào ô xác nhận -> Nhấp **Delete**.
4. Hoặc thực thi qua CLI:
   ```bash
   tgw_id=$(aws ec2 describe-transit-gateways --region ap-southeast-1 --filters "Name=tag:Name,Values=fabric-tgw" --query 'TransitGateways[0].TransitGatewayId' --output text)
   if [ "$tgw_id" != "None" ] && [ -n "$tgw_id" ]; then
     aws ec2 delete-transit-gateway --region ap-southeast-1 --transit-gateway-id $tgw_id
   fi
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/02-tgw-status.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Transit Gateway `fabric-tgw` đạt trạng thái `available` tại Singapore `ap-southeast-1`.
- [ ] `AmazonSideAsn` hiển thị chính xác giá trị `64512`.
- [ ] `DefaultRouteTableAssociation` có giá trị `disable`.
- [ ] `DefaultRouteTablePropagation` có giá trị `disable`.
- [ ] `DnsSupport` có giá trị `enable`.
