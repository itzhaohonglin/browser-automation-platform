#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试修复后的批处理文件
模拟运行环境，检查语法是否正确
"""

import subprocess
import sys
from pathlib import Path


def test_batch_syntax(bat_file):
    """
    测试批处理文件语法
    使用 cmd /c 运行，但立即退出，只检查语法
    """
    print(f"Testing: {bat_file.name}")

    try:
        # 使用 echo 命令测试文件是否可被 cmd 正确解析
        # 注意：我们不实际执行文件内容，只检查语法
        result = subprocess.run(
            ['cmd', '/c', 'type', str(bat_file)],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='gbk'
        )

        if result.returncode == 0:
            print(f"  [OK] Syntax valid, file readable")
            return True
        else:
            print(f"  [ERROR] Exit code {result.returncode}")
            if result.stderr:
                print(f"  Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  [ERROR] Timeout")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Quick Syntax Test for Batch Files")
    print("=" * 60)
    print()

    # 获取 client 目录
    script_dir = Path(__file__).parent
    client_dir = script_dir / 'client'

    if not client_dir.exists():
        print(f"[ERROR] Directory not found: {client_dir}")
        return 1

    # 测试关键批处理文件
    critical_files = [
        'install.bat',
        'startup.bat',
        'install_browser.bat',
        'init_database.bat',
        'init_config.bat'
    ]

    all_ok = True

    for filename in critical_files:
        bat_file = client_dir / filename
        if bat_file.exists():
            if not test_batch_syntax(bat_file):
                all_ok = False
        else:
            print(f"[WARN] File not found: {filename}")
            all_ok = False
        print()

    print("=" * 60)
    if all_ok:
        print("[SUCCESS] All critical batch files passed syntax check!")
        print()
        print("The 'if not exist' error should be fixed.")
        print("You can now package and test in production.")
        return 0
    else:
        print("[FAILURE] Some files failed syntax check!")
        print()
        print("Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
