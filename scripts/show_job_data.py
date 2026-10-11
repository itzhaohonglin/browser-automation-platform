"""显示任务采集数据"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.result import CrawlerResult
from sqlalchemy import select

async def show_data(job_id):
    async with get_session() as session:
        result = await session.execute(
            select(CrawlerResult).where(CrawlerResult.job_id == job_id)
        )
        row = result.scalar_one_or_none()

        if not row:
            print(f'未找到Job {job_id}的结果')
            return

        # 解析extracted_data
        if isinstance(row.extracted_data, str):
            data = json.loads(row.extracted_data)
        else:
            data = row.extracted_data

        print('=' * 80)
        print(f'Job {job_id} 采集结果')
        print('=' * 80)
        print(f'页数: {row.page_count}')

        items = data.get('items', [])
        print(f'总记录数: {len(items)}')
        print(f'items类型: {type(items)}')
        if items:
            print(f'第一个item类型: {type(items[0])}')
            print(f'第一个item内容: {repr(items[0])[:200]}')

        for i, item in enumerate(items, 1):
            # 如果item是字符串，需要解析
            if isinstance(item, str):
                if not item.strip():  # 空字符串
                    print(f'\n记录 {i}: 空数据，跳过')
                    continue
                try:
                    item = json.loads(item)
                except json.JSONDecodeError as e:
                    print(f'\n记录 {i}: JSON解析失败: {e}')
                    print(f'原始数据: {repr(item)[:200]}')
                    continue

            print(f'\n{"=" * 80}')
            print(f'记录 {i}')
            print("=" * 80)

            # 列表数据
            list_data = item.get('list_data', {})
            print(f'\n【列表数据】({len(list_data)} 个字段):')
            for key, value in list_data.items():
                print(f'  {key}: {value}')

            # 详情数据
            detail_data = item.get('detail_data', {})
            detail_status = item.get('detail_status', 'unknown')
            print(f'\n【详情数据】(状态: {detail_status}, {len(detail_data)} 个字段):')

            if detail_data:
                for key, value in detail_data.items():
                    # 处理长文本
                    if value and len(str(value)) > 100:
                        display_value = str(value)[:100] + '...'
                    else:
                        display_value = value
                    print(f'  {key}: {display_value}')
            else:
                print('  (无详情数据)')

        # 汇总统计
        summary = data.get('summary', {})
        if summary:
            print(f'\n{"=" * 80}')
            print('【汇总统计】')
            print("=" * 80)
            for key, value in summary.items():
                print(f'  {key}: {value}')

if __name__ == "__main__":
    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 52
    asyncio.run(show_data(job_id))
