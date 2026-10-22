"""
诊断调度器停止问题

检查：
1. 数据库中pending任务数量
2. 数据库中processing任务数量
3. 进程池状态
4. 调度器配置
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from sqlalchemy import select, func


async def diagnose():
    """诊断调度器状态"""
    print("=" * 60)
    print("调度器诊断工具")
    print("=" * 60)

    async with get_session() as session:
        # 1. 统计各状态任务数量
        print("\n【1】任务状态统计：")
        for status in [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.SUCCESS, JobStatus.FAILED]:
            stmt = select(func.count()).where(JobQueue.status == status)
            result = await session.execute(stmt)
            count = result.scalar()
            print(f"  {status.value}: {count} 个")

        # 2. 查询最近的processing任务
        print("\n【2】PROCESSING 状态任务详情：")
        stmt = select(JobQueue).where(JobQueue.status == JobStatus.PROCESSING).order_by(JobQueue.updated_at.desc())
        result = await session.execute(stmt)
        processing_jobs = result.scalars().all()

        if processing_jobs:
            for job in processing_jobs:
                print(f"  任务 #{job.id}:")
                print(f"    - config_id: {job.config_id}")
                print(f"    - 开始时间: {job.updated_at}")
                print(f"    - 已运行: {(asyncio.get_event_loop().time() - job.updated_at.timestamp()) / 60:.1f} 分钟")
        else:
            print("  无PROCESSING任务")

        # 3. 查询最近的pending任务
        print("\n【3】PENDING 状态任务（前5个）：")
        stmt = select(JobQueue).where(JobQueue.status == JobStatus.PENDING).order_by(JobQueue.priority.desc(), JobQueue.created_at.asc()).limit(5)
        result = await session.execute(stmt)
        pending_jobs = result.scalars().all()

        if pending_jobs:
            for job in pending_jobs:
                print(f"  任务 #{job.id}: priority={job.priority}, created_at={job.created_at}")
        else:
            print("  无PENDING任务")

        # 4. 查询最近完成的任务
        print("\n【4】最近完成的任务（后5个）：")
        stmt = select(JobQueue).where(JobQueue.status == JobStatus.SUCCESS).order_by(JobQueue.updated_at.desc()).limit(5)
        result = await session.execute(stmt)
        success_jobs = result.scalars().all()

        if success_jobs:
            for job in success_jobs:
                print(f"  任务 #{job.id}: updated_at={job.updated_at}")
        else:
            print("  无SUCCESS任务")

        # 5. 总任务数
        stmt = select(func.count()).select_from(JobQueue)
        result = await session.execute(stmt)
        total_count = result.scalar()
        print(f"\n【5】总任务数: {total_count}")

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

    # 判断问题
    print("\n【诊断结果】：")
    if processing_jobs:
        print("⚠️  发现 PROCESSING 状态任务，可能是：")
        print("   1. 任务正在执行中（正常）")
        print("   2. 任务执行卡死（异常）")
        print("   3. 进程池回调失败，计数器未递减（BUG）")
        print("\n   建议：检查日志中是否有该任务的'执行完成'日志")
    elif not pending_jobs:
        print("✓  没有PENDING任务，调度器正常停止（所有任务已完成）")
    else:
        print("❌ 有PENDING任务但未被分发，可能原因：")
        print("   1. 进程池计数器错误，认为进程池已满")
        print("   2. 调度器未正常运行")
        print("   3. 数据库连接问题")
        print("\n   建议：重启服务，或手动重置PROCESSING任务")


if __name__ == "__main__":
    # Windows 平台设置
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(diagnose())
