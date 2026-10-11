"""
使用配置ID 14创建任务
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue


async def create_job():
    """创建任务"""

    async with get_session() as session:
        # 创建任务
        job = JobQueue(
            config_id=14,  # 使用刚创建的配置ID
            query_params={"registration_no": "滇械注准20192140008"},
            status="pending"
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        print(f"Job created: ID={job.id}, config_id={job.config_id}, status={job.status}")
        print(f"\nExecute: curl -X POST 'http://127.0.0.1:8000/task/run?config_id=14&limit=1'")

        return job.id


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(create_job())
