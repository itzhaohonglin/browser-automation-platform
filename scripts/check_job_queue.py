"""
检查任务队列状态
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import select, func
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus


async def check_jobs():
    """检查任务队列"""
    print("\n" + "="*60)
    print("  任务队列状态检查")
    print("="*60 + "\n")

    async with get_session() as db:
        # 1. 统计所有任务
        total_stmt = select(func.count(JobQueue.id))
        total_result = await db.execute(total_stmt)
        total = total_result.scalar() or 0

        print(f"[统计] 总任务数: {total}")

        if total == 0:
            print("\n[警告] 数据库中没有任何任务")
            print("\n提示：请先创建任务，可以使用以下方式：")
            print("  1. 批量导入脚本：python scripts/batch_import_registration_jobs.py")
            print("  2. 手动创建脚本：python scripts/create_nhsa_job.py")
            print()
            return

        # 2. 按状态统计
        for status in JobStatus:
            stmt = select(func.count(JobQueue.id)).where(JobQueue.status == status)
            result = await db.execute(stmt)
            count = result.scalar() or 0
            if count > 0:
                print(f"  - {status.value}: {count}")

        # 3. 按配置统计
        print(f"\n[配置] 按配置统计：")
        stmt = select(
            JobQueue.config_id,
            func.count(JobQueue.id).label('count')
        ).group_by(JobQueue.config_id)

        result = await db.execute(stmt)
        config_stats = result.all()

        for config_id, count in config_stats:
            print(f"  - 配置 ID {config_id}: {count} 个任务")

            # 查询该配置下的待处理任务
            pending_stmt = select(func.count(JobQueue.id)).where(
                JobQueue.config_id == config_id,
                JobQueue.status == JobStatus.PENDING
            )
            pending_result = await db.execute(pending_stmt)
            pending_count = pending_result.scalar() or 0

            if pending_count > 0:
                print(f"    [OK] 其中 {pending_count} 个待处理")
            else:
                print(f"    [注意] 没有待处理任务")

        # 4. 显示待处理任务详情
        print(f"\n[详情] 待处理任务详情：")
        stmt = select(JobQueue).where(
            JobQueue.status == JobStatus.PENDING
        ).limit(5)

        result = await db.execute(stmt)
        pending_jobs = result.scalars().all()

        if pending_jobs:
            for job in pending_jobs:
                print(f"\n  任务 ID: {job.id}")
                print(f"  配置 ID: {job.config_id}")
                print(f"  查询参数: {job.query_params}")
                print(f"  创建时间: {job.created_at}")
        else:
            print("  [注意] 没有待处理任务")

        print("\n" + "="*60)
        print()


if __name__ == "__main__":
    asyncio.run(check_jobs())
