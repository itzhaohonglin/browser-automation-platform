"""
同步环境配置文件

将新增的配置项同步到所有 .env.example 文件中：
- 根目录 .env.example
- dist/browser-automation-platform/.env.example
- dist/browser-automation-platform/_internal/.env.example
"""

import os
import re
from pathlib import Path

# 新增的配置项
NEW_CONFIG = """
# ===== 任务超时检测配置 =====
# 防止任务卡在 processing 状态导致队列阻塞

# 是否启用任务超时检测（默认：启用）
TASK_TIMEOUT_CHECK_ENABLED=true

# 任务超时阈值（分钟）
# 超过此时间的 processing 任务将自动标记为 failed
# 建议值：根据单个任务平均耗时设置，通常 30-120 分钟
# - 快速任务（1-5分钟）：30分钟
# - 普通任务（5-15分钟）：60分钟
# - 慢速任务（15-30分钟）：120分钟
TASK_TIMEOUT_MINUTES=60

# 超时检测间隔（分钟）
# 调度器多久检查一次超时任务
# 建议值：5-15 分钟
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES=10
"""

def find_env_files():
    """查找所有需要更新的 .env.example 文件"""
    base_dir = Path(__file__).parent.parent

    files = [
        base_dir / ".env.example",
        base_dir / "dist" / "browser-automation-platform" / ".env.example",
        base_dir / "dist" / "browser-automation-platform" / "_internal" / ".env.example",
    ]

    return [f for f in files if f.exists()]

def update_env_file(file_path: Path):
    """更新单个 .env.example 文件"""
    print(f"\n处理文件: {file_path}")

    # 读取现有内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经包含新配置
    if 'TASK_TIMEOUT_CHECK_ENABLED' in content:
        print("  [OK] 文件已包含任务超时配置，跳过")
        return False

    # 在文件末尾添加新配置（在最后一行之前）
    if not content.endswith('\n'):
        content += '\n'

    content += NEW_CONFIG

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("  [OK] 已添加任务超时配置")
    return True

def main():
    print("="*60)
    print("同步环境配置文件")
    print("="*60)

    # 查找文件
    files = find_env_files()

    if not files:
        print("\n未找到任何 .env.example 文件")
        return

    print(f"\n找到 {len(files)} 个配置文件")

    # 更新文件
    updated_count = 0
    for file_path in files:
        if update_env_file(file_path):
            updated_count += 1

    print("\n" + "="*60)
    print(f"完成！共更新 {updated_count}/{len(files)} 个文件")
    print("="*60)

    # 显示配置说明
    print("\n配置说明：")
    print("  详细文档: docs/task_timeout_detection.md")
    print("\n  快速配置:")
    print("    - 快速任务: TASK_TIMEOUT_MINUTES=30")
    print("    - 普通任务: TASK_TIMEOUT_MINUTES=60")
    print("    - 慢速任务: TASK_TIMEOUT_MINUTES=120")

if __name__ == "__main__":
    main()
