# 09.04 — Kiểm Chứng Đường Truyền Logic Bằng AWS VPC Reachability Analyzer

> **Mã bài lab:** `09.04`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 35 phút  
> **Chi phí ước tính:** ~$0.10 USD (Tính cước per analysis run của Reachability Analyzer)  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn tất kết nối Transit Gateway và các bảng định tuyến phân đoạn tại [Module 02](../02-ha-tang-mang-co-ban/03-tgw-route-tables-and-attachments.md).
- Đã triển khai cụm GWLB và Suricata IDS/IPS tại [Module 05](../05-gwlb-suricata-ids-ips/02-gateway-load-balancer-and-target-group.md).
- Cụm Core Internal NLB `fabric-core-internal-nlb` đang hoạt động tại [Module 04](../04-phan-bo-workloads/03-core-internal-nlb.md).
- Giao diện mạng (ENI) của Worker Node trong Edge VPC và ENI của Core NLB đã được ghi nhận ID.
- Đang mở phiên AWS Management Console tại Singapore `ap-southeast-1`.

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để tạo đường dẫn và phân tích khả năng tiếp cận mạng:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInsightsPath",
        "ec2:DeleteNetworkInsightsPath",
        "ec2:DescribeNetworkInsightsPaths",
        "ec2:StartNetworkInsightsAnalysis",
        "ec2:DescribeNetworkInsightsAnalyses",
        "ec2:GetNetworkInsightsAnalysisResults",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSecurityGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** AWS tính phí **$0.10 USD cho mỗi lần chạy phân tích (Analysis run)**. Một lần tạo đường dẫn (Path) là miễn phí.
- **Bản chất công nghệ Formal Reasoning:** Reachability Analyzer **hoàn toàn không gửi gói tin thực (Synthetic packet) qua mạng**, mà phân tích toán học dựa trên cấu hình khai báo (Declarative configuration) của Route Tables, Security Groups, NACLs, TGW Attachments và GWLB Endpoints. Do đó, thao tác này tuyệt đối không gây suy giảm hiệu năng, không làm gián đoạn lưu lượng production, và không làm kích hoạt báo động sai trên IDS/IPS.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Mở Reachability Analyzer Trên VPC Console
1. Đăng nhập vào **AWS Management Console** tại Region Singapore (`ap-southeast-1`).
2. Mở dịch vụ **VPC**.
3. Tại thanh menu bên trái, cuộn xuống nhóm **Network analysis** -> Nhấp vào **Reachability Analyzer**.
4. Nhấp nút màu cam **Create and analyze path** ở góc trên bên phải.

---

### Bước 2: Khai Báo Điểm Đầu Và Điểm Cuối Đường Dẫn (Path Configuration)
Trong trang cấu hình *Create and analyze path*:

1. **Path settings:**
   - **Name tag:** `fabric-edge-to-core-nlb-path`
2. **Source configuration:**
   - **Source type:** Chọn **`Network Interfaces`**
   - **Source:** Nhấp vào danh sách dropdown và tìm chọn ENI của Worker Node Edge EKS trong subnet private `fabric-edge-priv-1a` (Ví dụ: `eni-0123456789abcdef0`).
   - **Source IP address (Optional):** Nhập địa chỉ IP riêng của Pod hoặc Node: `10.40.10.15`
3. **Destination configuration:**
   - **Destination type:** Chọn **`Network Interfaces`**
   - **Destination:** Chọn ENI của Core Internal NLB nằm trong subnet private `fabric-core-priv-1a` (Ví dụ: `eni-0fedcba9876543210`).
   - **Destination IP address (Optional):** Nhập IP nội bộ của NLB: `10.50.20.25`
4. **Protocol and port:**
   - **Protocol:** Chọn radio button **`TCP`**
   - **Destination port:** Nhập `443`
5. **Tags:**
   - Key: `Project` | Value: `aws-eks-secure-network-fabric`
   - Key: `Environment` | Value: `dev`
   - Key: `PathType` | Value: `East-West-Inspection`

---

### Bước 3: Khởi Động Phân Tích (Analyze Path)
1. Kiểm tra lại toàn bộ thông số đã nhập.
2. Nhấp nút màu cam **Create and analyze path** ở cuối trang.
3. Hệ thống sẽ tạo đối tượng Path `nip-xxxxxxxxxxxxxxxxx` và lập tức khởi chạy một phiên phân tích `nia-yyyyyyyyyyyyyyyyy`.
4. Quan sát thanh trạng thái chuyển từ `Running` sang **`Completed`** (thường mất khoảng 30 đến 45 giây).

---

### Bước 4: Kiểm Tra Biểu Đồ Và Từng Chặng Mạng (Hop-by-Hop Verification)
1. Khi phân tích hoàn thành, quan sát nhãn trạng thái tổng thể:
   - **Status:** `Completed`
   - **Reachability status:** Hiển thị biểu tượng tích xanh: **`Reachable`** (Thông suốt 100%).
