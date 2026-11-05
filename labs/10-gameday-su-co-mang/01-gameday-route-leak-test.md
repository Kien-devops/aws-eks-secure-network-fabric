# 10.01 — GameDay Kịch Bản 1: Sự Cố Rò Rỉ Tuyến Đường (Route Leak Attack / Drift)

> **Mã bài lab:** `10.01`  
> **Trạng thái:** `READY FOR IMPLEMENTATION`  
> **Thời gian dự kiến:** 45 phút  
> **Chi phí ước tính:** $0.00 USD  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore)  

---

## 1. Tiền đề (Prerequisites)

- Đã hoàn tất cấu hình toàn bộ hạ tầng mạng TGW và Route Tables tại [Module 02](../02-ha-tang-mang-co-ban/03-tgw-route-tables-and-attachments.md).
- Hai cụm EKS `fabric-edge-cluster` và `fabric-core-cluster` đang hoạt động bình thường tại [Module 03](../03-cum-eks-kep/02-dual-eks-clusters.md).
- Đã triển khai microservices `frontend` và `order` theo mô hình GitOps tại [Module 04](../04-phan-bo-workloads/04-microservices-gitops-deploy.md).
- Có quyền truy cập `kubectl` tới cả 2 cụm EKS và quyền quản trị VPC/TGW trên AWS Management Console tại Singapore (`ap-southeast-1`).

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để tiêm lỗi định tuyến (Fault Injection) và khôi phục:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTransitGatewayRoute",
        "ec2:DeleteTransitGatewayRoute",
        "ec2:ReplaceTransitGatewayRoute",
        "ec2:SearchTransitGatewayRoutes",
        "ec2:GetTransitGatewayRouteTablePropagations",
        "ec2:DescribeTransitGatewayRouteTables",
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

- **Chi phí:** Thao tác trên TGW Route Tables và gửi lưu lượng thử nghiệm không phát sinh chi phí phụ trội ($0.00 USD).
- **Cảnh báo GameDay (Controlled Blast Radius):** Đây là kịch bản tiêm lỗi mạng có kiểm soát. Mặc dù thao tác trên môi trường Dev/Lab, người thực hiện cần tuân thủ nghiêm ngặt quy trình ghi nhận mốc thời gian ($T_{fault}$, $T_{detect}$, $T_{mitigate}$, $T_{recover}$) và sẵn sàng thực thi lệnh Rollback ngay khi hoàn thành kiểm chứng.

---

## 4. Các Bước Thực Hiện Chi Tiết Trên Console (Console Walkthrough)

### Bước 1: Kiểm Tra Trạng Thái Định Tuyến Chuẩn Ban Đầu (Baseline Check)
1. Mở **VPC Console** tại Region Singapore (`ap-southeast-1`).
2. Tại menu bên trái, cuộn xuống mục **Transit gateways** -> Chọn **Transit gateway route tables**.
3. Chọn bảng định tuyến: `fabric-tgw-edge-rt`.
4. Mở tab **Routes**:
   - Đảm bảo tuyến đường tới mạng Core `10.50.0.0/16` đang có Target là **`fabric-insp-tgw-attachment`** (Bắt buộc phải đi qua Inspection VPC).
5. Từ một Pod kiểm thử trong Edge EKS, gửi lệnh kiểm tra tới Core NLB:
   ```bash
   kubectl exec -it deploy/frontend -n default -- curl -kIv https://order.internal.fabric/health
   ```
   *Kết quả baseline:* Kết nối HTTP/2 200 OK thành công.

---

### Bước 2: Gieo Rắc Lỗi Định Tuyến Trực Tiếp (Fault Injection — Route Leak)
*Mô phỏng tình huống:* Kỹ sư cấu hình sai thêm static route trỏ thẳng sang Core VPC, cố tình bỏ qua cụm kiểm tra an ninh Suricata IDS/IPS.

1. Trên bảng định tuyến **`fabric-tgw-edge-rt`**, chọn tab **Routes**.
2. Nhấp nút màu cam **Create static route**.
3. Trong giao diện tạo tuyến đường:
   - **CIDR:** Nhập `10.50.0.0/16` (Dải IP của Core VPC).
   - **Attachment type:** Chọn `VPC`.
   - **Transit gateway attachment:** Chọn attachment trỏ thẳng sang Core: **`fabric-core-tgw-attachment`**.
4. Ghi lại timestamp chính xác lúc bấm tạo: **$T_{fault}$** (Ví dụ: `2026-11-05 10:15:00 UTC`).
5. Nhấp nút cam **Create static route**.
6. Xác nhận dòng route `10.50.0.0/16` hiện tại đã ghi đè target sang Core Attachment.

---

### Bước 3: Quan Sát Hiện Tượng & Kiểm Chứng Khả Năng Phòng Thủ Đa Tầng (Defense-in-Depth)
Khi tuyến đường TGW bị rò rỉ bỏ qua Inspection, các chốt chặn an ninh nội bộ (Defense-in-Depth) phải phát huy tác dụng:

1. **Kiểm tra truy cập từ Edge Pod:**
   ```bash
   kubectl exec -it deploy/frontend -n default -- curl -m 3 -kIv https://order.internal.fabric/health
   ```
   - **Hiện tượng thực tế:** Gói tin bị chặn đứng ngay tại Core Node / Core Pod. Kết nối trả về lỗi `curl: (28) Failed to connect to order.internal.fabric port 443: Connection timed out`.
