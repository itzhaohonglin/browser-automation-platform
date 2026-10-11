"""
直接查询配置表的真实ID
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import text
from app.core.database import get_session


async def check_config_ids():
    """直接查询配置表"""
    print("\n" + "="*60)
    print("  配置表 ID 检查")
    print("="*60 + "\n")

    async with get_session() as db:
        # 原始 SQL 查询
        result = await db.execute(text("""
            SELECT
                id,
                config_name,
                is_active,
                created_at
            FROM crawler_configs
            ORDER BY id
        """))

        configs = result.fetchall()

        print(f"配置总数: {len(configs)}\n")

        for row in configs:
            print(f"ID: {row[0]}")
            print(f"  Name: {row[1]}")
            print(f"  Active: {row[2]}")
            print(f"  Created: {row[3]}")
            print()

    print("="*60)
    print()


if __name__ == "__main__":
    asyncio.run(check_config_ids())
