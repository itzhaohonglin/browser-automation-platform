"""
诊断进程池状态

检查当前进程池的活跃工作进程数和实际数据库中的 processing 任务数
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, func
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus


async def diagnose():
    """诊断进程池状态"""
    print("=" * 60)
    print("进程池状态诊断")
    print("=" * 60)

    async with get_session() as session:
        # 统计各状态任务数
        for status in [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.SUCCESS, JobStatus.FAILED]:
            stmt = select(func.count()).where(JobQueue.status == status)
            result = await session.execute(stmt)
            count = result.scalar()
            print(f"{status.value:12s}: {count:5d} 个任务")

        print("-" * 60)

        # 查询 processing 状态的任务（理论上应该为0或正在执行的任务）
        stmt = select(JobQueue).where(JobQueue.status == JobStatus.PROCESSING)
        result = await session.execute(stmt)
        processing_jobs = result.scalars().all()

        if processing_jobs:
            print(f"\n⚠️  发现 {len(processing_jobs)} 个 PROCESSING 状态的任务:")
            for job in processing_jobs:
                print(f"  - 任务 #{job.id}: 更新时间 {job.updated_at}")
        else:
            print("\n✅ 没有 PROCESSING 状态的任务（进程池应该是空闲的）")

        print("\n" + "=" * 60)
        print("诊断建议:")
        print("=" * 60)

        if processing_jobs:
            print("""
如果这些 PROCESSING 任务已经完成但状态未更新，说明进程池回调失败。

解决方案：
1. 重启应用（会自动将超时的 PROCESSING 任务标记为失败）
2. 手动将这些任务重置为 PENDING:
   UPDATE job_queue SET status='pending' WHERE status='processing';
            """)
        else:
            print("""
数据库中没有 PROCESSING 任务，但调度器无法分发新任务。

可能原因：
1. 进程池的 _active_workers 计数器未正确递减
2. 需要重启应用来重置进程池状态
            """)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(diagnose())
