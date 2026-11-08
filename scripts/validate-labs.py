#!/usr/bin/env python3
"""
validate-labs.py: Comprehensive specification validator for AWS EKS Secure Network Fabric labs.
Enforces:
1. Declarative resource specification structure:
   - Mục Tiêu (Objective: 1-2 sentences)
   - Tài Nguyên / Resource (Name, Type, VPC/Subnet/AZ)
   - Tags (Standard tags: Project, Environment, ManagedBy)
   - Cấu Hình / Configuration (CIDR, Ports, Protocols, Routing, IAM, TLS)
   - Phụ Thuộc / Dependencies
   - Kiểm Tra Đạt / Verification Checklist
   - Cảnh Báo & Rollback (Safety warnings & rollback conditions)
2. Status tag lifecycle: DRAFT, READY_TO_RUN, RUNTIME_PASS (COMPLETED is deprecated)
3. Zero Fake Data & Sanitization: flags unredacted AWS Account IDs
4. Link verification across lab documents (no dead links, e.g. deleted spec.md)
5. Architectural consistency: 2 services baseline (edge-frontend, core-service)
"""

import os
import re
import sys
from pathlib import Path

REQUIRED_SPEC_SECTIONS = [
    (r"mục tiêu|objective", "1. Mục Tiêu (Objective)"),
    (r"tài nguyên|resource", "2. Tài Nguyên / Resources"),
    (r"thẻ định danh|tags", "3. Thẻ Định Danh / Tags"),
    (r"cấu hình|configuration", "4. Cấu Hình Chi Tiết / Configuration"),
    (r"phụ thuộc|dependencies", "5. Phụ Thuộc / Dependencies"),
    (r"kiểm tra đạt|tiêu chí nghiệm thu|verification", "6. Kiểm Tra Đạt / Verification"),
    (r"cảnh báo|khôi phục|rollback|an toàn", "7. Cảnh Báo An Toàn & Rollback")
]

VALID_STATUSES = {"DRAFT", "READY_TO_RUN", "RUNTIME_PASS"}

# Detect unredacted 12-digit AWS account numbers (except 123456789012)
ACCOUNT_ID_REGEX = re.compile(r"\b(?!123456789012\b)(\d{12})\b")