2. Cuộn xuống phần **Visual explanation** (Sơ đồ trực quan) và **Detailed path**:
   - Xác nhận chuỗi các chặng mạng logic diễn ra đúng chuẩn thiết kế East-West Inspection:
     - **Chặng 1:** `Source ENI (10.40.10.15)`
     - **Chặng 2:** `Edge Worker Security Group` (Kiểm tra egress port 443 -> Allowed)
     - **Chặng 3:** `Edge Private Route Table (rtb-xxx)` (Định tuyến `0.0.0.0/0` hoặc `10.50.0.0/16` trỏ về TGW Attachment)
     - **Chặng 4:** `Edge TGW Attachment (tgw-attach-xxx)`
     - **Chặng 5:** `Transit Gateway Route Table (fabric-tgw-edge-rt)` (Định tuyến `10.50.0.0/16` trỏ sang Inspection VPC Attachment)
     - **Chặng 6:** `Inspection TGW Attachment (tgw-attach-yyy)`
     - **Chặng 7:** `Inspection Subnet Route Table` (Định tuyến trỏ vào GWLB Endpoint `fabric-gwlbe-1a`)
     - **Chặng 8:** `GWLB Endpoint (vpce-xxx)`
     - **Chặng 9:** `Transit Gateway Route Table (fabric-tgw-inspection-rt)` (Định tuyến trả về `10.50.0.0/16` trỏ sang Core VPC Attachment)
     - **Chặng 10:** `Core TGW Attachment (tgw-attach-zzz)`
     - **Chặng 11:** `Core Subnet Route Table` (Định tuyến nội bộ local Core VPC)
     - **Chặng 12:** `Core NLB Security Group` (Kiểm tra ingress port 443 -> Allowed)
     - **Chặng 13:** `Destination ENI (Core Internal NLB - 10.50.20.25)`

---

### Bước 5: (Tùy Chọn) Thử Nghiệm Chuẩn Đoán Khi Cấu Hình Lỗi (Unreachable Diagnostic)
1. Thử tạo một Path khác với Destination Port là `22` (SSH) giữa 2 ENI trên.
2. Nhấp **Create and analyze path**.
3. Quan sát kết quả:
   - **Reachability status:** **`Not reachable`**
   - Reachability Analyzer giải thích rõ nguyên nhân chính xác: *"No security group rule allows inbound traffic from source IP to destination ENI on TCP port 22"* hoặc *"No route found in route table"*.
   - Đây là công cụ cực kỳ mạnh mẽ để chứng minh không có đường tắt (bypass) nào cho các cổng không được phép.

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Thực hiện tạo Path và phân tích thông qua AWS CLI:

```bash
# 1. Lấy ENI của Edge Node và Core NLB
EDGE_ENI=$(aws ec2 describe-instances \
  --region ap-southeast-1 \
  --filters "Name=tag:aws:eks:cluster-name,Values=fabric-edge-cluster" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' \
  --output text)

CORE_NLB_ARN=$(aws elbv2 describe-load-balancers \
  --region ap-southeast-1 \
  --names "fabric-core-internal-nlb" \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

CORE_NLB_ENI=$(aws ec2 describe-network-interfaces \
  --region ap-southeast-1 \
  --filters "Name=description,Values=*fabric-core-internal-nlb*" \
  --query 'NetworkInterfaces[0].NetworkInterfaceId' \
  --output text)

echo "Edge ENI: $EDGE_ENI | Core NLB ENI: $CORE_NLB_ENI"

# 2. Tạo Reachability Analyzer Path
PATH_ID=$(aws ec2 create-network-insights-path \
  --region ap-southeast-1 \
  --source "$EDGE_ENI" \
  --destination "$CORE_NLB_ENI" \
  --protocol tcp \
  --destination-port 443 \
  --tag-specifications 'ResourceType=network-insights-path,Tags=[{Key=Name,Value=fabric-edge-to-core-path},{Key=Project,Value=aws-eks-secure-network-fabric}]' \
  --query 'NetworkInsightsPath.NetworkInsightsPathId' \
  --output text)

echo "Created Path: $PATH_ID"

# 3. Kích hoạt phân tích
ANALYSIS_ID=$(aws ec2 start-network-insights-analysis \
  --region ap-southeast-1 \
  --network-insights-path-id "$PATH_ID" \
  --query 'NetworkInsightsAnalysis.NetworkInsightsAnalysisId' \
  --output text)

echo "Started Analysis: $ANALYSIS_ID"

# 4. Chờ 30 giây và kiểm tra kết quả
sleep 30
aws ec2 describe-network-insights-analyses \
  --region ap-southeast-1 \
  --network-insights-analysis-ids "$ANALYSIS_ID" \
  --query 'NetworkInsightsAnalyses[0].{Id:NetworkInsightsAnalysisId,Status:Status,NetworkPathFound:NetworkPathFound}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Khi cần dọn dẹp các Paths đã tạo để tránh rác tài nguyên:
1. Mở VPC Console -> Reachability Analyzer.
2. Tích chọn `fabric-edge-to-core-nlb-path`.
3. Nhấp menu **Actions** -> Chọn **Delete path** -> Xác nhận xóa.
4. Lệnh CLI:
   ```bash
   [ -n "$PATH_ID" ] && aws ec2 delete-network-insights-path --region ap-southeast-1 --network-insights-path-id "$PATH_ID"
   ```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/09-observability/reachability-analyzer-edge-core.json`: Kết quả chi tiết toàn bộ các hops và thuộc tính `NetworkPathFound = true`.
- `evidence/09-observability/reachability-visual-hops.txt`: Trích xuất chuỗi các thành phần trung gian của đường truyền.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Đường dẫn Reachability Analyzer kết nối thành công giữa Edge Worker ENI và Core NLB ENI qua TCP port 443.
- [ ] Trạng thái phân tích đạt **`Status: Completed`** và **`NetworkPathFound: true`**.
- [ ] Chuỗi các chặng logic chứng minh gói tin bắt buộc phải xuyên qua Inspection VPC và GWLB Endpoint trước khi sang Core VPC.
- [ ] Các Security Groups và Route Tables dọc đường truyền đều ở trạng thái hợp lệ (No blocking rules).
