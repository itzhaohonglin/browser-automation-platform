"""
查询所有pending任务
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from sqlalchemy import select


async def list_pending_jobs():
    """列出所有pending任务"""

    async with get_session() as session:
        stmt = select(JobQueue).where(
            JobQueue.status == JobStatus.PENDING
        ).order_by(JobQueue.id.desc()).limit(10)

        result = await session.execute(stmt)
        jobs = result.scalars().all()

        print(f"Total pending jobs: {len(jobs)}\n")

        for job in jobs:
            print(f"Job ID: {job.id}, Config ID: {job.config_id}, Created: {job.created_at}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(list_pending_jobs())
