# 02.04 — Cấu Hình Bảng Định Tuyến Subnet (Subnet Route Tables Chaining)

> **Mã bài lab:** `02.04`  
> **Trạng thái:** `RUNTIME_PASS`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD (Bảng định tuyến VPC Route Tables hoàn toàn miễn phí)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — AZs: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn thành toàn bộ các bài lab [02.01](01-four-vpcs-and-subnets.md), [02.02](02-transit-gateway-setup.md), và [02.03](03-tgw-route-tables-and-attachments.md).
- 4 VPCs, 28 subnets, Transit Gateway và 4 TGW Attachments đã ở trạng thái `available`.
- Đăng nhập AWS Management Console tại Region Singapore `ap-southeast-1`.

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
        "ec2:CreateRouteTable",
        "ec2:AssociateRouteTable",
        "ec2:CreateRoute",
        "ec2:ReplaceRoute",
        "ec2:DeleteRoute",
        "ec2:DescribeRouteTables",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo, An Toàn & Nguyên Tắc Định Tuyến Chuyên Sâu (Routing Architecture Principles)

- **Chi phí:** $0.00 USD (Bảng định tuyến VPC Route Tables hoàn toàn miễn phí).
- **Phân biệt TGW Subnets giữa Spoke VPCs và Transit/Service VPCs:**
  - **Spoke TGW Subnets (`fabric-edge-tgw-rt`, `fabric-core-tgw-rt`):** Chỉ chứa duy nhất tuyến nội bộ `local`. Khi lưu lượng từ TGW đi vào Spoke VPC, ENI attachment sẽ chuyển tiếp trực tiếp tới workload đích trong cùng VPC theo tuyến `local`. Không được cấu hình route trỏ ngược lại TGW để triệt tiêu hoàn toàn nguy cơ routing loop.
  - **Transit / Inspection / Egress TGW Subnets (`fabric-insp-tgw-rt`, `fabric-egress-tgw-rt`):** Đóng vai trò là cổng đón luồng (Ingress Steering) của chuỗi kiểm tra an ninh (Service Chaining). Trong kiến trúc hoàn chỉnh, các route table này **không dừng lại ở local** mà sẽ chứa các tuyến chuyển hướng (ví dụ: trỏ tới GWLB Endpoint trong Module 05, hoặc AWS Network Firewall Endpoint / NAT Gateway trong Module 06). Trong phạm vi nền tảng của Module 02, do các endpoints này chưa được khởi tạo, route tables tạm thời duy trì tuyến nền tảng để tránh cấu hình lỗi hướng vào tài nguyên chưa tồn tại.
- **Bắt buộc Return Route từ Centralized Egress Public Subnet (`fabric-egress-public-rt`):**
  - Khi NAT Gateway nhận lưu lượng từ các Spoke VPC và dịch địa chỉ (SNAT) đi ra Internet qua IGW, gói tin phản hồi từ Internet về NAT Gateway sẽ mang IP đích là Spoke Private IP (`10.40.x.x` hoặc `10.50.x.x`).
  - Nếu `fabric-egress-public-rt` chỉ có tuyến `0.0.0.0/0 -> IGW`, NAT Gateway sẽ tra bảng định tuyến và đẩy nhầm gói tin trả về Internet qua IGW (bị IGW drop ngay lập tức).
  - Do đó, **bắt buộc phải cấu hình tuyến trả về `10.40.0.0/16` và `10.50.0.0/16` trỏ tới `fabric-tgw` ngay trong `fabric-egress-public-rt`**.
- **Bảo Vệ & Phản Hồi Cho Data Subnet (`fabric-core-data-rt`):**
  - Tuyệt đối **KHÔNG** thêm route `0.0.0.0/0` ra Internet (cô lập 100% tầng lưu trữ dữ liệu khỏi Internet).
  - Giao tiếp chuẩn giữa các Pod nghiệp vụ Core EKS (`order-service`, `inventory-service`) và Aurora/Redis diễn ra nội bộ cùng VPC qua tuyến `10.50.0.0/16 -> local`.
  - Bổ sung tuyến riêng tư `10.40.0.0/16 -> fabric-tgw` để đảm bảo đường phản hồi hai chiều an toàn khi có các luồng truy vấn quản trị hoặc kết nối riêng tư hợp lệ từ Edge VPC, đồng thời kiểm soát chặt chẽ bằng Security Group (chỉ mở cổng 5432/6379 cho đối tượng được phép).

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Tạo & Cấu Hình Bảng Định Tuyến Cho Edge VPC (`fabric-edge-vpc`)
Mở **VPC Console** -> Menu bên trái chọn **Route tables** -> Nhấp nút cam **Create route table**.

