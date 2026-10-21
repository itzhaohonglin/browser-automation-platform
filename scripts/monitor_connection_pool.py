"""
数据库连接池监控工具

用于实时监控连接池状态，帮助诊断连接泄漏问题。

使用方法:
    python scripts/monitor_connection_pool.py
"""

import asyncio
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, ".")

from app.core.database import async_engine


async def monitor_pool():
    """监控连接池状态"""
    print("=" * 60)
    print("数据库连接池监控工具")
    print("=" * 60)
    print()
    print("按 Ctrl+C 退出")
    print()

    try:
        while True:
            pool = async_engine.pool

            # 获取连接池状态
            size = pool.size()  # 当前连接数
            checked_in = pool.checkedin()  # 空闲连接数
            overflow = pool.overflow()  # 溢出连接数
            checked_out = size - checked_in  # 正在使用的连接数

            # 计算利用率
            total_capacity = async_engine.pool._pool.maxsize + async_engine.pool._max_overflow
            utilization = (size / total_capacity) * 100 if total_capacity > 0 else 0

            # 输出状态
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}]")
            print(f"  连接池大小: {async_engine.pool._pool.maxsize}")
            print(f"  最大溢出: {async_engine.pool._max_overflow}")
            print(f"  当前连接数: {size}")
            print(f"  空闲连接: {checked_in}")
            print(f"  使用中连接: {checked_out}")
            print(f"  溢出连接: {overflow}")
            print(f"  利用率: {utilization:.1f}%")

            # 告警检查
            if checked_out > async_engine.pool._pool.maxsize:
                print(f"  ⚠️  警告: 使用溢出连接！")

            if utilization > 80:
                print(f"  ⚠️  警告: 连接池利用率过高！")

            if checked_in == 0 and checked_out > 0:
                print(f"  ⚠️  警告: 无空闲连接，可能即将阻塞！")

            print()

            # 每 5 秒刷新一次
            await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\n监控已停止")


if __name__ == "__main__":
    # Windows 平台设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(monitor_pool())
