"""
快速创建NHSA采集任务并执行
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue


async def create_and_list_job():
    """创建任务"""

    async with get_session() as session:
        # 查找最新的NHSA配置
        from sqlalchemy import select, desc

        stmt = select(CrawlerConfig).where(
            CrawlerConfig.config_name.like('%NHSA%')
        ).order_by(desc(CrawlerConfig.id)).limit(1)

        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            print("ERROR: No NHSA config found")
            return

        print(f"Using config ID: {config.id} - {config.config_name}")

        # 创建任务
        job = JobQueue(
            config_id=config.id,
            query_params={"registration_no": "滇械注准20192140008"},
            status="pending"
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        print(f"\nJob created successfully!")
        print(f"  Job ID: {job.id}")
        print(f"  Config ID: {job.config_id}")
        print(f"  Status: {job.status}")

        print(f"\nExecute with:")
        print(f"  curl -X POST 'http://127.0.0.1:8000/task/run?config_id={config.id}&limit=1'")

        return job.id, config.id


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(create_and_list_job())
