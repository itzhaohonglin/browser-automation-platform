"""
查找 config_id=45 的配置
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import text
from app.core.database import get_session


async def find_config_45():
    """查找 ID=45 的配置"""
    print("\n" + "="*60)
    print("  查找 config_id=45")
    print("="*60 + "\n")

    async with get_session() as db:
        # 查询 ID=45 的配置
        result = await db.execute(text("""
            SELECT
                id,
                config_name,
                is_active,
                created_at,
                deleted_at
            FROM crawler_configs
            WHERE id = 45
        """))

        config = result.fetchone()

        if config:
            print(f"[找到] ID=45 的配置:")
            print(f"  ID: {config[0]}")
            print(f"  Name: {config[1]}")
            print(f"  Active: {config[2]}")
            print(f"  Created: {config[3]}")
            print(f"  Deleted: {config[4]}")
        else:
            print("[未找到] ID=45 的配置不存在")

        # 查询所有配置
        print(f"\n[所有配置]:")
        result = await db.execute(text("""
            SELECT id, config_name, deleted_at
            FROM crawler_configs
            ORDER BY id
        """))
        all_configs = result.fetchall()

        for row in all_configs:
            status = "(已删除)" if row[2] else ""
            print(f"  ID={row[0]}, Name={row[1]} {status}")

    print("\n" + "="*60)
    print()


if __name__ == "__main__":
    asyncio.run(find_config_45())
