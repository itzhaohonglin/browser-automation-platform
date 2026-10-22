#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复批处理文件中的 "if not exist" 语法问题
将 "if not exist" 语法改为更兼容的 "if exist ... goto" 风格
"""

import os
import re
from pathlib import Path

def fix_if_not_exist(content):
    """
    将 if not exist 语法改为 if exist + goto 风格

    原始格式：
        if not exist file.txt (
            echo error
            exit /b 1
        )

    修复格式：
        if exist file.txt goto :label_ok
        echo error
        exit /b 1
        :label_ok
    """
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    label_counter = 1

    while i < len(lines):
        line = lines[i]

        # 匹配 if not exist pattern
        match = re.match(r'^(\s*)if not exist (.+?) \($', line)
        if match:
            indent = match.group(1)
            file_path = match.group(2).strip()

            # 收集括号内的内容
            block_lines = []
            i += 1
            paren_count = 1

            while i < len(lines) and paren_count > 0:
                block_line = lines[i]
                if '(' in block_line:
                    paren_count += block_line.count('(')
                if ')' in block_line:
                    paren_count -= block_line.count(')')

                if paren_count > 0:
                    block_lines.append(block_line)
                i += 1

            # 生成标签名
            label = f"check_ok_{label_counter}"
            label_counter += 1

            # 生成修复后的代码
            fixed_lines.append(f"{indent}if exist {file_path} goto :{label}")
            fixed_lines.extend(block_lines)
            fixed_lines.append(f"{indent}:{label}")
        else:
            fixed_lines.append(line)
            i += 1

    return '\n'.join(fixed_lines)


def fix_simple_if_not_exist(content):
    """
    修复简单的单行 if not exist (不带括号块)

    原始: if not exist import_data mkdir import_data
    修复: if not exist import_data mkdir import_data (保持不变，这种格式通常没问题)
    """
    # 简单的单行 if not exist 通常不会有问题，保持原样
    return content


def process_bat_file(file_path):
    """处理单个批处理文件"""
    print(f"Processing: {file_path.name}")

    # 读取文件内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        encoding = 'utf-8'
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='gbk') as f:
            content = f.read()
        encoding = 'gbk'

    # 修复内容
    original_content = content
    content = fix_if_not_exist(content)

    # 如果有变化，写回文件
    if content != original_content:
        # 使用 ANSI/GBK 编码保存（Windows 批处理标准）
        with open(file_path, 'w', encoding='gbk', newline='\r\n') as f:
            f.write(content)
        print(f"  [OK] Fixed")
        return True
    else:
        print(f"  [SKIP] No changes needed")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Fix 'if not exist' syntax in batch files")
    print("=" * 60)
    print()

    # 获取 client 目录
    script_dir = Path(__file__).parent
    client_dir = script_dir / 'client'

    if not client_dir.exists():
        print(f"Error: Directory not found {client_dir}")
        return

    # 查找所有 .bat 文件
    bat_files = list(client_dir.glob('*.bat'))

    if not bat_files:
        print(f"No batch files found in: {client_dir}")
        return

    print(f"Found {len(bat_files)} batch files\n")

    # 处理每个文件
    fixed_count = 0
    for bat_file in bat_files:
        if process_bat_file(bat_file):
            fixed_count += 1

    print()
    print("=" * 60)
    print(f"Complete: Fixed {fixed_count} files")
    print("=" * 60)

    # 创建备份说明
    backup_note = client_dir / 'BATCH_FIX_README.txt'
    with open(backup_note, 'w', encoding='utf-8') as f:
        f.write("Batch File Fix Notes\n")
        f.write("=" * 60 + "\n\n")
        f.write("Problem: 'if not exist' syntax causes errors in some Windows environments\n")
        f.write("Error message: 'This time should not have not' (Chinese Windows)\n\n")
        f.write("Solution: Replace 'if not exist' with 'if exist + goto' style\n\n")
        f.write("Before:\n")
        f.write("  if not exist file.txt (\n")
        f.write("      echo error\n")
        f.write("      exit /b 1\n")
        f.write("  )\n\n")
        f.write("After:\n")
        f.write("  if exist file.txt goto :check_ok\n")
        f.write("  echo error\n")
        f.write("  exit /b 1\n")
        f.write("  :check_ok\n\n")
        f.write(f"Fix time: {__import__('datetime').datetime.now()}\n")
        f.write(f"Files fixed: {fixed_count}\n")

    print(f"\nReadme created: {backup_note}")


if __name__ == '__main__':
    main()
