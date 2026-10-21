"""
检查任务状态和调度器问题
"""
import asyncio
import sys
import io
from pathlib import Path

# 设置 stdout 为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session
from app.models.job import JobQueue
from sqlalchemy import select, func


async def check_tasks():
    """检查任务状态"""
    async with get_session() as session:
        # 统计各状态任务数量
        stmt = select(
            JobQueue.status,
            func.count(JobQueue.id).label('count')
        ).group_by(JobQueue.status)

        result = await session.execute(stmt)
        status_counts = result.all()

        print("=" * 60)
        print("任务状态统计")
        print("=" * 60)
        for status, count in status_counts:
            print(f"{status}: {count} 个任务")

        # 查看最近的 pending 任务
        print("\n" + "=" * 60)
        print("最近的 5 个 pending 任务")
        print("=" * 60)
        stmt = select(JobQueue).where(
            JobQueue.status == 'pending'
        ).order_by(JobQueue.created_at.desc()).limit(5)

        result = await session.execute(stmt)
        pending_jobs = result.scalars().all()

        if pending_jobs:
            for job in pending_jobs:
                print(f"任务 #{job.id}: config_id={job.config_id}, "
                      f"priority={job.priority}, created_at={job.created_at}")
        else:
            print("没有 pending 任务")

        # 查看最近的 processing 任务
        print("\n" + "=" * 60)
        print("最近的 5 个 processing 任务")
        print("=" * 60)
        stmt = select(JobQueue).where(
            JobQueue.status == 'processing'
        ).order_by(JobQueue.created_at.desc()).limit(5)

        result = await session.execute(stmt)
        processing_jobs = result.scalars().all()

        if processing_jobs:
            for job in processing_jobs:
                print(f"任务 #{job.id}: config_id={job.config_id}, "
                      f"started_at={job.started_at}")
        else:
            print("没有 processing 任务")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(check_tasks())