#### 1. Tạo `fabric-edge-public-rt` (Dành cho ALB Ingress Subnets):
1. **Name:** Nhập `fabric-edge-public-rt` (`rtb-0c5a68767a6fe2926`).
2. **VPC:** Chọn `fabric-edge-vpc`.
3. Nhấp **Create route table**.
4. Chuyển sang tab **Subnet associations** -> Nhấp nút **Edit subnet associations**:
   - Tích chọn 2 subnets: `fabric-edge-public-1a` và `fabric-edge-public-1b`.
   - Nhấp **Save associations**.
5. Chuyển sang tab **Routes** -> Nhấp nút **Edit routes**:
   - Tuyến 1: `10.40.0.0/16` -> Target: `local` (mặc định có sẵn).
   - Nhấp **Add route**:
     - Destination: `0.0.0.0/0` -> Target: Chọn **Internet Gateway** -> Chọn `fabric-edge-igw`.
   - Nhấp **Add route**:
     - Destination: `10.50.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Save changes**.

#### 2. Tạo `fabric-edge-private-rt` (Dành cho EKS Worker Nodes & VPCE):
1. Nhấp **Create route table**.
2. **Name:** Nhập `fabric-edge-private-rt` (`rtb-00cd096fd0d4a2615`) | **VPC:** Chọn `fabric-edge-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn 4 subnets: `fabric-edge-nodes-1a`, `fabric-edge-nodes-1b`, `fabric-edge-vpce-1a`, `fabric-edge-vpce-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes** -> **Edit routes**:
   - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Save changes**.

#### 3. Tạo `fabric-edge-tgw-rt` (Dành riêng cho TGW Attachment ENIs):
1. Nhấp **Create route table**.
2. **Name:** Nhập `fabric-edge-tgw-rt` (`rtb-0e6e7436bb74cdf73`) | **VPC:** Chọn `fabric-edge-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn: `fabric-edge-tgw-1a` và `fabric-edge-tgw-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes**: Giữ nguyên duy nhất tuyến `10.40.0.0/16` -> `local`.

---

### Bước 2: Tạo & Cấu Hình Bảng Định Tuyến Cho Core VPC (`fabric-core-vpc`)
Tại màn hình **Route tables** -> Nhấp nút cam **Create route table**.

#### 1. Tạo `fabric-core-private-rt` (Dành cho Core EKS Nodes & VPCE):
1. **Name:** Nhập `fabric-core-private-rt` (`rtb-00ac268964554cc7e`).
2. **VPC:** Chọn `fabric-core-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn 4 subnets: `fabric-core-nodes-1a`, `fabric-core-nodes-1b`, `fabric-core-vpce-1a`, `fabric-core-vpce-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes** -> **Edit routes**:
   - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
   - Nhấp **Save changes**.

#### 2. Tạo `fabric-core-data-rt` (Dành cho Aurora PostgreSQL & ElastiCache Redis):
1. Nhấp **Create route table**.
2. **Name:** Nhập `fabric-core-data-rt` (`rtb-0df8c388148a51656`) | **VPC:** Chọn `fabric-core-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn 2 subnets: `fabric-core-data-1a` và `fabric-core-data-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes** -> **Edit routes**:
   - Tuyến 1: `10.50.0.0/16` -> Target: `local` (Được kế thừa mặc định, phục vụ kết nối trực tiếp từ Core EKS Nodes).
   - Nhấp **Add route**:
     - Destination: `10.40.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
     - *(Lý do: Đảm bảo đường phản hồi hai chiều riêng tư nếu có kết nối trực tiếp hoặc tác vụ quản trị từ Edge VPC qua TGW mà không cần mở Internet)*.
   - Nhấp **Save changes**. (Tuyệt đối không có tuyến `0.0.0.0/0` ra Internet).

