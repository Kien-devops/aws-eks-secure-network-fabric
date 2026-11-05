# Module 02: Thiết Lập Nền Tảng Hạ Tầng Mạng Đa VPC & Transit Gateway

## 1. Mục Tiêu Kỹ Thuật
- **Mục tiêu:**
  - Khởi tạo 4 Virtual Private Clouds (VPCs) tại Singapore (`ap-southeast-1`):
    1. `fabric-edge-vpc` (`10.40.0.0/16`)
    2. `fabric-core-vpc` (`10.50.0.0/16`)
    3. `fabric-inspection-vpc` (`10.70.0.0/16`)
    4. `fabric-egress-vpc` (`10.80.0.0/16`)
  - Thiết kế đầy đủ subnets theo từng AZ (`ap-southeast-1a` và `ap-southeast-1b`).
  - Khởi tạo AWS Transit Gateway (`fabric-tgw`), tắt chế độ tự động gán & tự động quảng bá route (`default-route-table-association = disable`, `default-route-table-propagation = disable`).
  - Tạo 5 bảng định tuyến riêng biệt trên TGW: `edge-rt`, `core-rt`, `inspection-rt`, `egress-rt`, `dev-rt`.
  - Bật tính năng **Appliance Mode** trên Inspection VPC Attachment.
  - Bật VPC Flow Logs đẩy về CloudWatch Log Groups.

---

## 2. Các Bước Thực Hiện Chi Tiết

### Bước 1: Khởi tạo 4 VPCs & Bật DNS Hostnames
Triển khai qua AWS Console hoặc AWS CLI (`aws-api-mcp/call_aws`):
```bash
# Edge VPC
aws ec2 create-vpc --cidr-block 10.40.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=fabric-edge-vpc}]' --region ap-southeast-1
# Core VPC
aws ec2 create-vpc --cidr-block 10.50.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=fabric-core-vpc}]' --region ap-southeast-1
# Inspection VPC
aws ec2 create-vpc --cidr-block 10.70.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=fabric-inspection-vpc}]' --region ap-southeast-1
# Egress VPC
aws ec2 create-vpc --cidr-block 10.80.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=fabric-egress-vpc}]' --region ap-southeast-1
```
*Bắt buộc bật `enableDnsHostnames` và `enableDnsSupport` cho cả 4 VPCs.*

### Bước 2: Tạo Subnets Chuyên Dụng Từng AZ
- **Edge VPC:**
  - Public Subnets (ALB): `10.40.0.0/24` (1a), `10.40.1.0/24` (1b)
  - Private Node Subnets: `10.40.10.0/22` (1a), `10.40.14.0/22` (1b)
  - TGW Attachment Subnets: `10.40.250.0/28` (1a), `10.40.250.16/28` (1b)
- **Core VPC:**
  - Private Node Subnets: `10.50.10.0/22` (1a), `10.50.14.0/22` (1b)
  - Private Data Subnets: `10.50.20.0/24` (1a), `10.50.21.0/24` (1b)
  - TGW Attachment Subnets: `10.50.250.0/28` (1a), `10.50.250.16/28` (1b)
- **Inspection VPC:**
  - TGW Attachment Subnets: `10.70.0.0/28` (1a), `10.70.0.16/28` (1b)
  - GWLBe Subnets: `10.70.1.0/28` (1a), `10.70.1.16/28` (1b)
  - Firewall EC2 Subnets: `10.70.10.0/24` (1a), `10.70.11.0/24` (1b)
- **Egress VPC:**
  - TGW Attachment Subnets: `10.80.0.0/28` (1a), `10.80.0.16/28` (1b)
  - Firewall Endpoint Subnets: `10.80.1.0/28` (1a), `10.80.1.16/28` (1b)
  - Public NAT Subnets: `10.80.10.0/24` (1a), `10.80.11.0/24` (1b)

### Bước 3: Khởi tạo AWS Transit Gateway & Bảng Định Tuyến
1. Khởi tạo TGW với tùy chọn:
   - `AmazonSideAsn`: `64512`
   - `AutoAcceptSharedAttachments`: `disable`
   - `DefaultRouteTableAssociation`: `disable`
   - `DefaultRouteTablePropagation`: `disable`
2. Tạo 5 TGW Route Tables:
   - `fabric-tgw-rt-edge`
   - `fabric-tgw-rt-core`
   - `fabric-tgw-rt-inspection`
   - `fabric-tgw-rt-egress`
   - `fabric-tgw-rt-dev`

### Bước 4: Tạo TGW VPC Attachments & Bật Appliance Mode
1. Tạo VPC Attachment cho từng VPC vào các Subnet TGW tương ứng.
2. **Đặc biệt với Inspection VPC Attachment:**
   ```bash
   aws ec2 modify-transit-gateway-vpc-attachment \
     --transit-gateway-attachment-id <inspection-attachment-id> \
     --options "ApplianceModeSupport=enable" \
     --region ap-southeast-1
   ```
3. Associate từng attachment vào đúng bảng định tuyến TGW tương ứng.

---

## 3. Xác Minh (Verification)
Kiểm tra Appliance Mode đã được kích hoạt trên Inspection Attachment:
```bash
aws ec2 describe-transit-gateway-vpc-attachments \
  --transit-gateway-attachment-ids <inspection-attachment-id> \
  --region ap-southeast-1 \
  --query 'TransitGatewayVpcAttachments[0].Options.ApplianceModeSupport' \
  --output text
```
> Kết quả mong đợi: `enable`

---

## 4. Tiêu Chí Nghiệm Thu (Acceptance Criteria)
- [ ] Cả 4 VPCs và toàn bộ Subnets được khởi tạo chuẩn xác tại `ap-southeast-1a` và `ap-southeast-1b`.
- [ ] TGW tắt hoàn toàn default association và propagation.
- [ ] Inspection Attachment xác nhận `ApplianceModeSupport = enable`.
- [ ] VPC Flow Logs đã được kích hoạt đẩy về CloudWatch Logs.
