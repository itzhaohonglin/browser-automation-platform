"""
手动执行任务脚本

使用方法：
    python scripts/execute_job_manual.py --config-id 1 --limit 1
"""

import asyncio
import argparse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from app.services.executor import PlaywrightExecutor
from app.api.websocket import websocket_manager
from sqlalchemy import select


async def execute_jobs(config_id: int, limit: int = 1):
    """手动执行任务"""
    print(f"\n{'='*60}")
    print(f"  手动执行任务")
    print(f"{'='*60}\n")
    print(f"配置ID: {config_id}")
    print(f"执行数量: {limit}")
    print()

    async with get_session() as db:
        # 1. 查询待处理任务
        stmt = select(JobQueue).where(
            JobQueue.config_id == config_id,
            JobQueue.status == JobStatus.PENDING
        ).limit(limit)

        result = await db.execute(stmt)
        jobs = result.scalars().all()

        if not jobs:
            print("[错误] 未找到待处理的任务")
            print(f"\n提示：请先创建配置ID为 {config_id} 的任务")
            return

        print(f"找到 {len(jobs)} 个待处理任务\n")

        # 2. 创建执行器
        executor = PlaywrightExecutor(ws_manager=websocket_manager)

        # 3. 执行任务
        success_count = 0
        failed_count = 0

        for i, job in enumerate(jobs, 1):
            print(f"[{i}/{len(jobs)}] 执行任务 ID: {job.id}")
            print(f"  查询参数: {job.query_params}")

            try:
                result = await executor.execute_job(job.id, db)

                if result.get("status") == "success":
                    print(f"  ✅ 状态: 成功")
                    print(f"  提取数据: {len(result.get('extracted_data', []))} 条记录")
                    print(f"  页数: {result.get('page_count', 0)}")
                    success_count += 1
                else:
                    print(f"  ❌ 状态: 失败")
                    print(f"  错误: {result.get('error', 'Unknown error')}")
                    failed_count += 1

            except Exception as e:
                print(f"  ❌ 状态: 异常")
                print(f"  错误: {str(e)}")
                failed_count += 1

            print()

        # 4. 输出统计
        print(f"{'='*60}")
        print(f"  执行完成")
        print(f"{'='*60}")
        print(f"总数: {len(jobs)}")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print(f"成功率: {success_count / len(jobs) * 100:.1f}%")
        print()


def main():
    parser = argparse.ArgumentParser(description='手动执行任务')
    parser.add_argument(
        '--config-id',
        type=int,
        required=True,
        help='配置ID'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=1,
        help='执行任务数量（默认1，最大10）'
    )

    args = parser.parse_args()

    # 限制最大数量
    limit = min(args.limit, 10)

    # 执行任务
    asyncio.run(execute_jobs(args.config_id, limit))


if __name__ == "__main__":
    main()