#### 3. Tạo `fabric-core-tgw-rt` (Dành cho TGW Attachment ENIs):
1. Nhấp **Create route table**.
2. **Name:** Nhập `fabric-core-tgw-rt` (`rtb-047cf904c6c014554`) | **VPC:** Chọn `fabric-core-vpc`.
3. Nhấp **Create route table**.
4. Tab **Subnet associations** -> **Edit subnet associations**:
   - Tích chọn: `fabric-core-tgw-1a` và `fabric-core-tgw-1b`.
   - Nhấp **Save associations**.
5. Tab **Routes**: Giữ nguyên chỉ có tuyến `10.50.0.0/16` -> `local`.

---

### Bước 3: Tạo Bảng Định Tuyến Theo Vùng (Zonal RTBs) Cho Inspection VPC (`fabric-inspection-vpc`)

Nhằm bảo đảm tính đối xứng và không đi chéo Vùng sẵn sàng (Cross-AZ traffic), các subnet kết nối TGW trong Inspection VPC được tách riêng theo từng AZ để trỏ chính xác về GWLB Endpoint của AZ đó:

1. **Tạo `fabric-insp-tgw-rt-1a` (Dành cho TGW ENI tại AZ-a):**
   - **Name:** Nhập `fabric-insp-tgw-rt-1a` (`rtb-0b04448561b80d486`) | **VPC:** Chọn `fabric-inspection-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gán với `fabric-insp-tgw-1a` (`subnet-0e260eae20eea3ccb`).
   - *(Lưu ý: Tuyến `0.0.0.0/0` trỏ tới `GWLBE-1a` sẽ được kích hoạt trong Module 05 khi GWLB Endpoint hoàn tất triển khai)*.
2. **Tạo `fabric-insp-tgw-rt-1b` (Dành cho TGW ENI tại AZ-b):**
   - **Name:** Nhập `fabric-insp-tgw-rt-1b` (`rtb-026ce1b95a394d8c1`) | **VPC:** Chọn `fabric-inspection-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gán với `fabric-insp-tgw-1b` (`subnet-0a1481ce7d8302538`).
   - *(Lưu ý: Tuyến `0.0.0.0/0` trỏ tới `GWLBE-1b` sẽ được kích hoạt trong Module 05)*.
3. **Tạo `fabric-insp-gwlbe-rt` (Bảng định tuyến cho GWLB Endpoints):**
   - **Name:** Nhập `fabric-insp-gwlbe-rt` (`rtb-0378f50d79f1ed01f`) | **VPC:** Chọn `fabric-inspection-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gán với `fabric-insp-gwlbe-1a` và `fabric-insp-gwlbe-1b`.
   - Tab **Routes** -> **Edit routes**:
     - Tuyến 1: `10.70.0.0/16` -> Target: `local` (Mặc định).
     - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
     - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
     - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
     - *(Lý do: Sau khi gói tin được giải mã và kiểm duyệt qua GWLB/Suricata, GWLB Endpoint sẽ chuyển tiếp gói tin quay trở lại TGW để tới Spoke đích hoặc Egress VPC)*.
     - Nhấp **Save changes**.
4. **Tạo `fabric-insp-fw-rt` (Dành cho Subnet chứa máy chủ Suricata EC2):**
   - **Name:** Nhập `fabric-insp-fw-rt` (`rtb-00b06850e681ef0e6`) | **VPC:** Chọn `fabric-inspection-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gán với `fabric-insp-fw-1a` và `fabric-insp-fw-1b`.
   - Tab **Routes**: Giữ nguyên duy nhất `10.70.0.0/16` -> `local` (Do kiến trúc GWLB One-Arm nhận và trả gói tin bọc GENEVE UDP 6081 trực tiếp với GWLB qua giao diện nội bộ).

---

### Bước 4: Tạo Bảng Định Tuyến Theo Vùng (Zonal RTBs) Cho Centralized Egress VPC (`fabric-egress-vpc`)

Tương tự Inspection VPC, các TGW Attachment subnets tại Egress VPC được tách thành 2 bảng định tuyến theo từng AZ để chuyển lưu lượng ra đúng cổng NAT Gateway của AZ tương ứng:

