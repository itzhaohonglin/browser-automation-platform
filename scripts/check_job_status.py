"""
查询任务状态
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue
from sqlalchemy import select


async def check_job_status(job_id):
    """查询任务状态"""

    async with get_session() as session:
        stmt = select(JobQueue).where(JobQueue.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            print(f"Job {job_id} not found")
            return

        print(f"Job ID: {job.id}")
        print(f"Config ID: {job.config_id}")
        print(f"Status: {job.status}")
        print(f"Query Params: {job.query_params}")
        print(f"Retry Count: {job.retry_count}")
        print(f"Error Message: {job.error_msg if job.error_msg else 'None'}")
        print(f"Created At: {job.created_at}")
        print(f"Completed At: {job.completed_at if job.completed_at else 'Not completed'}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    asyncio.run(check_job_status(job_id))
