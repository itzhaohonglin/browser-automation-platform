"""
使用新的注册证号创建任务
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue


async def create_job_new_reg_no():
    """创建任务 - 使用新的注册证号"""

    async with get_session() as session:
        # 使用不同的注册证号
        job = JobQueue(
            config_id=14,
            query_params={"registration_no": "京械注准20210001234"},  # 新注册证号
            status="pending"
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        print(f"Job created: ID={job.id}, config_id={job.config_id}, status={job.status}")
        print(f"Registration No: 京械注准20210001234")
        print(f"\nExecute: python scripts/execute_job_direct.py {job.id}")

        return job.id


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(create_job_new_reg_no())
