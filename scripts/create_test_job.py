"""
创建测试任务用于验证详情列表采集
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue


async def create_test_job():
    """创建测试任务"""

    async with get_session() as session:
        # 创建任务
        test_job = JobQueue(
            config_id=1,
            query_params={
                "registration_no": "滇械注准20192140008"
            }
        )
        session.add(test_job)
        await session.commit()
        await session.refresh(test_job)

        print(f"Test job created: ID = {test_job.id}")
        print(f"Config ID: {test_job.config_id}")
        print(f"Query params: {test_job.query_params}")
        print(f"\nExecute with: python scripts/execute_job_direct.py {test_job.id}")

        return test_job.id


if __name__ == "__main__":
    try:
        job_id = asyncio.run(create_test_job())
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
