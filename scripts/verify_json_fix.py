"""验证 JSON 修复结果"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue
from sqlalchemy import select, text


async def verify():
    async with get_session() as session:
        # 检查前10个任务
        result = await session.execute(
            select(JobQueue).order_by(JobQueue.id).limit(10)
        )
        jobs = result.scalars().all()

        print('=' * 80)
        print('验证修复结果 - 检查前10个任务')
        print('=' * 80)

        success_count = 0
        failed_count = 0

        for job in jobs:
            raw_result = await session.execute(
                text('SELECT query_params FROM job_queue WHERE id = :id'),
                {'id': job.id}
            )
            raw_value = raw_result.scalar_one()

            # 检查是否还有双重转义
            has_double_backslash = '\\\\' in raw_value
            has_unicode_escape = '\\u' in raw_value and not has_double_backslash

            print(f'\nID={job.id}:')
            print(f'  数据库原始: {raw_value[:60]}...')
            print(f'  ORM 读取: {job.query_params}')

            if has_double_backslash:
                print(f'  [FAIL] 仍有双重转义')
                failed_count += 1
            elif has_unicode_escape:
                print(f'  [WARN] 有 Unicode 转义（但这是正常的）')
                success_count += 1
            else:
                print(f'  [OK] 正常')
                success_count += 1

        print('\n' + '=' * 80)
        print(f'修复成功: {success_count}/{len(jobs)}')
        print(f'仍有问题: {failed_count}/{len(jobs)}')
        print('=' * 80)


if __name__ == '__main__':
    asyncio.run(verify())