2. **Nguyên nhân kỹ thuật (Multi-layer Defense):**
   - **Lớp 1 (NetworkPolicy):** Calico / Kubernetes NetworkPolicy trên `order-service` chỉ cho phép lưu lượng có Source IP sau khi đã được SNAT hoặc kiểm tra phiên hợp lệ.
   - **Lớp 2 (Security Group):** Security Group của Core Worker Nodes chỉ cho phép traffic đến từ CIDR kiểm tra hợp lệ hoặc từ chối các port không được khai báo.
   - **Lớp 3 (Asymmetric Return Failure):** Core TGW Route Table (`fabric-tgw-core-rt`) vẫn có route trả lời `10.40.0.0/16` trỏ sang Inspection VPC (`fabric-insp-tgw-attachment`). Do đó gói tin chiều đi đi thẳng, nhưng gói tin chiều về lại bị ném vào Inspection VPC -> Gây mất đối xứng nghiêm trọng và bị Suricata drop tại chỗ!
3. **Mở CloudWatch Logs Insights:**
   - Chọn Log Group `/aws/vpc/fabric-core-flow`.
   - Chạy query phát hiện các gói tin `REJECT`:
     ```sql
     fields @timestamp, srcAddr, dstAddr, dstPort, action
     | filter action = "REJECT" and dstPort = 443
     | sort @timestamp desc
     | limit 10
     ```
   - Xác nhận có các bản ghi REJECT xuất hiện trùng khớp với mốc thời gian $T_{fault}$.
   - Ghi lại mốc thời gian phát hiện: **$T_{detect}$**.

---

### Bước 4: Khắc Phục Sự Cố & Phục Hồi Tuyến Đường (Incident Remediation)
1. Quay lại trang **Transit gateway route tables** -> Chọn `fabric-tgw-edge-rt` -> Tab **Routes**.
2. Tìm dòng route `10.50.0.0/16`.
3. Tích chọn checkbox cạnh dòng route này -> Nhấp vào menu **Actions** -> Chọn **Delete static route**.
4. Hộp thoại xác nhận hiện ra: Nhập `delete` -> Nhấp **Delete**.
5. Nhấp **Create static route**:
   - **CIDR:** `10.50.0.0/16`
   - **Transit gateway attachment:** Chọn lại **`fabric-insp-tgw-attachment`** (Khôi phục luồng kiểm tra qua Inspection VPC).
   - Nhấp **Create static route**.
6. Ghi lại timestamp phục hồi: **$T_{mitigate}$**.

---

### Bước 5: Kiểm Chứng Phục Hồi Hoàn Toàn (Verification)
1. Thực hiện lại lệnh gọi dịch vụ từ Edge Pod:
   ```bash
   kubectl exec -it deploy/frontend -n default -- curl -kIv https://order.internal.fabric/health
   ```
   *Kết quả phục hồi:* Phản hồi `HTTP/2 200 OK` thành công ngay lập tức.
2. Ghi lại mốc thời gian phục hồi hoàn toàn: **$T_{recover}$**.
3. Tính toán các chỉ số GameDay:
   - Thời gian phát hiện (MTTD): $MTTD = T_{detect} - T_{fault}$
   - Thời gian khắc phục (MTTR): $MTTR = T_{recover} - T_{fault}$

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Kiểm tra trực tiếp tuyến đường trong TGW Route Table qua AWS CLI để chứng minh không còn route leak:

```bash
TGW_EDGE_RT=$(aws ec2 describe-transit-gateway-route-tables \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-tgw-edge-rt" \
  --query 'TransitGatewayRouteTables[0].TransitGatewayRouteTableId' \
  --output text)

aws ec2 search-transit-gateway-routes \
  --region ap-southeast-1 \
  --transit-gateway-route-table-id "$TGW_EDGE_RT" \
  --filters "Name=route-search.exact-match,Values=10.50.0.0/16" \
  --query 'Routes[*].{DestinationCidrBlock:DestinationCidrBlock,State:State,Type:Type,AttachmentId:TransitGatewayAttachments[0].TransitGatewayAttachmentId}' \
  --output table
```

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Lệnh khẩn cấp qua CLI để ép buộc sửa lại route về Inspection Attachment nếu giao diện Console bị trễ:

```bash
TGW_INSP_ATTACH=$(aws ec2 describe-transit-gateway-vpc-attachments \
  --region ap-southeast-1 \
  --filters "Name=tag:Name,Values=fabric-insp-tgw-attachment" \
  --query 'TransitGatewayVpcAttachments[0].TransitGatewayAttachmentId' \
  --output text)

aws ec2 replace-transit-gateway-route \
  --region ap-southeast-1 \
  --transit-gateway-route-table-id "$TGW_EDGE_RT" \
  --destination-cidr-block "10.50.0.0/16" \
  --transit-gateway-attachment-id "$TGW_INSP_ATTACH"
```

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

- `evidence/10-gameday/gameday-01-route-leak-timeline.json`: Mốc thời gian $T_{fault}, T_{detect}, T_{recover}$.
- `evidence/10-gameday/gameday-01-blocked-flow-logs.json`: Bằng chứng Flow Logs REJECT chứng minh cơ chế Defense-in-Depth.
- `evidence/10-gameday/gameday-01-restored-tgw-route.json`: Cấu hình route table sau khi khôi phục an toàn.

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Tiêm thành công lỗi định tuyến trực tiếp trên TGW Route Table và ghi lại $T_{fault}$.
- [ ] Chứng minh nguyên lý Defense-in-Depth: Lưu lượng vi phạm bị chặn đứng ở tầng tiếp theo, không thể truy cập trái phép vào tài nguyên Core.
- [ ] Flow Logs và CloudWatch Insights ghi nhận đầy đủ sự kiện REJECT.
- [ ] Khôi phục tuyến đường về `fabric-insp-tgw-attachment` thành công.
- [ ] Dịch vụ giữa Edge và Core thông suốt 100% với HTTP 200 sau khi khắc phục.
