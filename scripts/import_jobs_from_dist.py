"""
从 dist 目录的 jobs.txt 导入任务到数据库

处理格式：序号\t注册证号
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
from sqlalchemy import select


async def import_jobs():
    """导入任务"""

    # 读取文件
    file_path = project_root / "dist" / "browser-automation-platform" / "import_data" / "jobs.txt"

    if not file_path.exists():
        print(f"[ERROR] 文件不存在: {file_path}")
        return

    print("="*80)
    print("批量导入国家医保局注册证号查询任务")
    print("="*80)
    print(f"\n文件路径: {file_path}")

    # 读取并解析注册证号
    registration_numbers = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 处理格式：序号\t注册证号
            parts = line.split('\t')
            if len(parts) >= 2:
                reg_no = parts[1].strip()
                registration_numbers.append(reg_no)
            else:
                # 如果没有制表符，直接作为注册证号
                registration_numbers.append(line)

    print(f"读取到 {len(registration_numbers)} 个注册证号")

    if not registration_numbers:
        print("[ERROR] 没有找到有效的注册证号")
        return

    # 显示前5个和后5个
    print("\n前5个注册证号:")
    for i, reg_no in enumerate(registration_numbers[:5], 1):
        print(f"  {i}. {reg_no}")

    if len(registration_numbers) > 10:
        print("  ...")
        print(f"\n后5个注册证号:")
        for i, reg_no in enumerate(registration_numbers[-5:], len(registration_numbers)-4):
            print(f"  {i}. {reg_no}")

    # 确认导入（支持自动确认）
    if '--yes' in sys.argv or '-y' in sys.argv:
        print(f"\n自动确认: 导入 {len(registration_numbers)} 个任务")
    else:
        confirm = input(f"\n确认导入 {len(registration_numbers)} 个任务？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return

    # 开始导入
    async with get_session() as session:
        # 查找配置（直接按ID降序获取最新的）
        result = await session.execute(
            select(CrawlerConfig)
            .order_by(CrawlerConfig.id.desc())
            .limit(1)
        )
        config = result.scalars().first()

        if not config:
            print("\n[ERROR] 数据库中没有任何配置")
            print("\n请先运行初始化脚本：")
            print("python scripts/init_nhsa_registration_config.py")
            return

        # 验证配置名称
        if '国家医保局' not in config.config_name and 'NHSA' not in config.config_name.upper():
            print(f"\n[WARNING] 找到的配置可能不是NHSA配置: {config.config_name}")
            print("但仍将使用该配置继续...")

        print(f"\n使用配置: {config.config_name} (ID: {config.id})")
        print("\n开始创建任务...")

        created_jobs = []

        for idx, reg_no in enumerate(registration_numbers, 1):
            # 创建任务
            job = JobQueue(
                config_id=config.id,
                query_params={
                    "registration_no": reg_no
                },
                status="pending"
            )
            session.add(job)
            await session.flush()  # 获取 job.id

            created_jobs.append(job.id)

            # 每100个显示一次进度
            if idx % 100 == 0 or idx == len(registration_numbers):
                print(f"[{idx}/{len(registration_numbers)}] 已创建 {len(created_jobs)} 个任务")

        await session.commit()

        print(f"\n✓ 成功创建 {len(created_jobs)} 个任务")
        print(f"✓ 任务ID范围: {min(created_jobs)} - {max(created_jobs)}")

        print("\n" + "="*80)
        print("任务已创建，可以通过以下方式执行：")
        print("="*80)

        print("\n方法1：通过前端看板")
        print("  访问: http://127.0.0.1:8000/static/index.html")

        print("\n方法2：自动调度（推荐）")
        print("  调度器会自动执行 pending 状态的任务")
        print("  确保服务正在运行: python -m app.main")

        print("\n方法3：手动触发（用于测试）")
        print(f"  curl -X POST http://127.0.0.1:8000/api/jobs/{min(created_jobs)}/execute")

        print("\n" + "="*80)


if __name__ == "__main__":
    try:
        asyncio.run(import_jobs())
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n[ERROR] 导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
