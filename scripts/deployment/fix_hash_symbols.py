#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复批处理文件中的 # 符号问题
批处理中 # 会被当作命令，导致 "此时不应有" 错误
"""

import re
from pathlib import Path


def fix_hash_in_echo(content):
    """
    移除 echo 语句中的 # 注释

    批处理中 # 不是注释符号，会导致解析错误
    """
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # 检查是否是 echo 语句且包含 #
        if re.match(r'^\s*echo\s+.*#', line):
            # 移除 # 及其后面的内容
            fixed_line = re.sub(r'\s*#.*$', '', line)
            fixed_lines.append(fixed_line)
            print(f"    Fixed: {line.strip()}")
            print(f"        -> {fixed_line.strip()}")
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def process_bat_file(file_path):
    """处理单个批处理文件"""
    print(f"\nProcessing: {file_path.name}")
    print("-" * 60)

    # 读取文件
    try:
        with open(file_path, 'r', encoding='gbk') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

    # 检查是否有问题
    has_hash = bool(re.search(r'^\s*echo\s+.*#', content, re.MULTILINE))

    if not has_hash:
        print("  [OK] No # symbols in echo statements")
        return False

    # 修复内容
    original_content = content
    content = fix_hash_in_echo(content)

    # 写回文件
    if content != original_content:
        with open(file_path, 'w', encoding='gbk', newline='\r\n') as f:
            f.write(content)
        print("  [FIXED] File updated")
        return True
    else:
        print("  [OK] No changes needed")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Fix # symbols in batch files")
    print("=" * 60)
    print()
    print("Issue: # is not a comment in batch files")
    print("       It will be parsed as a command and cause errors")
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

    print(f"Found {len(bat_files)} batch files")

    # 处理每个文件
    fixed_count = 0
    for bat_file in bat_files:
        if process_bat_file(bat_file):
            fixed_count += 1

    print()
    print("=" * 60)
    print(f"Complete: Fixed {fixed_count} files")
    print("=" * 60)


if __name__ == '__main__':
    main()
