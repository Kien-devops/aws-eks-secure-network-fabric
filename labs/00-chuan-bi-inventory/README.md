# Module 00: Chuẩn Bị Môi Trường & Kiểm Kê Tài Nguyên AWS (Inventory)

## 1. Thứ Tự Phụ Thuộc (Execution Order)

```text
01-account-region-identity.md (Xác thực IAM & Region ap-southeast-1)
  │
  ▼
02-naming-tagging-budget.md (Chuẩn định danh & Budget $50.00 USD)
  │
  ▼
03-evidence-hygiene-sanitization.md (S3 Vault & Khử trùng dữ liệu)
```

---

## 2. Danh Mục Tài Nguyên (Resource Inventory)

| Tài Nguyên (Resource) | Loại (Type) | Phạm Vi / Vùng | Mô Tả & Tiêu Chuẩn |
| :--- | :--- | :--- | :--- |
| `kien-lvn` | IAM Identity | Global | Caller identity triển khai hạ tầng |
| `ap-southeast-1` | AWS Region | Singapore | Vùng triển khai mặc định (AZs: 1a, 1b) |
| `fabric-project6-monthly-budget` | AWS Budget | Global | Ngân sách trần $50.00 USD, cảnh báo 80% & 100% |
| `fabric-evidence-vault-*` | S3 Bucket | `ap-southeast-1` | Kho lưu trữ bằng chứng kiểm toán (Block Public Access, SSE-S3) |
| `evidence/00-inventory/` | Local Directory | Local Workspace | Thư mục bằng chứng runtime đã khử trùng |