1. **Tạo `fabric-egress-tgw-rt-1a` (Dành cho TGW ENI tại AZ-a):**
   - **Name:** Nhập `fabric-egress-tgw-rt-1a` (`rtb-0e44e9ee6af736348`) | **VPC:** Chọn `fabric-egress-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gán với `fabric-egress-tgw-1a` (`subnet-0a9b70d43770f1e86`).
   - *(Lưu ý: Tuyến `0.0.0.0/0` trỏ tới Network Firewall Endpoint AZ-a (`vpce-*`) sẽ được cấu hình trong Module 06 để kiểm tra sâu gói tin trước khi ra NAT Gateway)*.
2. **Tạo `fabric-egress-tgw-rt-1b` (Dành cho TGW ENI tại AZ-b):**
   - **Name:** Nhập `fabric-egress-tgw-rt-1b` (`rtb-0f49dc7e1ab7a050d`) | **VPC:** Chọn `fabric-egress-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gán với `fabric-egress-tgw-1b` (`subnet-0b0653845a52c4f75`).
   - *(Lưu ý: Tuyến `0.0.0.0/0` trỏ tới Network Firewall Endpoint AZ-b (`vpce-*`) sẽ được cấu hình trong Module 06)*.
3. **Tạo `fabric-egress-public-rt` (Dành cho NAT Gateways & IGW):**
   - **Name:** Nhập `fabric-egress-public-rt` (`rtb-0c759f9192847ad8b`) | **VPC:** Chọn `fabric-egress-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gán với `fabric-egress-public-1a` và `fabric-egress-public-1b`.
   - Tab **Routes** -> **Edit routes**:
     - Tuyến 1: `10.80.0.0/16` -> Target: `local` (Mặc định).
     - Nhấp **Add route**: Destination: `0.0.0.0/0` -> Target: Chọn **Internet Gateway** -> Chọn `fabric-egress-igw`.
     - Nhấp **Add route**: Destination: `10.40.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
     - Nhấp **Add route**: Destination: `10.50.0.0/16` -> Target: Chọn **Transit Gateway** -> Chọn `fabric-tgw`.
     - *(Lý do: Đảm bảo NAT Gateway khi nhận gói tin phản hồi từ Internet có thể định tuyến ngược về Edge VPC và Core VPC qua TGW, ngăn ngừa triệt để tình trạng Blackhole / Asymmetric Drop tại IGW)*.
     - Nhấp **Save changes**.
4. **Tạo `fabric-egress-fw-rt` (Dành cho Network Firewall Subnets):**
   - **Name:** Nhập `fabric-egress-fw-rt` (`rtb-0f71ea39c116e5857`) | **VPC:** Chọn `fabric-egress-vpc`.
   - Nhấp **Create route table**.
   - Tab **Subnet associations**: Gán với `fabric-egress-fw-1a` và `fabric-egress-fw-1b`.
   - Tab **Routes**: Giữ nguyên `10.80.0.0/16` -> `local` (Sẽ cấu hình trỏ tới NAT Gateway sau khi triển khai Network Firewall tại Module 06).

---

### Bảng Ánh Xạ Phân Pha Định Tuyến Hạ Tầng (Phased Routing Dependency Matrix)

