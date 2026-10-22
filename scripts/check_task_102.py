"""检查任务102的详细信息"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from sqlalchemy import select


async def check():
    print("检查任务102-106的详细信息：\n")

    async with get_session() as session:
        # 查询任务102-106
        stmt = select(JobQueue).where(JobQueue.id.between(102, 106)).order_by(JobQueue.id)
        result = await session.execute(stmt)
        jobs = result.scalars().all()

        for job in jobs:
            print(f"任务 #{job.id}:")
            print(f"  status: {job.status.value}")
            print(f"  priority: {job.priority}")
            print(f"  config_id: {job.config_id}")
            print(f"  created_at: {job.created_at}")
            print(f"  updated_at: {job.updated_at}")
            print(f"  retry_count: {job.retry_count}")
            print()

        # 测试调度器的查询
        print("\n模拟调度器查询（按优先级+创建时间排序，limit=5）：")
        stmt = select(JobQueue).where(
            JobQueue.status == JobStatus.PENDING
        ).order_by(
            JobQueue.priority.desc(),
            JobQueue.created_at.asc()
        ).limit(5)

        result = await session.execute(stmt)
        pending_jobs = result.scalars().all()

        if pending_jobs:
            print(f"找到 {len(pending_jobs)} 个任务：")
            for job in pending_jobs:
                print(f"  任务 #{job.id}: priority={job.priority}, created_at={job.created_at}")
        else:
            print("没有找到任何pending任务！")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(check())
