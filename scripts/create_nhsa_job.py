"""
创建NHSA注册证号采集任务

直接向数据库插入任务记录
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.job import JobQueue, JobStatus
from app.models.config import CrawlerConfig
from sqlalchemy import select


async def create_job():
    """创建采集任务"""

    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            # 1. 验证配置是否存在
            stmt = select(CrawlerConfig).where(CrawlerConfig.id == 44)
            result = await session.execute(stmt)
            config = result.scalar_one_or_none()

            if not config:
                print("错误：配置ID 44 不存在")
                return

            print(f"找到配置：{config.config_name}")

            # 2. 创建任务
            job = JobQueue(
                config_id=44,
                query_params={"registration_no": "滇械注准20192140008"},
                status=JobStatus.PENDING,
                retry_count=0
            )

            session.add(job)
            await session.commit()
            await session.refresh(job)

            print(f"\n任务创建成功！")
            print(f"  任务ID: {job.id}")
            print(f"  配置ID: {job.config_id}")
            print(f"  状态: {job.status}")
            print(f"  查询参数: {job.query_params}")
            print(f"  创建时间: {job.created_at}")

            print(f"\n执行命令：")
            print(f"  curl -X POST 'http://127.0.0.1:8000/task/run?config_id=44&limit=1'")

            return job.id
        finally:
            await session.close()


if __name__ == "__main__":
    # Windows平台设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    job_id = asyncio.run(create_job())