| Bảng Định Tuyến (Route Table) | Đích (Destination) | Đích Đến Kế Tiếp (Next Hop) | Giai Đoạn Triển Khai | Mục Đích Kỹ Thuật |
|---|---|---|:---:|---|
| `fabric-edge-public-rt` | `0.0.0.0/0` | `fabric-edge-igw` | **Module 02** | Cho phép ALB Ingress nhận lưu lượng Internet từ bên ngoài |
| `fabric-edge-public-rt` | `10.50.0.0/16` | `fabric-tgw` | **Module 02** | Chuyển tiếp lưu lượng gọi sang Core VPC |
| `fabric-edge-private-rt` | `0.0.0.0/0` | `fabric-tgw` | **Module 02** | Đẩy lưu lượng ra ngoài qua Centralized Egress |
| `fabric-edge-private-rt` | `10.50.0.0/16` | `fabric-tgw` | **Module 02** | Kết nối nội bộ Đông - Tây tới Core EKS |
| `fabric-core-private-rt` | `0.0.0.0/0` | `fabric-tgw` | **Module 02** | Đẩy lưu lượng ra ngoài qua Centralized Egress |
| `fabric-core-private-rt` | `10.40.0.0/16` | `fabric-tgw` | **Module 02** | Phản hồi lưu lượng Đông - Tây về Edge VPC |
| `fabric-core-data-rt` | `10.40.0.0/16` | `fabric-tgw` | **Module 02** | Phản hồi lưu lượng riêng tư tới Edge VPC (nếu có truy vấn DB trực tiếp) |
| `fabric-insp-gwlbe-rt` | `10.40.0.0/16` | `fabric-tgw` | **Module 02** | Đẩy gói tin đã qua kiểm tra Suricata về Edge VPC qua TGW |
| `fabric-insp-gwlbe-rt` | `10.50.0.0/16` | `fabric-tgw` | **Module 02** | Đẩy gói tin đã qua kiểm tra Suricata về Core VPC qua TGW |
| `fabric-insp-gwlbe-rt` | `0.0.0.0/0` | `fabric-tgw` | **Module 02** | Đẩy gói tin outbound đã kiểm tra sang Egress VPC qua TGW |
| `fabric-egress-public-rt` | `0.0.0.0/0` | `fabric-egress-igw` | **Module 02** | Đẩy lưu lượng từ NAT Gateway ra Internet |
| `fabric-egress-public-rt` | `10.40.0.0/16` | `fabric-tgw` | **Module 02** | Đường về từ NAT Gateway trả về Edge VPC qua TGW |
| `fabric-egress-public-rt` | `10.50.0.0/16` | `fabric-tgw` | **Module 02** | Đường về từ NAT Gateway trả về Core VPC qua TGW |
| `fabric-insp-tgw-rt-1a` | `0.0.0.0/0` | GWLB Endpoint 1a (`vpce-*`) | *Module 05* | Bắt buộc lưu lượng TGW tại AZ-a đi vào GWLB Endpoint AZ-a |
| `fabric-insp-tgw-rt-1b` | `0.0.0.0/0` | GWLB Endpoint 1b (`vpce-*`) | *Module 05* | Bắt buộc lưu lượng TGW tại AZ-b đi vào GWLB Endpoint AZ-b |
| `fabric-egress-tgw-rt-1a` | `0.0.0.0/0` | Network Firewall Endpoint 1a (`vpce-*`) | *Module 06* | Bắt buộc lưu lượng từ TGW tại AZ-a đi vào NFW Endpoint AZ-a kiểm tra an ninh |
| `fabric-egress-tgw-rt-1b` | `0.0.0.0/0` | Network Firewall Endpoint 1b (`vpce-*`) | *Module 06* | Bắt buộc lưu lượng từ TGW tại AZ-b đi vào NFW Endpoint AZ-b kiểm tra an ninh |
| `fabric-egress-fw-rt` | `0.0.0.0/0` | NAT Gateway 1a/1b (`nat-*`) | *Module 06* | Chuyển tiếp lưu lượng sau kiểm tra an ninh ra NAT Gateway theo từng AZ |
| `fabric-egress-fw-rt` | `10.40.0.0/16`, `10.50.0.0/16` | `fabric-tgw` | *Module 06* | Trả lưu lượng phản hồi từ NFW về Spoke VPC qua TGW |
| `fabric-egress-public-rt` (Phase 06) | `10.40.0.0/16`, `10.50.0.0/16` | Network Firewall Endpoint (`vpce-*`) | *Module 06* | Lưu lượng phản hồi từ NAT Gateway bắt buộc qua NFW Endpoint trước khi về TGW |

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái Route Tables và các Subnet Associations tương ứng:
```bash
# 1. Liệt kê toàn bộ 14 Route Tables đã tạo kèm VPC ID và số lượng Subnet liên kết
aws ec2 describe-route-tables --region ap-southeast-1 \
  --filters "Name=tag:Project,Values=aws-eks-secure-network-fabric" \
  --query 'RouteTables[*].{Name:Tags[?Key==`Name`].Value | [0],Id:RouteTableId,VpcId:VpcId,AssocCount:length(Associations)}' \
  --output table

# 2. Kiểm tra chi tiết tuyến đường trong fabric-insp-gwlbe-rt
aws ec2 describe-route-tables --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-insp-gwlbe-rt" \
  --query 'RouteTables[0].Routes[*].{Destination:DestinationCidrBlock,Target:TransitGatewayId || GatewayId || InstanceId,State:State}' \
  --output table

# 3. Kiểm tra chi tiết tuyến đường trong fabric-egress-public-rt
aws ec2 describe-route-tables --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-egress-public-rt" \
  --query 'RouteTables[0].Routes[*].{Destination:DestinationCidrBlock,Target:TransitGatewayId || GatewayId || InstanceId,State:State}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp định tuyến sai, xóa các route cụ thể hoặc gỡ association khỏi subnet:
```bash
# Xóa một route không mong muốn
aws ec2 delete-route --region ap-southeast-1 --route-table-id <rtb-id> --destination-cidr-block <cidr>

