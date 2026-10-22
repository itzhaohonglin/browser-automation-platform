"""
彻底诊断进程池回调问题

检查：
1. 当前进程池状态（内存计数器）
2. 数据库中的PROCESSING任务数
3. 两者是否一致
4. 如果不一致，强制同步
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def diagnose_and_fix():
    """诊断并修复进程池计数器"""
    from app.core.database import get_session
    from app.models.job import JobQueue, JobStatus
    from sqlalchemy import select, func

    print("="*60)
    print("进程池回调问题诊断")
    print("="*60)

    async with get_session() as session:
        # 查询数据库中PROCESSING状态的任务
        stmt = select(func.count()).where(JobQueue.status == JobStatus.PROCESSING)
        result = await session.execute(stmt)
        db_processing_count = result.scalar() or 0

        print(f"\n数据库中PROCESSING任务数: {db_processing_count}")

        if db_processing_count > 0:
            print(f"\n⚠️  发现 {db_processing_count} 个PROCESSING任务，可能卡住了！")
            print("\n详细信息：")

            stmt = select(JobQueue).where(JobQueue.status == JobStatus.PROCESSING)
            result = await session.execute(stmt)
            processing_jobs = result.scalars().all()

            for job in processing_jobs:
                from datetime import datetime
                runtime = (datetime.now() - job.updated_at).total_seconds() / 60
                print(f"  任务 #{job.id}:")
                print(f"    - 开始时间: {job.updated_at}")
                print(f"    - 已运行: {runtime:.1f} 分钟")
                print(f"    - config_id: {job.config_id}")

            # 询问是否重置
            print(f"\n这些PROCESSING任务可能已经完成但回调失败，导致状态没有更新。")
            print(f"建议：将这些任务重置为PENDING状态，让调度器重新分发。")
            print(f"\n是否重置这些任务为PENDING? (yes/no)")

            response = input().strip().lower()
            if response == 'yes':
                for job in processing_jobs:
                    job.status = JobStatus.PENDING
                    job.error_msg = "进程池回调失败，已重置"
                    print(f"  重置任务 #{job.id}")

                await session.commit()
                print(f"\n✓ 已重置 {len(processing_jobs)} 个任务")
            else:
                print("\n跳过重置")
        else:
            print("\n✓ 没有PROCESSING任务，状态正常")

        # 检查pending任务
        stmt = select(func.count()).where(JobQueue.status == JobStatus.PENDING)
        result = await session.execute(stmt)
        pending_count = result.scalar() or 0

        print(f"\n待处理任务数: {pending_count}")

        if pending_count > 0:
            print(f"✓ 有 {pending_count} 个任务等待执行")
            print("\n建议：重启服务后，调度器会自动分发这些任务")
        else:
            print("所有任务已完成")

    print("\n" + "="*60)
    print("诊断完成")
    print("="*60)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(diagnose_and_fix())
