"""修复已存在的双重转义 JSON 数据

问题：旧版本的 ChineseJSON 导致数据被双重序列化
修复：重新解析并保存所有受影响的记录
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text
from app.core.database import get_session
from app.models.job import JobQueue
from app.models.result import CrawlerResult
from app.models.config import CrawlerConfig


async def fix_job_queue():
    """修复 job_queue 表的 query_params 字段"""
    print("=" * 80)
    print("修复 job_queue.query_params")
    print("=" * 80)

    async with get_session() as session:
        # 查询所有任务
        result = await session.execute(select(JobQueue))
        jobs = result.scalars().all()

        print(f"\n共找到 {len(jobs)} 个任务")

        fixed_count = 0
        error_count = 0

        for job in jobs:
            try:
                # 检查是否需要修复
                raw_result = await session.execute(
                    text('SELECT query_params FROM job_queue WHERE id = :id'),
                    {'id': job.id}
                )
                raw_value = raw_result.scalar_one()

                # 判断是否有双重转义（包含 \\" 或 \\u）
                if '\\u' in raw_value or '\\"' in raw_value:
                    # 需要修复：双重 JSON 解析
                    try:
                        # 第一次解析：移除外层引号和反斜杠转义
                        if raw_value.startswith('"') and raw_value.endswith('"'):
                            # 使用 json.loads 解析，它会自动处理 \" 和 \uXXXX
                            first_parse = json.loads(raw_value)
                        else:
                            first_parse = raw_value

                        # 第二次解析：将 JSON 字符串转为 dict
                        if isinstance(first_parse, str):
                            parsed = json.loads(first_parse)
                        else:
                            parsed = first_parse

                        # 验证结果
                        if not isinstance(parsed, dict):
                            print(f"  [WARN] 任务 ID={job.id} 解析结果不是 dict: {type(parsed)}")
                            error_count += 1
                            continue

                        # 更新记录
                        job.query_params = parsed
                        fixed_count += 1

                        if fixed_count % 100 == 0:
                            print(f"  已修复 {fixed_count} 个任务...")

                    except Exception as e:
                        print(f"  [ERROR] 任务 ID={job.id} 修复失败: {e}")
                        print(f"    原始值: {raw_value[:100]}...")
                        error_count += 1

            except Exception as e:
                print(f"  [ERROR] 任务 ID={job.id} 检查失败: {e}")
                error_count += 1

        # 提交更改
        if fixed_count > 0:
            await session.commit()
            print(f"\n✓ 成功修复 {fixed_count} 个任务")
        else:
            print(f"\n✓ 没有需要修复的任务")

        if error_count > 0:
            print(f"✗ {error_count} 个任务修复失败")


async def fix_crawler_results():
    """修复 crawler_results 表的 extracted_data 字段"""
    print("\n" + "=" * 80)
    print("修复 crawler_results.extracted_data")
    print("=" * 80)

    async with get_session() as session:
        # 查询所有结果
        result = await session.execute(select(CrawlerResult))
        results = result.scalars().all()

        print(f"\n共找到 {len(results)} 个结果记录")

        fixed_count = 0
        error_count = 0

        for res in results:
            try:
                # 检查是否需要修复
                raw_result = await session.execute(
                    text('SELECT extracted_data FROM crawler_results WHERE id = :id'),
                    {'id': res.id}
                )
                raw_value = raw_result.scalar_one()

                # 判断是否有双重转义
                if raw_value and ('\\u' in raw_value or '\\"' in raw_value):
                    try:
                        # 双重解析
                        if raw_value.startswith('"') and raw_value.endswith('"'):
                            first_parse = json.loads(raw_value)
                        else:
                            first_parse = raw_value

                        if isinstance(first_parse, str):
                            parsed = json.loads(first_parse)
                        else:
                            parsed = first_parse

                        # 更新记录
                        res.extracted_data = parsed
                        fixed_count += 1

                        if fixed_count % 50 == 0:
                            print(f"  已修复 {fixed_count} 个结果...")

                    except Exception as e:
                        print(f"  [ERROR] 结果 ID={res.id} 修复失败: {e}")
                        error_count += 1

            except Exception as e:
                print(f"  [ERROR] 结果 ID={res.id} 检查失败: {e}")
                error_count += 1

        # 提交更改
        if fixed_count > 0:
            await session.commit()
            print(f"\n✓ 成功修复 {fixed_count} 个结果")
        else:
            print(f"\n✓ 没有需要修复的结果")

        if error_count > 0:
            print(f"✗ {error_count} 个结果修复失败")


async def fix_crawler_configs():
    """修复 crawler_configs 表的 JSON 字段"""
    print("\n" + "=" * 80)
    print("修复 crawler_configs 的 JSON 字段")
    print("=" * 80)

    async with get_session() as session:
        result = await session.execute(select(CrawlerConfig))
        configs = result.scalars().all()

        print(f"\n共找到 {len(configs)} 个配置")

        fixed_count = 0

        for config in configs:
            try:
                # 检查并修复所有 JSON 字段
                fields_to_check = [
                    'input_configs',
                    'fields_mapping',
                    'timeout_config',
                    'extraction_config'
                ]

                config_fixed = False

                for field_name in fields_to_check:
                    raw_result = await session.execute(
                        text(f'SELECT {field_name} FROM crawler_configs WHERE id = :id'),
                        {'id': config.id}
                    )
                    raw_value = raw_result.scalar_one()

                    if raw_value and ('\\u' in raw_value or '\\"' in raw_value):
                        try:
                            # 双重解析
                            if raw_value.startswith('"') and raw_value.endswith('"'):
                                first_parse = json.loads(raw_value)
                            else:
                                first_parse = raw_value

                            if isinstance(first_parse, str):
                                parsed = json.loads(first_parse)
                            else:
                                parsed = first_parse

                            setattr(config, field_name, parsed)
                            config_fixed = True

                        except Exception as e:
                            print(f"  [ERROR] 配置 ID={config.id} 字段 {field_name} 修复失败: {e}")

                if config_fixed:
                    fixed_count += 1

            except Exception as e:
                print(f"  [ERROR] 配置 ID={config.id} 检查失败: {e}")

        if fixed_count > 0:
            await session.commit()
            print(f"\n✓ 成功修复 {fixed_count} 个配置")
        else:
            print(f"\n✓ 没有需要修复的配置")


async def verify_fix():
    """验证修复结果"""
    print("\n" + "=" * 80)
    print("验证修复结果")
    print("=" * 80)

    async with get_session() as session:
        # 随机检查几个任务
        result = await session.execute(
            select(JobQueue).order_by(JobQueue.id.desc()).limit(5)
        )
        jobs = result.scalars().all()

        print("\n检查最新的5个任务:")
        for job in jobs:
            raw_result = await session.execute(
                text('SELECT query_params FROM job_queue WHERE id = :id'),
                {'id': job.id}
            )
            raw_value = raw_result.scalar_one()

            has_escape = '\\u' in raw_value or '\\"' in raw_value
            status = "❌ 仍有转义" if has_escape else "✓ 正常"

            print(f"  ID={job.id}: {status}")
            print(f"    ORM: {job.query_params}")


async def main():
    """主函数"""
    print("开始修复数据库中的双重转义 JSON 数据...\n")

    try:
        # 1. 修复任务队列
        await fix_job_queue()

        # 2. 修复采集结果
        await fix_crawler_results()

        # 3. 修复采集配置
        await fix_crawler_configs()

        # 4. 验证修复
        await verify_fix()

        print("\n" + "=" * 80)
        print("修复完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] 修复过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
