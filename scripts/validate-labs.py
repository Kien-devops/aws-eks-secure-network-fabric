#!/usr/bin/env python3
"""
validate-labs.py: Comprehensive static validator for AWS EKS Secure Network Fabric labs.
Enforces:
1. Standard section headers (Prerequisites, IAM, Cost/Warning, Steps, Verification, Rollback, Evidence)
2. Lab status tag lifecycle (DRAFT, READY_TO_RUN, RUNTIME_PASS)
3. Zero Fake Data: flags premature [PASS] marks without evidence
4. Sanitization: flags unredacted AWS Account IDs (12 digits != 123456789012)
5. Link verification across lab documents
"""

import os
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    (r"tiền đề|prerequisite", "1. Tiền đề (Prerequisites)"),
    (r"quyền iam|iam permission", "2. Quyền IAM Yêu Cầu (Required IAM Permissions)"),
    (r"cảnh báo|ước tính chi phí|cost.*warning", "3. Cảnh Báo & Ước Tính Chi Phí (Cost & Safety Warnings)"),
    (r"các bước thực hiện|thực hiện trên console|console.*walkthrough", "4. Các Bước Thực Hiện Trên Console"),
    (r"lệnh kiểm tra|cli verification|xác minh", "5. Lệnh Kiểm Tra / CLI Verification"),
    (r"kế hoạch khôi phục|rollback", "6. Kế Hoạch Khôi Phục / Rollback Plan"),
    (r"đường dẫn bằng chứng|expected evidence", "7. Đường Dẫn Bằng Chứng (Expected Evidence Path)")
]

VALID_STATUSES = {"DRAFT", "READY_TO_RUN", "RUNTIME_PASS"}

# Detect unredacted 12-digit AWS account numbers
ACCOUNT_ID_REGEX = re.compile(r"\b(?!123456789012\b)(\d{12})\b")

def validate_lab_file(file_path: Path) -> list:
    errors = []
    warnings = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Status tag check
    status_match = re.search(r"\*\*Trạng thái:\*\*\s*`?([A-Z_]+)`?", content, re.IGNORECASE)
    if not status_match:
        errors.append(f"Missing or malformed status header (**Trạng thái:** `DRAFT|READY_TO_RUN|RUNTIME_PASS`)")
    else:
        status_val = status_match.group(1).upper()
        if status_val not in VALID_STATUSES:
            errors.append(f"Invalid status '{status_val}'. Must be one of {VALID_STATUSES}")

    # 2. Required sections check
    for pattern, section_name in REQUIRED_SECTIONS:
        if not re.search(rf"^#+\s*.*({pattern})", content, re.MULTILINE | re.IGNORECASE):
            errors.append(f"Missing required section: {section_name}")

    # 3. Premature [PASS] check (if status is DRAFT)
    if status_match and status_match.group(1).upper() == "DRAFT":
        if re.search(r"\[PASS\]", content):
            warnings.append("Found '[PASS]' marker in a DRAFT lab without confirmed runtime execution")

    # 4. Account ID sanitization
    for match in ACCOUNT_ID_REGEX.finditer(content):
        # Exclude common non-account numbers if any (e.g., timestamps if 12 digits, but 12 digits usually account ID)
        val = match.group(1)
        if not val.startswith("2026"):  # avoid timestamp matches
            errors.append(f"Potentially unredacted AWS Account ID found: {val} (Must be redacted or 123456789012)")

    # 5. Check markdown relative links
    link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    for text, link in link_matches:
        if link.startswith("http") or link.startswith("#") or link.startswith("mailto:"):
            continue
        # Strip anchor if present
        clean_link = link.split("#")[0]
        if not clean_link:
            continue
        target_path = (file_path.parent / clean_link).resolve()
        if not target_path.exists():
            warnings.append(f"Broken relative link: '{link}' (points to non-existent path: {target_path})")

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
    # Filter out README.md in module directories if desired, or validate them separately
    step_labs = [f for f in lab_files if f.name != "README.md"]
    
    print(f"==================================================")
    print(f"AWS EKS Secure Network Fabric - Lab Validator")
    print(f"Root: {labs_dir}")
    print(f"Total Step Labs Found: {len(step_labs)}")
    print(f"==================================================\n")

    for lab_file in step_labs:
        total_files += 1
        rel_path = lab_file.relative_to(repo_root)
        errors, warnings = validate_lab_file(lab_file)
        
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
        print("Status: PASSED. All lab documents adhere to framework rules.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
