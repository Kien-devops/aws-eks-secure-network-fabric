# 09.04 — Đặc Tả Kiểm Chứng Đường Truyền Logic Bằng AWS VPC Reachability Analyzer

> **Mã bài lab:** `09.04`
> **Trạng thái tài liệu:** `RUNTIME_PASS`
> **Vùng triển khai:** `ap-southeast-1` (Singapore)
> **File bằng chứng:** `evidence/09-observability/reachability-analyzer-edge-core.json`

---

## 1. Mục Tiêu (Objective)

Đặc tả công cụ phân tích toán học mô hình mạng AWS VPC Reachability Analyzer (Formal Reasoning) nhằm kiểm chứng và chứng minh đường truyền logic hai chiều giữa Edge Worker Node ENI và Core Internal NLB ENI qua cổng TCP 443 đi xuyên qua GWLB Inspection mà không gửi gói tin giả lập.

---

## 2. Tài Nguyên (Resources)

| Tên Logical | Loại Resource | Điểm Đầu / Điểm Cuối | Runtime ID / ARN (Snapshot) |
| :--- | :--- | :--- | :--- |
| `fabric-edge-to-core-path` | `AWS::EC2::NetworkInsightsPath` | Source: Edge Node ENI<br>Dest: Core NLB ENI | Protocol: TCP, Port: 443 |
| Phiên Phân Tích Logic | `AWS::EC2::NetworkInsightsAnalysis` | Liên kết với Path trên | Status: `succeeded`<br>`NetworkPathFound: true` |

*Ghi chú: Runtime ID / ARN là dữ liệu snapshot tại thời điểm kiểm tra thực tế; Tên Logical là định danh chuẩn theo thiết kế.*

---

## 3. Thẻ Định Danh (Tags)

| Key | Value | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| `Name` | `fabric-edge-to-core-path` | Network Insights Path |
| `Project` | `aws-eks-secure-network-fabric` | Network Insights Path & Analysis |
| `Environment` | `prod` | Network Insights Path & Analysis |
| `ManagedBy` | `manual` | Quản trị kiểm tra mạng thủ công Console/CLI |

---

## 4. Cấu Hình Chi Tiết (Configuration)

### 4.1 Thuộc Tính Network Insights Path

- **Source Type:** `Network Interfaces` (ENI của Node `fabric-edge-eks`).
- **Destination Type:** `Network Interfaces` (ENI của `fabric-core-internal-nlb`).
- **Protocol & Port:** `TCP 443` (HTTPS mã hóa TLS).

### 4.2 Chuỗi 13 Chặng Mạng Logic Được Xác Minh (Hop-by-Hop Verification)

| Chặng (Hop) | Thành Phần Mạng | Vai Trò Trong Kiến Trúc |
| :---: | :--- | :--- |
| **1 - 2** | `Edge Node ENI` & `Node Security Group` | Nguồn gói tin, kiểm tra Egress TCP 443 -> `Allowed`. |
| **3 - 4** | `fabric-edge-private-rt` & `Edge TGW Attachment` | Định tuyến default `10.50.0.0/16` trỏ vào TGW. |
| **5** | `fabric-tgw-edge-rt` | TGW Route Table trỏ `10.50.0.0/16` sang Inspection VPC. |
| **6 - 7** | `Inspection TGW Attachment` & `Subnet RT 1a` | Tiếp nhận gói tin và chuyển tiếp tới GWLBe AZ-a. |
| **8** | `fabric-gwlbe-1a` | Điểm cuối GWLB đưa lưu lượng vào Suricata kiểm tra. |
| **9** | `fabric-tgw-inspection-rt` | TGW Route Table trả lưu lượng đã duyệt về Core VPC. |
| **10 - 11** | `Core TGW Attachment` & `Core Node Subnet RT` | Tiếp nhận gói tin đã kiểm tra vào Core VPC. |
| **12 - 13** | `Core NLB Security Group` & `Core NLB ENI` | Đích đến, kiểm tra Ingress TCP 443 -> `Allowed`. |

---

## 5. Phụ Thuộc (Dependencies)

- Phụ thuộc vào `02.03` (TGW Attachments và Route Tables).
- Phụ thuộc vào `04.03` (Internal NLB và các ENIs phân bổ).
- Phụ thuộc vào `05.03`, `05.04` (GWLB Endpoints và bảng định tuyến đối xứng).

---

## 6. Kiểm Tra Đạt (Verification)

| Kiểm Tra | Lệnh / Tiêu Chí Xác Minh | Kết Quả Mong Đợi |
| :--- | :--- | :--- |
| **Trạng Thái Phân Tích** | `aws ec2 describe-network-insights-analyses --network-insights-analysis-ids <AnalysisId>` | `Status: succeeded`, `NetworkPathFound: true`. |
| **Độ Dài Tuyến Đường** | Phân tích mảng `ForwardPathComponents` trong kết quả JSON | Xuất hiện đầy đủ chuỗi chặng đi qua cả 3 VPCs (Edge, Inspection, Core). |
| **Chẩn Đoán Cổng Không Hợp Lệ** | Thử nghiệm phân tích cổng TCP 22 (SSH) | `NetworkPathFound: false` (Báo lỗi chính xác do Security Group chặn). |

---

## 7. Cảnh Báo An Toàn & Rollback Plan

- **Tính chất an toàn tuyệt đối:** Reachability Analyzer dựa trên phân tích hình thức toán học (Formal Reasoning), hoàn toàn không truyền tải dữ liệu thật, do đó không gây gián đoạn hay ảnh hưởng tới hiệu năng hệ thống.
- **Quy trình Rollback:**
  ```bash
  # Xóa Network Insights Path
  aws ec2 delete-network-insights-path --region ap-southeast-1 --network-insights-path-id <PathId>
  ```
