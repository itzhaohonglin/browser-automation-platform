"""
验证数据库连接池配置

检查连接池参数是否正确配置，帮助诊断配置问题。

使用方法:
    python scripts/verify_connection_pool_config.py
"""

import sys
import io

# Windows 控制台编码修复
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, ".")

from app.core.database import async_engine
from app.core.config import settings


def verify_config():
    """验证连接池配置"""
    print("=" * 60)
    print("数据库连接池配置验证")
    print("=" * 60)
    print()

    # 获取配置
    pool = async_engine.pool
    pool_size = pool._pool.maxsize
    max_overflow = pool._max_overflow
    pool_recycle = pool._recycle
    pool_timeout = pool._timeout
    pool_pre_ping = async_engine.pool._pre_ping

    # 显示当前配置
    print("当前配置:")
    print(f"  pool_size: {pool_size}")
    print(f"  max_overflow: {max_overflow}")
    print(f"  pool_recycle: {pool_recycle} 秒 ({pool_recycle / 60:.1f} 分钟)")
    print(f"  pool_timeout: {pool_timeout} 秒")
    print(f"  pool_pre_ping: {pool_pre_ping}")
    print(f"  总连接容量: {pool_size + max_overflow}")
    print()

    # 验证配置
    issues = []
    warnings = []
    ok = []

    # 检查 pool_size
    if pool_size < 10:
        issues.append(f"❌ pool_size={pool_size} 过小，建议至少 10（当前并发需求）")
    else:
        ok.append(f"✅ pool_size={pool_size} 合适")

    # 检查 max_overflow
    if max_overflow > 10:
        warnings.append(f"⚠️  max_overflow={max_overflow} 过大，建议 5-10")
    elif max_overflow < 3:
        warnings.append(f"⚠️  max_overflow={max_overflow} 过小，建议至少 5")
    else:
        ok.append(f"✅ max_overflow={max_overflow} 合适")

    # 检查 pool_recycle（SQL Server 空闲超时通常是 30 分钟）
    if pool_recycle > 1800:  # 30 分钟
        issues.append(
            f"❌ pool_recycle={pool_recycle}秒 ({pool_recycle / 60:.1f}分钟) "
            f"过长，可能超过 SQL Server 空闲超时（30分钟），建议 1200 秒（20分钟）"
        )
    elif pool_recycle < 600:  # 10 分钟
        warnings.append(f"⚠️  pool_recycle={pool_recycle}秒 ({pool_recycle / 60:.1f}分钟) 过短，可能导致频繁重建连接")
    else:
        ok.append(f"✅ pool_recycle={pool_recycle}秒 ({pool_recycle / 60:.1f}分钟) 合适")

    # 检查 pool_pre_ping
    if not pool_pre_ping:
        issues.append("❌ pool_pre_ping=False，强烈建议启用以检测断开的连接")
    else:
        ok.append("✅ pool_pre_ping=True 已启用")

    # 检查总容量
    total_capacity = pool_size + max_overflow
    max_workers = settings.MAX_WORKERS
    required_capacity = max_workers + 7  # 工作进程 + 调度器(3) + API(4)
    if total_capacity < required_capacity:
        warnings.append(
            f"⚠️  总连接容量 {total_capacity} 可能不足 "
            f"(工作进程={max_workers}, 建议至少 {required_capacity})"
        )
    else:
        ok.append(f"✅ 总连接容量 {total_capacity} 充足")

    # 输出结果
    print("验证结果:")
    print()

    if ok:
        for item in ok:
            print(item)

    if warnings:
        print()
        for item in warnings:
            print(item)

    if issues:
        print()
        for item in issues:
            print(item)

    print()
    print("=" * 60)

    if issues:
        print("状态: ❌ 发现配置问题，建议修改")
        print()
        print("修改方法：编辑 app/core/database.py 中的 create_async_engine() 参数")
        return False
    elif warnings:
        print("状态: ⚠️  配置可用，但有优化建议")
        return True
    else:
        print("状态: ✅ 配置正确")
        return True


if __name__ == "__main__":
    try:
        success = verify_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
