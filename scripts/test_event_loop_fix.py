"""
测试事件循环关闭修复

验证在进程池中执行任务后，数据库连接能够正确关闭，
不会抛出 "RuntimeError: Event loop is closed" 错误。
"""
import asyncio
import sys
import os
import io

# 设置 stdout 为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.process_pool import ProcessPoolManager
from app.core.database import get_session
from app.models.job import JobQueue
from sqlalchemy import select


async def create_test_job():
    """创建一个测试任务"""
    async with get_session() as session:
        # 查找任意一个任务（优先 pending，其次任何状态）
        stmt = select(JobQueue).limit(1)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            print("❌ 数据库中没有任何任务")
            print("请先创建一些任务")
            return None

        # 如果任务不是 pending，将其重置为 pending
        if job.status != "pending":
            print(f"→ 找到任务 ID={job.id} (状态: {job.status})，重置为 pending 用于测试")
            job.status = "pending"
            job.error_msg = None
            await session.commit()

        print(f"✓ 使用测试任务: ID={job.id}, Config={job.config_id}, Status={job.status}")
        return job.id


async def main():
    """主测试流程"""
    print("=" * 60)
    print("事件循环关闭修复测试")
    print("=" * 60)

    # 1. 创建测试任务
    print("\n[1/4] 查找测试任务...")
    job_id = await create_test_job()
    if not job_id:
        return

    # 2. 启动进程池
    print("\n[2/4] 启动进程池...")
    pool = ProcessPoolManager(max_workers=1)
    await pool.start()
    print("✓ 进程池已启动")

    # 3. 提交任务到进程池
    print(f"\n[3/4] 提交任务 {job_id} 到进程池...")
    try:
        future = await pool.submit_job(job_id)
        result = await future
        print(f"✓ 任务执行完成: status={result.get('status', 'unknown')}")
    except Exception as e:
        print(f"❌ 任务执行失败: {e}")
        import traceback
        traceback.print_exc()

    # 4. 等待一段时间，检查是否有事件循环错误
    print("\n[4/4] 等待并检查错误日志...")
    await asyncio.sleep(2)

    # 5. 关闭进程池
    print("\n[5/4] 关闭进程池...")
    await pool.shutdown(wait=True)
    print("✓ 进程池已关闭")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n检查点：")
    print("1. 任务是否成功执行？")
    print("2. 是否出现 'RuntimeError: Event loop is closed' 错误？")
    print("3. 数据库连接是否正确关闭？")
    print("\n如果没有看到上述错误，说明修复成功！")


if __name__ == "__main__":
    # Windows 平台设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
