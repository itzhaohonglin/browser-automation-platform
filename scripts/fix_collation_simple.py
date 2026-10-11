"""
简化版排序规则修复脚本
专注于修改业务数据相关的列
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.database import get_session


async def fix_collation_simple():
    """修复关键业务表的排序规则"""

    print("修复数据库排序规则 - 简化版")
    print("="*60)

    # 定义需要修改的列（表名, 列名, 数据类型）
    columns_to_fix = [
        # crawler_configs - 配置表
        ("crawler_configs", "config_name", "NVARCHAR(100)"),
        ("crawler_configs", "target_url", "NVARCHAR(500)"),
        ("crawler_configs", "auth_profile", "NVARCHAR(50)"),
        ("crawler_configs", "login_url", "NVARCHAR(500)"),
        ("crawler_configs", "input_configs", "NVARCHAR(MAX)"),
        ("crawler_configs", "submit_selector", "NVARCHAR(200)"),
        ("crawler_configs", "wait_selector", "NVARCHAR(200)"),
        ("crawler_configs", "fields_mapping", "NVARCHAR(MAX)"),
        ("crawler_configs", "pagination_selector", "NVARCHAR(200)"),
        ("crawler_configs", "timeout_config", "NVARCHAR(MAX)"),
        ("crawler_configs", "extraction_config", "NVARCHAR(MAX)"),

        # job_queue - 任务队列
        ("job_queue", "query_params", "NVARCHAR(MAX)"),
        ("job_queue", "error_msg", "NVARCHAR(MAX)"),

        # crawler_results - 结果表（最重要）
        ("crawler_results", "extracted_data", "NVARCHAR(MAX)"),
        ("crawler_results", "query_params", "NVARCHAR(MAX)"),
    ]

    async with get_session() as session:
        success = 0
        failed = 0

        for table_name, column_name, data_type in columns_to_fix:
            try:
                sql = f"""
                    ALTER TABLE [{table_name}]
                    ALTER COLUMN [{column_name}] {data_type}
                    COLLATE Chinese_PRC_CI_AS NULL
                """
                await session.execute(text(sql))
                print(f"[OK] {table_name}.{column_name}")
                success += 1
            except Exception as e:
                print(f"[FAIL] {table_name}.{column_name}: {str(e)[:80]}")
                failed += 1

        await session.commit()

        print("="*60)
        print(f"完成: 成功 {success} 个, 失败 {failed} 个")

        # 验证最关键的列
        print("\n验证关键列:")
        result = await session.execute(text("""
            SELECT c.collation_name
            FROM sys.columns c
            JOIN sys.tables t ON c.object_id = t.object_id
            WHERE t.name = 'crawler_results'
            AND c.name = 'extracted_data'
        """))
        collation = result.scalar()
        if collation == 'Chinese_PRC_CI_AS':
            print(f"[OK] crawler_results.extracted_data: {collation}")
        else:
            print(f"[FAIL] crawler_results.extracted_data: {collation}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(fix_collation_simple())
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