def validate_lab_file(file_path: Path, repo_root: Path) -> tuple[list, list]:
    errors = []
    warnings = []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Status tag check
    status_match = re.search(r"\*\*Trạng thái(?:\s*tài liệu)?:\*\*\s*`?([A-Z_]+)`?", content, re.IGNORECASE)
    if not status_match:
        errors.append("Missing status header (**Trạng thái:** `DRAFT|READY_TO_RUN|RUNTIME_PASS`)")
    else:
        status_val = status_match.group(1).upper()
        if status_val not in VALID_STATUSES:
            errors.append(f"Invalid status '{status_val}'. Must be one of {sorted(VALID_STATUSES)}")

    # 2. Required sections check
    for pattern, section_name in REQUIRED_SPEC_SECTIONS:
        if not re.search(rf"^#+\s*.*({pattern})", content, re.MULTILINE | re.IGNORECASE):
            errors.append(f"Missing required specification section: {section_name}")

    # 3. Account ID sanitization
    for match in ACCOUNT_ID_REGEX.finditer(content):
        val = match.group(1)
        if not val.startswith("2026"):  # avoid timestamp matches
            errors.append(f"Potentially unredacted AWS Account ID found: {val} (Must be redacted to 123456789012)")

    # 4. Check markdown relative links
    link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    for text, link in link_matches:
        if link.startswith("http") or link.startswith("#") or link.startswith("mailto:"):
            continue
        # Strip anchor if present
        clean_link = link.split("#")[0]
        if not clean_link:
            continue
        # Handle file:// scheme
        if clean_link.startswith("file:///"):
            clean_link = clean_link.replace("file:///", "")
            target_path = Path(clean_link)
        else:
            target_path = (file_path.parent / clean_link).resolve()

        if not target_path.exists():
            errors.append(f"Broken relative link: '{link}' -> {target_path}")

    # 5. Check deprecated 5-service references (baseline is 2 services: edge-frontend, core-service)
    # Flag legacy service names if they are specified as separate pods: auth-service, order-service, inventory-service, payment-service
    deprecated_services = ["auth-service", "inventory-service", "payment-service"]
    for svc in deprecated_services:
        if re.search(rf"\b{svc}\b", content) and "legacy" not in content.lower() and "trước đây" not in content.lower():
            warnings.append(f"Reference to deprecated microservice '{svc}'. Baseline architecture is 2 services (edge-frontend, core-service).")

    # 6. Check standard project tags and ManagedBy=manual in Tags section
    if "3. thẻ định danh" in content.lower() or "## 3. tags" in content.lower() or "thẻ định danh" in content.lower():
        if "aws-eks-secure-network-fabric" not in content and "Project" not in content:
            warnings.append("Missing standard tag 'Project: aws-eks-secure-network-fabric' in tags specification.")
        if re.search(r"ManagedBy\s*`?:\s*`?(terraform|iac|cicd|gitops)", content, re.IGNORECASE) or \
           re.search(r"\|\s*`?ManagedBy`?\s*\|\s*`?(terraform|iac|cicd|gitops)`?", content, re.IGNORECASE):
            errors.append("Invalid ManagedBy value. Entire project is manual: ManagedBy must be 'manual'.")

        # Enforce 'Name' key in Section 3 Tag table
        if not re.search(r"\|\s*`?Name`?\s*\|", content, re.IGNORECASE):
            errors.append("Section 3 (Tags) must define the standard 'Name' key/tag.")

    # 7. Check for deprecated/inconsistent CIDRs
    outdated_cidrs = [
        (r"\b10\.80\.250\.\d+/\d+\b", "Outdated Egress TGW CIDR 10.80.250.0/28. Canonical is 10.80.0.0/28 (AZ-a) or 10.80.0.16/28 (AZ-b)."),
        (r"\b10\.70\.2\.0/24\b", "Outdated GWLBe CIDR 10.70.2.0/24. Canonical is 10.70.1.16/28."),
        (r"\b10\.70\.1\.0/24\b", "Outdated GWLBe CIDR 10.70.1.0/24. Canonical is 10.70.1.0/28."),
        (r"\b10\.80\.0\.0/24\b", "Outdated Egress Public CIDR 10.80.0.0/24. Canonical is 10.80.10.0/24."),
    ]
    for cidr_pattern, desc in outdated_cidrs:
        if re.search(cidr_pattern, content):
            errors.append(f"Inconsistent CIDR found: {desc}")

    # 8. Check CIDR syntax validity when CIDRs are present
    cidr_matches = re.findall(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/(\d{1,2})\b", content)
    for ip, prefix in cidr_matches:
        prefix_int = int(prefix)
        if not (0 <= prefix_int <= 32):
            errors.append(f"Invalid CIDR prefix /{prefix} in {ip}/{prefix}")
        parts = [int(p) for p in ip.split(".")]
        if any(p < 0 or p > 255 for p in parts):
            errors.append(f"Invalid IPv4 octet in CIDR: {ip}/{prefix}")

    return errors, warnings

def main():
    repo_root = Path(__file__).resolve().parent.parent
    labs_dir = repo_root / "labs"

    if not labs_dir.exists():
        print(f"Error: Labs directory not found at {labs_dir}")
        sys.exit(1)

    total_files = 0
    total_errors = 0
    total_warnings = 0

    # Scan all numbered labs
    lab_files = sorted(labs_dir.glob("*/*.md"))
    step_labs = [f for f in lab_files if f.name != "README.md"]

    print(f"==================================================")
    print(f"AWS EKS Secure Network Fabric - Resource Spec Validator")
    print(f"Root: {labs_dir}")
    print(f"Total Step Labs Found: {len(step_labs)}")
    print(f"==================================================\n")

    for lab_file in step_labs:
        total_files += 1
        rel_path = lab_file.relative_to(repo_root)
        errors, warnings = validate_lab_file(lab_file, repo_root)

        if errors or warnings:
            print(f"[{rel_path}]")
            for err in errors:
                print(f"  [ERROR] {err}")
                total_errors += 1
            for warn in warnings:
                print(f"  [WARN]  {warn}")
                total_warnings += 1
            print()

    print(f"--------------------------------------------------")
    print(f"Validation Summary:")
    print(f"Files Checked : {total_files}")
    print(f"Errors Found  : {total_errors}")
    print(f"Warnings Found: {total_warnings}")
    print(f"--------------------------------------------------")

    if total_errors > 0:
        print("Status: FAILED. Please remediate reported errors.")
        return 1
    else:
        print("Status: PASSED. All lab documents adhere to resource specification rules.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
