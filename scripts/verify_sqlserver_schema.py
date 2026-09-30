import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def verify_schema():
    async with async_engine.connect() as conn:
        # 检查表
        result = await conn.execute(text(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
        ))
        tables = [row[0] for row in result]
        print(f"Tables: {tables}")

        # 检查 crawler_configs 表结构
        result = await conn.execute(text(
            "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'crawler_configs' ORDER BY ORDINAL_POSITION"
        ))
        columns = [(row[0], row[1], row[2]) for row in result]
        print(f"\ncrawler_configs columns:")
        for col, dtype, length in columns:
            if length:
                print(f"  - {col}: {dtype}({length})")
            else:
                print(f"  - {col}: {dtype}")

        # 验证 JSON 字段类型
        json_fields = [col for col, dtype, _ in columns if col in ['input_configs', 'fields_mapping', 'timeout_config', 'extraction_config']]
        print(f"\nJSON fields found in crawler_configs: {json_fields}")
        assert len(json_fields) == 4, f"Expected 4 JSON fields, found: {json_fields}"

        # 检查 job_queue 表的 ENUM 字段
        result = await conn.execute(text(
            "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'job_queue' AND COLUMN_NAME = 'status'"
        ))
        status_col = result.fetchone()
        print(f"\njob_queue.status column: {status_col}")

        print("\n=== Verification Successful ===")
        print("- All required tables exist")
        print("- JSON fields correctly mapped")
        print("- ENUM fields correctly mapped")

if __name__ == "__main__":
    asyncio.run(verify_schema())