# Gỡ bỏ association khỏi subnet nếu gán nhầm
aws ec2 disassociate-route-table --region ap-southeast-1 --association-id <rtb-assoc-id>
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`evidence/02-network/04-subnet-route-tables.json`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [x] Toàn bộ 28 subnets được gán đúng 14 Route Tables tương ứng (0 subnet nào rơi vào Main Route Table mặc định).
- [x] Subnet Node của Edge EKS và Core EKS đều trỏ `0.0.0.0/0` về `fabric-tgw`.
- [x] Subnet Data của Core VPC không có tuyến ra Internet `0.0.0.0/0` (cô lập tuyệt đối), nhưng có tuyến riêng tư `10.40.0.0/16` về `fabric-tgw` để hỗ trợ phản hồi hai chiều cho Edge VPC.
- [x] Subnet TGW Attachment trong Spoke VPCs (Edge & Core) chỉ có duy nhất tuyến `local` (chống loop).
- [x] Subnet TGW Attachment trong Inspection và Egress VPCs được tách Zonal theo từng AZ (`1a` và `1b`) độc lập để chuẩn bị cho việc liên kết GWLBe và NAT Gateway cục bộ của từng AZ.
- [x] Route Table của GWLB Endpoints (`fabric-insp-gwlbe-rt`) có đủ các tuyến trả về `10.40.0.0/16`, `10.50.0.0/16`, và `0.0.0.0/0` qua `fabric-tgw`.
- [x] Public Subnet của Edge VPC trỏ `0.0.0.0/0` về `fabric-edge-igw` và `10.50.0.0/16` về `fabric-tgw`.
- [x] Public Subnet của Egress VPC trỏ `0.0.0.0/0` về `fabric-egress-igw`, đồng thời chứa đầy đủ 2 tuyến trả về Spoke CIDRs (`10.40.0.0/16`, `10.50.0.0/16` -> `fabric-tgw`) để tránh drop luồng phản hồi từ NAT Gateway.

### Trạng Thái Thực Thi Runtime (All 14 Route Tables & 28 Subnet Associations Completed)
- **Thời gian hoàn thành:** `2026-11-05T17:35:00Z`
- **Công cụ thực thi:** MCP `aws-api-mcp/call_aws`
- **14 Route Tables Đã Tạo & Cấu Hình Thành Công:**
  - **Edge VPC (3 RTBs):** `fabric-edge-public-rt` (`rtb-0c5a68767a6fe2926`), `fabric-edge-private-rt` (`rtb-00cd096fd0d4a2615`), `fabric-edge-tgw-rt` (`rtb-0e6e7436bb74cdf73`).
  - **Core VPC (3 RTBs):** `fabric-core-private-rt` (`rtb-00ac268964554cc7e`), `fabric-core-data-rt` (`rtb-0df8c388148a51656`), `fabric-core-tgw-rt` (`rtb-047cf904c6c014554`).
  - **Inspection VPC (4 RTBs):** `fabric-insp-tgw-rt-1a` (`rtb-0b04448561b80d486`), `fabric-insp-tgw-rt-1b` (`rtb-026ce1b95a394d8c1`), `fabric-insp-gwlbe-rt` (`rtb-0378f50d79f1ed01f`), `fabric-insp-fw-rt` (`rtb-00b06850e681ef0e6`).
  - **Egress VPC (4 RTBs):** `fabric-egress-tgw-rt-1a` (`rtb-0e44e9ee6af736348`), `fabric-egress-tgw-rt-1b` (`rtb-0f49dc7e1ab7a050d`), `fabric-egress-public-rt` (`rtb-0c759f9192847ad8b`), `fabric-egress-fw-rt` (`rtb-0f71ea39c116e5857`).
- **File bằng chứng:** `evidence/02-network/04-subnet-route-tables.json`
