#!/usr/bin/env python3
"""
scripts/sanitize-evidence.py
Automated sanitizer for evidence artifacts and logs.
Enforces:
1. AWS Account ID -> 123456789012
2. AWS Access Key -> AKIA***REDACTED***
3. Passwords & sensitive tokens -> ***REDACTED***
"""

import os
import re
import sys
from pathlib import Path

PATTERNS = [
    (r"\b(?!123456789012\b)(\d{12})\b", "123456789012"),
    (r"AKIA[0-9A-Z]{16}", "AKIA***REDACTED***"),
    (r"\"Password\":\s*\"[^\"]+\"", "\"Password\": \"***REDACTED***\""),
    (r"\"password\":\s*\"[^\"]+\"", "\"password\": \"***REDACTED***\""),
    (r"Bearer\s+[A-Za-z0-9\-_\.]+", "Bearer ***REDACTED***"),
]

def sanitize_file(filepath: Path) -> bool:
    try:
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    new_content = content
    for pattern, replacement in PATTERNS:
        # Don't replace timestamps like 202611051530 if 12 digits
        def repl(match):
            val = match.group(0)
            if val.startswith("2026") or val.startswith("2025") or val.startswith("2024"):
                return val
            return replacement
        if pattern == PATTERNS[0][0]:
            new_content = re.sub(pattern, repl, new_content)
        else:
            new_content = re.sub(pattern, replacement, new_content)

    if new_content != content:
        filepath.write_text(new_content, encoding="utf-8")
        print(f"[SANITIZED] {filepath}")
        return True
    return False

def main():
    root = Path(__file__).resolve().parent.parent / "evidence"
    if not root.exists():
        print("Evidence folder not found.")
        sys.exit(0)

    modified = 0
    total = 0
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".log", ".txt", ".md"}:
            total += 1
            if sanitize_file(path):
                modified += 1
    print(f"Sanitization scan complete: {total} files scanned, {modified} modified.")

if __name__ == "__main__":
    main()

