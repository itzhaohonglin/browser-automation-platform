"""
直接查询数据库验证任务
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import text
from app.core.database import get_session


async def check_database():
    """直接查询数据库"""
    print("\n" + "="*60)
    print("  数据库直接查询")
    print("="*60 + "\n")

    async with get_session() as db:
        # 1. 查询配置
        print("[配置表] crawler_configs:")
        result = await db.execute(text("SELECT id, config_name FROM crawler_configs WHERE is_active = 1"))
        configs = result.fetchall()
        for row in configs:
            print(f"  ID: {row[0]}, Name: {row[1]}")

        if not configs:
            print("  [警告] 没有找到活跃的配置")
            return

        config_id = configs[0][0]
        print(f"\n使用配置ID: {config_id}")

        # 2. 查询任务
        print(f"\n[任务表] job_queue (config_id={config_id}):")
        result = await db.execute(
            text("SELECT id, status, query_params FROM job_queue WHERE config_id = :config_id ORDER BY id DESC"),
            {"config_id": config_id}
        )
        jobs = result.fetchall()

        if jobs:
            print(f"  找到 {len(jobs)} 个任务:")
            for row in jobs[:10]:  # 只显示前10个
                print(f"    ID: {row[0]}, Status: {row[1]}, Params: {row[2]}")
        else:
            print("  [警告] 没有找到任务")

        # 3. 统计状态
        print(f"\n[统计] 任务状态分布:")
        result = await db.execute(
            text("SELECT status, COUNT(*) as count FROM job_queue WHERE config_id = :config_id GROUP BY status"),
            {"config_id": config_id}
        )
        stats = result.fetchall()
        for row in stats:
            print(f"  {row[0]}: {row[1]}")

        print("\n" + "="*60)
        print()


if __name__ == "__main__":
    asyncio.run(check_database())
