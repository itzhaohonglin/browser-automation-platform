"""直接更新数据库中的 JSON 字段，将 Unicode 转义转换为中文"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.database import get_session


async def fix_unicode_in_database():
    """直接在数据库层面修复 Unicode 转义"""

    async with get_session() as session:
        print("="*80)
        print("修复数据库中的 Unicode 转义")
        print("="*80)

        # 1. 修复 job_queue 表
        print("\n【1. 修复 job_queue.query_params】")

        # 获取所有任务
        result = await session.execute(
            text("SELECT id, query_params FROM job_queue")
        )
        jobs = result.fetchall()

        fixed_count = 0
        for job_id, query_params_str in jobs:
            # 解析 JSON（会自动转换 Unicode 转义）
            query_params = json.loads(query_params_str)

            # 重新序列化（不转义中文）
            fixed_json = json.dumps(query_params, ensure_ascii=False, separators=(',', ':'))

            # 更新数据库
            await session.execute(
                text("UPDATE job_queue SET query_params = :params WHERE id = :id"),
                {"params": fixed_json, "id": job_id}
            )

            fixed_count += 1
            if fixed_count <= 3:
                print(f"  Job {job_id}:")
                print(f"    Before: {query_params_str}")
                print(f"    After:  {fixed_json}")

        print(f"  共修复 {fixed_count} 个任务")

        # 2. 修复 crawler_configs 表的所有 JSON 字段
        print("\n【2. 修复 crawler_configs 的 JSON 字段】")

        result = await session.execute(
            text("SELECT id, config_name, input_configs, fields_mapping, timeout_config, extraction_config FROM crawler_configs")
        )
        configs = result.fetchall()

        fixed_configs = 0
        for config_id, name, input_configs, fields_mapping, timeout_config, extraction_config in configs:
            updates = []
            params = {"id": config_id}

            # 修复 input_configs
            if input_configs:
                parsed = json.loads(input_configs)
                fixed = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
                updates.append("input_configs = :input_configs")
                params["input_configs"] = fixed

            # 修复 fields_mapping
            if fields_mapping:
                parsed = json.loads(fields_mapping)
                fixed = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
                updates.append("fields_mapping = :fields_mapping")
                params["fields_mapping"] = fixed

            # 修复 timeout_config
            if timeout_config:
                parsed = json.loads(timeout_config)
                fixed = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
                updates.append("timeout_config = :timeout_config")
                params["timeout_config"] = fixed

            # 修复 extraction_config
            if extraction_config:
                parsed = json.loads(extraction_config)
                fixed = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
                updates.append("extraction_config = :extraction_config")
                params["extraction_config"] = fixed

            if updates:
                sql = f"UPDATE crawler_configs SET {', '.join(updates)} WHERE id = :id"
                await session.execute(text(sql), params)
                fixed_configs += 1
                print(f"  Config {config_id}: {name}")

        print(f"  共修复 {fixed_configs} 个配置")

        # 3. 修复 crawler_results 表
        print("\n【3. 修复 crawler_results 的 JSON 字段】")

        result = await session.execute(
            text("SELECT id, query_params, extracted_data FROM crawler_results")
        )
        results = result.fetchall()

        fixed_results = 0
        for result_id, query_params, extracted_data in results:
            updates = []
            params = {"id": result_id}

            if query_params:
                parsed = json.loads(query_params)
                fixed = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
                updates.append("query_params = :query_params")
                params["query_params"] = fixed

            if extracted_data:
                parsed = json.loads(extracted_data)
                fixed = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'))
                updates.append("extracted_data = :extracted_data")
                params["extracted_data"] = fixed

            if updates:
                sql = f"UPDATE crawler_results SET {', '.join(updates)} WHERE id = :id"
                await session.execute(text(sql), params)
                fixed_results += 1

        print(f"  共修复 {fixed_results} 个结果")

        # 提交更改
        await session.commit()

        print("\n" + "="*80)
        print("修复完成!")
        print("="*80)

        # 验证修复结果
        print("\n【验证结果】")
        result = await session.execute(
            text("SELECT id, query_params FROM job_queue WHERE id = 1")
        )
        row = result.fetchone()

        if row:
            job_id, query_params = row
            print(f"\nJob ID {job_id}:")
            print(f"  Raw JSON: {query_params}")

            # 检查是否还有 Unicode 转义
            if '\\u' in query_params:
                print("  Status: 仍包含 Unicode 转义")
            else:
                print("  Status: 已转换为中文!")


if __name__ == "__main__":
    asyncio.run(fix_unicode_in_database())
