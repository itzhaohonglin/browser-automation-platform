"""
周期性任务功能验证脚本

用途：验证周期性任务调度功能是否正常工作

使用方法：
    python scripts/test_scheduled_tasks.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus


async def test_scheduled_tasks():
    """测试周期性任务功能"""
    print("=" * 60)
    print("周期性任务功能验证")
    print("=" * 60)

    async with get_session() as session:
        # 1. 查找所有配置了周期性调度的配置
        print("\n1. 检查周期性调度配置...")
        stmt = select(CrawlerConfig).where(
            CrawlerConfig.is_active == True,
            CrawlerConfig.deleted_at.is_(None),
            CrawlerConfig.schedule_config.is_not(None)
        )
        result = await session.execute(stmt)
        configs = result.scalars().all()

        if not configs:
            print("   ❌ 未找到配置了周期性调度的采集配置")
            print("\n建议：")
            print("   1. 在数据库中配置 schedule_config 字段")
            print("   2. 参考文档：docs/scheduled_tasks_guide.md")
            return

        print(f"   ✅ 找到 {len(configs)} 个配置了周期性调度的采集配置")

        # 2. 检查每个配置的状态
        print("\n2. 检查配置详情...")
        for config in configs:
            print(f"\n   配置 ID: {config.id}")
            print(f"   配置名称: {config.config_name}")
            print(f"   调度配置: {config.schedule_config}")

            schedule_cfg = config.schedule_config or {}
            enabled = schedule_cfg.get('enabled', False)
            interval = schedule_cfg.get('interval_minutes', 'N/A')

            print(f"   启用状态: {'✅ 已启用' if enabled else '❌ 未启用'}")
            print(f"   执行间隔: {interval} 分钟")

            # 查询该配置的最新任务
            last_job_stmt = select(JobQueue).where(
                JobQueue.config_id == config.id
            ).order_by(JobQueue.created_at.desc()).limit(1)

            last_job_result = await session.execute(last_job_stmt)
            last_job = last_job_result.scalar_one_or_none()

            if last_job:
                print(f"   最新任务 ID: {last_job.id}")
                print(f"   任务状态: {last_job.status.value}")
                print(f"   创建时间: {last_job.created_at}")
                if hasattr(last_job, 'completed_at') and last_job.completed_at:
                    print(f"   完成时间: {last_job.completed_at}")
                else:
                    print(f"   更新时间: {last_job.updated_at}")
            else:
                print("   ⚠️  未找到任何任务")
                print("   建议：创建第一个任务以启动周期性调度")

        # 3. 检查调度器配置
        print("\n3. 检查调度器配置...")
        from app.core.config import settings
        print(f"   检查间隔: {settings.SCHEDULE_CHECK_INTERVAL_MINUTES} 分钟")
        print(f"   首次延迟: {settings.SCHEDULE_FIRST_RUN_DELAY_MINUTES} 分钟")

        # 4. 统计信息
        print("\n4. 任务统计...")
        for config in configs:
            total_stmt = select(JobQueue).where(
                JobQueue.config_id == config.id
            )
            total_result = await session.execute(total_stmt)
            total_jobs = total_result.scalars().all()

            success_count = sum(1 for j in total_jobs if j.status == JobStatus.SUCCESS)
            pending_count = sum(1 for j in total_jobs if j.status == JobStatus.PENDING)
            failed_count = sum(1 for j in total_jobs if j.status == JobStatus.FAILED)

            print(f"\n   配置 #{config.id} ({config.config_name}):")
            print(f"   - 总任务数: {len(total_jobs)}")
            print(f"   - 成功: {success_count}")
            print(f"   - 待处理: {pending_count}")
            print(f"   - 失败: {failed_count}")

    # 5. 测试建议
    print("\n" + "=" * 60)
    print("测试建议")
    print("=" * 60)
    print("\n如果周期性任务未自动创建，请检查：")
    print("1. schedule_config.enabled 是否为 true")
    print("2. 最新任务状态是否为 'success'")
    print("3. 是否已经过了 interval_minutes 时间")
    print("4. 服务是否正在运行（调度器是否启动）")
    print("5. 查看服务日志中的 '开始扫描周期性任务配置' 消息")
    print("\n启动服务后，调度器会每 5 分钟自动检查一次。")


if __name__ == "__main__":
    asyncio.run(test_scheduled_tasks())
