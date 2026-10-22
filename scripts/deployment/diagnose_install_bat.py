#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
详细诊断 install.bat 文件
检查可能导致错误的所有问题
"""

import os
import re
from pathlib import Path


def check_file_details(file_path):
    """详细检查文件"""
    print("=" * 70)
    print(f"Checking: {file_path}")
    print("=" * 70)
    print()

    # 1. 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return

    # 2. 检查文件大小
    file_size = os.path.getsize(file_path)
    print(f"File size: {file_size} bytes")
    print()

    # 3. 检查编码和 BOM
    with open(file_path, 'rb') as f:
        raw_content = f.read()

    if raw_content[:3] == b'\xef\xbb\xbf':
        print("[WARN] File has UTF-8 BOM")
    else:
        print("[OK] No BOM")

    # 4. 尝试不同编码读取
    encodings = ['gbk', 'utf-8', 'utf-8-sig', 'gb2312', 'ascii']
    detected_encoding = None

    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            detected_encoding = enc
            print(f"[OK] Can read with {enc} encoding")
            break
        except UnicodeDecodeError:
            print(f"[FAIL] Cannot read with {enc} encoding")

    if not detected_encoding:
        print("[ERROR] Cannot decode file with any common encoding")
        return

    print()

    # 5. 检查行尾符
    crlf_count = raw_content.count(b'\r\n')
    lf_only_count = raw_content.count(b'\n') - crlf_count
    cr_only_count = raw_content.count(b'\r') - crlf_count

    print(f"Line endings:")
    print(f"  CRLF (\\r\\n): {crlf_count}")
    print(f"  LF only (\\n): {lf_only_count}")
    print(f"  CR only (\\r): {cr_only_count}")

    if lf_only_count > 0 or cr_only_count > 0:
        print("[WARN] Mixed or non-CRLF line endings detected")
    else:
        print("[OK] All CRLF")
    print()

    # 6. 检查问题语法
    lines = content.split('\n')
    issues = []

    for i, line in enumerate(lines, 1):
        # 去掉行尾的 \r
        line = line.rstrip('\r')

        # 检查 if not exist 与括号
        if re.search(r'if not exist .+ \(', line):
            issues.append((i, 'if_not_exist', line))

        # 检查 echo 中的 #
        if re.search(r'^\s*echo\s+.*#', line):
            issues.append((i, 'hash_in_echo', line))

        # 检查特殊字符
        for char in ['&', '|', '<', '>', '^', '%']:
            if char in line and 'REM' not in line and '::' not in line:
                # 检查是否被正确转义或在合适的上下文中
                if char == '&' and '^&' not in line and 'errorlevel' not in line.lower():
                    issues.append((i, f'unescaped_{char}', line))

        # 检查非 ASCII 字符
        try:
            line.encode('ascii')
        except UnicodeEncodeError:
            non_ascii = [c for c in line if ord(c) > 127]
            if non_ascii and 'echo' not in line.lower():
                issues.append((i, 'non_ascii', f"{line} (chars: {non_ascii})"))

    if issues:
        print(f"[WARN] Found {len(issues)} potential issues:")
        print()
        for line_no, issue_type, line_content in issues:
            print(f"  Line {line_no}: {issue_type}")
            print(f"    {line_content[:70]}")
            print()
    else:
        print("[OK] No obvious syntax issues found")

    print()

    # 7. 检查关键命令
    print("Key commands found:")
    keywords = ['choice', 'if errorlevel', 'goto', 'exit', 'pause']
    for keyword in keywords:
        count = sum(1 for line in lines if keyword.lower() in line.lower() and not line.strip().startswith('REM') and not line.strip().startswith('::'))
        print(f"  {keyword}: {count} occurrences")

    print()

    # 8. 输出前20行和可能有问题的行
    print("First 20 lines:")
    print("-" * 70)
    for i, line in enumerate(lines[:20], 1):
        print(f"{i:3d}: {line.rstrip()}")

    if issues:
        print()
        print("-" * 70)
        print("Lines with potential issues:")
        print("-" * 70)
        for line_no, issue_type, line_content in issues[:10]:  # Show first 10
            print(f"{line_no:3d}: {line_content.rstrip()}")


def main():
    """主函数"""
    file_path = Path(__file__).parent / 'client' / 'install.bat'
    check_file_details(file_path)


if __name__ == '__main__':
    main()
