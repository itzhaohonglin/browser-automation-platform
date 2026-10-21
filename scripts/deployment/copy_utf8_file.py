#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复制文件并保持 UTF-8 编码
用于打包脚本，确保 .env.example 中的中文注释不乱码
"""
import sys
import shutil
from pathlib import Path


def copy_utf8_file(src: str, dst: str):
    """
    复制文件并保持 UTF-8 编码

    Args:
        src: 源文件路径
        dst: 目标文件路径
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)

        if not src_path.exists():
            print(f"[ERROR] Source file not found: {src}")
            return False

        # 确保目标目录存在
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        # 读取源文件（UTF-8）
        content = src_path.read_text(encoding='utf-8')

        # 写入目标文件（UTF-8）
        dst_path.write_text(content, encoding='utf-8')

        print(f"[OK] Copied {src} -> {dst} (UTF-8 encoding preserved)")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python copy_utf8_file.py <source> <destination>")
        sys.exit(1)

    src = sys.argv[1]
    dst = sys.argv[2]

    success = copy_utf8_file(src, dst)
    sys.exit(0 if success else 1)
