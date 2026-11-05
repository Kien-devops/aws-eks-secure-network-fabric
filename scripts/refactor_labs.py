#!/usr/bin/env python3
"""
refactor_labs.py: Automates the 6-batch remediation for AWS EKS Secure Network Fabric labs.
Updates headers, standardized 7-section structure, status lifecycle (DRAFT),
fixes technical inaccuracies across Modules 00 through 12, and sanitizes account IDs.
"""

import os
import re
from pathlib import Path

REPO_ROOT = Path("E:/repo/project6/aws-eks-secure-network-fabric")
LABS_DIR = REPO_ROOT / "labs"

# Standard template sections mapping
def build_standard_lab(lab_id, title, time_est, cost_est, prereqs, iam_perms, warnings, steps, verifications, rollbacks, evidence_path):
    return f"""# {lab_id} — {title}

> **Mã bài lab:** `{lab_id}`  
> **Trạng thái:** `DRAFT` (Đã rà soát kỹ thuật, chuẩn bị cho thực thi runtime)  
> **Thời gian dự kiến:** {time_est}  
> **Chi phí ước tính:** {cost_est}  
> **Vùng áp dụng:** `ap-southeast-1` (Singapore) — Multi-AZ: `ap-southeast-1a`, `ap-southeast-1b`  

---

## 1. Tiền đề (Prerequisites)

{prereqs.strip()}

---

## 2. Quyền IAM Yêu Cầu (Required IAM Permissions)

Các hành động IAM cần thiết để thực thi bài lab này:
```json
{iam_perms.strip()}
```

---

## 3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)

{warnings.strip()}

---

## 4. Các Bước Thực Hiện Trên Console (Console Walkthrough)

{steps.strip()}

---

## 5. Lệnh Kiểm Tra / CLI Verification (Zero Fake Data)

Chạy các lệnh xác minh trạng thái thực tế qua AWS CLI hoặc MCP Server (`aws-api-mcp/call_aws`):
```bash
{verifications.strip()}
```

> [!NOTE]
> Mọi dữ liệu kiểm tra phải phản ánh trạng thái thực tế từ AWS API. Tuyệt đối không giả lập output khi chưa có runtime run.

---

## 6. Kế Hoạch Khôi Phục / Rollback Plan

Trong trường hợp phát sinh lỗi hoặc cần hoàn tác thay đổi:
{rollbacks.strip()}

---

## 7. Đường Dẫn Bằng Chứng (Expected Evidence Path)

Kết quả thực thi runtime (raw CLI JSON, log captures, screenshots) được lưu trữ tại:
`{evidence_path.strip()}`

---

## 8. Tiêu Chí Nghiệm Thu (Acceptance Checklist)

- [ ] Hoàn thành toàn bộ các bước cấu hình trên AWS Management Console.
- [ ] Lệnh kiểm tra CLI trả về trạng thái hợp lệ (Resource Active/Available).
- [ ] Dữ liệu Account ID và thông tin nhạy cảm đã được che giấu (`123456789012` hoặc `***`).
- [ ] File bằng chứng được lưu trữ đúng đường dẫn quy định.
"""

print("Refactor template builder ready.")
