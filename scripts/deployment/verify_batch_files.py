#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证批处理文件的编码和语法
在打包前运行此脚本以确保批处理文件正确
"""

import os
import re
from pathlib import Path


def check_encoding(file_path):
    """检查文件编码"""
    # 尝试不同编码读取
    encodings = ['gbk', 'utf-8', 'utf-8-sig', 'gb2312']
    detected = None

    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            detected = enc
            break
        except UnicodeDecodeError:
            continue

    if detected:
        # 检查是否有 BOM
        with open(file_path, 'rb') as f:
            first_bytes = f.read(3)
            has_bom = first_bytes == b'\xef\xbb\xbf'

        return {
            'encoding': detected,
            'has_bom': has_bom,
            'status': 'ok' if detected in ['gbk', 'gb2312'] else 'warning'
        }
    else:
        return {
            'encoding': 'unknown',
            'has_bom': False,
            'status': 'error'
        }


def check_line_endings(file_path):
    """检查行尾符"""
    with open(file_path, 'rb') as f:
        content = f.read()

    crlf_count = content.count(b'\r\n')
    lf_count = content.count(b'\n') - crlf_count

    if crlf_count > 0 and lf_count == 0:
        return {'type': 'CRLF', 'status': 'ok'}
    elif lf_count > 0 and crlf_count == 0:
        return {'type': 'LF', 'status': 'warning'}
    elif crlf_count > 0 and lf_count > 0:
        return {'type': 'Mixed', 'status': 'error'}
    else:
        return {'type': 'Unknown', 'status': 'error'}


def check_syntax(file_path):
    """检查语法问题"""
    issues = []

    try:
        with open(file_path, 'r', encoding='gbk') as f:
            content = f.read()
    except:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # 检查 if not exist 与括号
        if re.search(r'if not exist .+ \(', line):
            issues.append({
                'line': i,
                'type': 'if_not_exist',
                'content': line.strip(),
                'severity': 'high'
            })

        # 检查 echo 语句中的 # 符号（批处理中会被当作命令）
        if re.search(r'^\s*echo\s+.*#', line):
            issues.append({
                'line': i,
                'type': 'hash_in_echo',
                'content': line.strip(),
                'severity': 'high'
            })

        # 检查未转义的特殊字符
        if '&' in line and '^&' not in line and 'REM' not in line:
            # 检查是否在 URL 中
            if 'URL' in line or 'http' in line:
                # URL 中的 & 应该转义为 ^&
                if not re.search(r'\^&', line):
                    issues.append({
                        'line': i,
                        'type': 'unescaped_ampersand',
                        'content': line.strip(),
                        'severity': 'low'
                    })

    return issues


def main():
    """主函数"""
    print("=" * 70)
    print("Batch Files Verification (Detailed)")
    print("=" * 70)
    print()

    # 获取 client 目录
    script_dir = Path(__file__).parent
    client_dir = script_dir / 'client'

    if not client_dir.exists():
        print(f"[ERROR] Directory not found: {client_dir}")
        return

    # 查找所有 .bat 文件
    bat_files = sorted(client_dir.glob('*.bat'))

    if not bat_files:
        print(f"[ERROR] No batch files found in: {client_dir}")
        return

    print(f"Found {len(bat_files)} batch files\n")

    # 检查每个文件
    all_ok = True
    results = []

    for bat_file in bat_files:
        print(f"Checking: {bat_file.name}")
        print("-" * 70)

        # 检查编码
        enc_result = check_encoding(bat_file)
        print(f"  Encoding: {enc_result['encoding']}", end="")
        if enc_result['has_bom']:
            print(" (with BOM)", end="")

        if enc_result['status'] == 'ok':
            print(" [OK]")
        elif enc_result['status'] == 'warning':
            print(" [WARN] Should use GBK")
            all_ok = False
        else:
            print(" [ERROR]")
            all_ok = False

        # 检查行尾符
        le_result = check_line_endings(bat_file)
        print(f"  Line Endings: {le_result['type']}", end="")

        if le_result['status'] == 'ok':
            print(" [OK]")
        elif le_result['status'] == 'warning':
            print(" [WARN] Should use CRLF")
            all_ok = False
        else:
            print(" [ERROR]")
            all_ok = False

        # 检查语法
        syntax_issues = check_syntax(bat_file)
        if syntax_issues:
            print(f"  Syntax Issues: {len(syntax_issues)} found [WARN]")
            for issue in syntax_issues:
                severity_str = "HIGH" if issue['severity'] == 'high' else "LOW"
                print(f"    Line {issue['line']} [{severity_str}]: {issue['type']}")
                print(f"      {issue['content'][:60]}...")
            all_ok = False
        else:
            print(f"  Syntax Issues: None [OK]")

        print()

        results.append({
            'file': bat_file.name,
            'encoding': enc_result,
            'line_endings': le_result,
            'syntax_issues': syntax_issues
        })

    # 汇总
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()

    if all_ok:
        print("[SUCCESS] All batch files are correctly formatted!")
        print()
        print("Ready for packaging:")
        print("  pyinstaller scripts/deployment/build.spec")
    else:
        print("[WARNING] Some issues found!")
        print()
        print("Recommended actions:")
        print("  1. Run fix script:")
        print("     python scripts/deployment/fix_batch_files.py")
        print()
        print("  2. Verify fixes:")
        print("     python scripts/deployment/verify_batch_files.py")
        print()
        print("  3. Package:")
        print("     pyinstaller scripts/deployment/build.spec")

    print()
    print("Documentation:")
    print("  docs/batch_file_syntax_fix.md")
    print()


if __name__ == '__main__':
    main()
