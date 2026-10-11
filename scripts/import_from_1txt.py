"""
从 docs/1.txt 批量导入注册证号任务

功能：
1. 读取 docs/1.txt 文件（每行一个注册证号）
2. 批量创建采集任务到数据库
3. 显示导入统计信息

使用方法：
python scripts/import_from_1txt.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue


async def import_from_docs_1txt():
    """从 docs/1.txt 批量导入注册证号任务"""

    print("=" * 80)
    print("从 docs/1.txt 批量导入注册证号任务")
    print("=" * 80)

    # 读取文件
    file_path = project_root / "docs" / "1.txt"
    if not file_path.exists():
        print(f"[ERROR] 文件不存在: {file_path}")
        return

    print(f"\n[1/4] 读取文件: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 解析注册证号（跳过空行和注释）
    registration_numbers = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            registration_numbers.append(line)

    print(f"      [OK] 读取到 {len(registration_numbers)} 个注册证号")

    # 连接数据库
    print(f"\n[2/4] 连接数据库...")
    async with get_session() as session:
        # 查找配置（优先使用最新的 NHSA 注册证号查询配置）
        from sqlalchemy import select, desc
        stmt = select(CrawlerConfig).where(
            CrawlerConfig.config_name.contains("注册证号")
        ).order_by(desc(CrawlerConfig.id))

        result = await session.execute(stmt)
        config = result.scalars().first()

        if not config:
            print("      [ERROR] 未找到 NHSA 注册证号查询配置")
            print("      请先运行: python scripts/init_nhsa_registration_config.py")
            return

        print(f"      [OK] 使用配置: {config.config_name} (ID: {config.id})")

        # 批量创建任务
        print(f"\n[3/4] 批量创建任务...")
        created_jobs = []
        batch_size = 100  # 每批提交100个

        for idx, reg_no in enumerate(registration_numbers, 1):
            job = JobQueue(
                config_id=config.id,
                query_params={"registration_no": reg_no},
                status="pending"
            )
            session.add(job)

            # 每100个或最后一批提交一次
            if idx % batch_size == 0 or idx == len(registration_numbers):
                await session.flush()
                print(f"      进度: {idx}/{len(registration_numbers)} ({idx*100//len(registration_numbers)}%)")

        await session.commit()

        # 获取创建的任务ID范围
        from sqlalchemy import func
        stmt = select(JobQueue.id).where(
            JobQueue.config_id == config.id
        ).order_by(JobQueue.id)

        result = await session.execute(stmt)
        all_job_ids = [row[0] for row in result.fetchall()]

        print(f"      [OK] 成功创建 {len(registration_numbers)} 个任务")
        if all_job_ids:
            print(f"      [OK] 任务ID范围: {min(all_job_ids)} - {max(all_job_ids)}")

    # 输出执行说明
    print(f"\n[4/4] 执行说明")
    print("=" * 80)

    print("\n方法1：通过前端看板执行")
    print("  1. 启动服务: startup.bat 或 python -m app.main")
    print("  2. 访问看板: http://127.0.0.1:8000/static/index.html")
    print("  3. 在任务管理页面找到任务并执行")

    print("\n方法2：通过调度器自动执行")
    print("  调度器每30分钟自动扫描 pending 状态的任务并执行")
    print("  只需启动服务，等待调度器自动处理")

    print("\n方法3：通过API批量执行（高级）")
    if all_job_ids:
        print(f"  for job_id in {{{min(all_job_ids)}..{max(all_job_ids)}}}")
        print("    curl -X POST http://127.0.0.1:8000/api/jobs/$job_id/execute")

    print("\n" + "=" * 80)
    print("导入完成！")
    print("=" * 80)
    print(f"\n统计信息:")
    print(f"  - 配置ID: {config.id}")
    print(f"  - 配置名称: {config.config_name}")
    print(f"  - 导入数量: {len(registration_numbers)} 个任务")
    print(f"  - 任务状态: pending（等待执行）")

    print("\n提示:")
    print("  - 任务会按顺序执行，每个任务大约需要 10-30 秒")
    print(f"  - 预计总耗时: {len(registration_numbers) * 20 / 60:.1f} 分钟")
    print("  - 可以在前端看板实时监控执行进度")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(import_from_docs_1txt())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] 导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
