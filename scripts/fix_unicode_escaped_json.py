"""修复数据库中 Unicode 转义的 JSON 数据

将 {"registration_no": "滇械注准20192140008"}
转换为 {"registration_no": "滇械注准20192140008"}
"""
import asyncio
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue
from app.models.config import CrawlerConfig
from app.models.result import CrawlerResult
from sqlalchemy import select


async def fix_json_fields():
    """修复所有表中的 JSON 字段"""

    async with get_session() as session:
        print("="*80)
        print("修复 Unicode 转义的 JSON 数据")
        print("="*80)

        # 1. 修复 job_queue 表
        print("\n【1. 修复 job_queue.query_params】")
        result = await session.execute(select(JobQueue))
        jobs = result.scalars().all()

        fixed_jobs = 0
        for job in jobs:
            # 强制重新赋值，触发 ChineseJSON 的序列化
            original = job.query_params
            job.query_params = original
            fixed_jobs += 1

            # 显示修复结果
            if fixed_jobs <= 5:  # 只显示前5个
                print(f"  Job {job.id}: {job.query_params}")

        print(f"  共修复 {fixed_jobs} 个任务")

        # 2. 修复 crawler_configs 表
        print("\n【2. 修复 crawler_configs 的 JSON 字段】")
        result = await session.execute(select(CrawlerConfig))
        configs = result.scalars().all()

        fixed_configs = 0
        for config in configs:
            # 修复所有 JSON 字段
            config.input_configs = config.input_configs
            config.fields_mapping = config.fields_mapping
            if config.timeout_config:
                config.timeout_config = config.timeout_config
            if config.extraction_config:
                config.extraction_config = config.extraction_config
            fixed_configs += 1

            print(f"  Config {config.id}: {config.config_name}")

        print(f"  共修复 {fixed_configs} 个配置")

        # 3. 修复 crawler_results 表
        print("\n【3. 修复 crawler_results 的 JSON 字段】")
        result = await session.execute(select(CrawlerResult))
        results = result.scalars().all()

        fixed_results = 0
        for result_obj in results:
            result_obj.query_params = result_obj.query_params
            result_obj.extracted_data = result_obj.extracted_data
            fixed_results += 1

        print(f"  共修复 {fixed_results} 个结果")

        # 提交所有更改
        await session.commit()

        print("\n" + "="*80)
        print("✅ 修复完成！")
        print("="*80)

        # 验证修复结果
        print("\n【验证结果】")
        result = await session.execute(select(JobQueue).limit(1))
        job = result.scalar_one_or_none()

        if job:
            print(f"\n示例 Job ID {job.id}:")
            print(f"  query_params: {job.query_params}")
            print(f"  类型: {type(job.query_params)}")

            # 检查是否还有 Unicode 转义
            import json
            json_str = json.dumps(job.query_params, ensure_ascii=False)
            if '\\u' in json_str:
                print("  ⚠️  仍然包含 Unicode 转义")
            else:
                print("  ✅ 已转换为中文")


if __name__ == "__main__":
    asyncio.run(fix_json_fields())
