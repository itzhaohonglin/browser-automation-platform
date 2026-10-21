"""
检查数据库配置和创建测试任务
"""
import asyncio
import sys
import io
from pathlib import Path

# 设置 stdout 为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue
from sqlalchemy import select


async def check_and_create():
    """检查配置并创建测试任务"""
    async with get_session() as session:
        # 查看所有配置
        stmt = select(CrawlerConfig).order_by(CrawlerConfig.id.asc())
        result = await session.execute(stmt)
        configs = result.scalars().all()

        print("=" * 60)
        print("数据库中的采集配置")
        print("=" * 60)

        if not configs:
            print("❌ 数据库中没有任何采集配置！")
            print("\n请先运行初始化脚本创建配置：")
            print("  python scripts/init_nhsa_registration_config.py")
            return

        for config in configs:
            print(f"ID: {config.id}")
            print(f"  名称: {config.config_name}")
            print(f"  目标URL: {config.target_url}")
            print(f"  是否启用: {config.is_active}")
            print()

        # 使用第一个配置创建测试任务
        first_config = configs[0]
        print("=" * 60)
        print(f"使用配置 #{first_config.id} 创建测试任务")
        print("=" * 60)

        # 创建一个测试任务
        test_job = JobQueue(
            config_id=first_config.id,
            query_params={"test_param": "test_value"},
            priority=5
        )
        session.add(test_job)
        await session.commit()

        print(f"✓ 成功创建测试任务 #{test_job.id}")
        print(f"  配置ID: {test_job.config_id}")
        print(f"  状态: {test_job.status}")
        print(f"  优先级: {test_job.priority}")
        print("\n等待调度器分发任务（最多等待 1 分钟）...")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(check_and_create())
