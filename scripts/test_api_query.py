"""
模拟 API 查询逻辑
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import select
from app.core.database import get_db
from app.models.job import JobQueue, JobStatus


async def test_api_query():
    """模拟 API 的查询逻辑"""
    print("\n" + "="*60)
    print("  模拟 API 查询")
    print("="*60 + "\n")

    config_id = 1
    limit = 10

    print(f"查询参数:")
    print(f"  config_id: {config_id}")
    print(f"  limit: {limit}")
    print(f"  status: {JobStatus.PENDING} ('{JobStatus.PENDING.value}')")
    print()

    # 使用 API 相同的方式获取 db
    async for db in get_db():
        try:
            # 1. 完全相同的查询语句
            stmt = select(JobQueue).where(
                JobQueue.config_id == config_id,
                JobQueue.status == JobStatus.PENDING
            ).limit(limit)

            print(f"执行查询...")
            result = await db.execute(stmt)
            jobs = result.scalars().all()

            print(f"查询结果: 找到 {len(jobs)} 个任务\n")

            if jobs:
                print("任务列表:")
                for job in jobs:
                    print(f"  ID: {job.id}")
                    print(f"    config_id: {job.config_id}")
                    print(f"    status: {job.status}")
                    print(f"    query_params: {job.query_params}")
                    print()
            else:
                print("[警告] 未找到待处理的任务")
                print("\n可能的原因:")
                print("  1. config_id 不匹配")
                print("  2. status 值不匹配")
                print("  3. 数据库连接问题")

        finally:
            break  # 只需要一次迭代

    print("="*60)
    print()


if __name__ == "__main__":
    asyncio.run(test_api_query())
