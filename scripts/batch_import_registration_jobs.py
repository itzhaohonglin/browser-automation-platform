"""
批量导入国家医保局注册证号查询任务

功能：
1. 从文件或列表读取注册证号
2. 批量创建采集任务
3. 可选择立即执行或放入队列

使用方法：
python scripts/batch_import_registration_jobs.py
"""

import asyncio
import sys
from pathlib import Path
from typing import List

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue


async def import_registration_jobs(
    registration_numbers: List[str],
    config_id: int = None,
    auto_execute: bool = False
):
    """
    批量导入注册证号查询任务

    Args:
        registration_numbers: 注册证号列表
        config_id: 配置ID（默认None - 自动查找国家医保局注册证号查询配置）
        auto_execute: 是否立即执行任务
    """

    print("="*80)
    print("批量导入国家医保局注册证号查询任务")
    print("="*80)

    async with get_session() as session:
        # 如果未指定config_id，自动查找
        if config_id is None:
            from sqlalchemy import select
            # 先尝试按名称模糊匹配
            result = await session.execute(
                select(CrawlerConfig)
                .where(CrawlerConfig.config_name.like('%国家医保局%注册证号%'))
                .order_by(CrawlerConfig.id.desc())
            )
            config = result.scalars().first()

            # 如果模糊匹配失败（可能因为编码问题），使用最新的配置
            if not config:
                result = await session.execute(
                    select(CrawlerConfig)
                    .order_by(CrawlerConfig.id.desc())
                    .limit(1)
                )
                config = result.scalars().first()

            if not config:
                print("[ERROR] 未找到国家医保局注册证号查询配置")
                print("\n请先运行初始化脚本：")
                print("python scripts/init_nhsa_registration_config.py")
                return []
            config_id = config.id
            print(f"[INFO] 自动找到配置: {config.config_name} (ID: {config_id})")
        else:
            # 验证配置是否存在
            config = await session.get(CrawlerConfig, config_id)
            if not config:
                print(f"[ERROR] 配置ID {config_id} 不存在")
                print("\n请先运行初始化脚本：")
                print("python scripts/init_nhsa_registration_config.py")
                return []

        print(f"\n使用配置: {config.config_name} (ID: {config_id})")
        print(f"待导入数量: {len(registration_numbers)} 个注册证号")
        print()

        created_jobs = []

        for idx, reg_no in enumerate(registration_numbers, 1):
            # 创建任务
            job = JobQueue(
                config_id=config_id,
                query_params={
                    "registration_no": reg_no
                },
                status="pending"
            )
            session.add(job)
            await session.flush()  # 获取job.id

            print(f"[{idx}/{len(registration_numbers)}] 创建任务 ID={job.id}, 注册证号={reg_no}")
            created_jobs.append(job.id)

        await session.commit()

        print(f"\n✓ 成功创建 {len(created_jobs)} 个任务")
        print(f"✓ 任务ID范围: {min(created_jobs)} - {max(created_jobs)}")

        # 可选：立即执行
        if auto_execute:
            print("\n开始执行任务...")
            from app.services.executor import execute_job

            for job_id in created_jobs:
                try:
                    print(f"执行任务 {job_id}...")
                    await execute_job(job_id)
                except Exception as e:
                    print(f"[ERROR] 任务 {job_id} 执行失败: {e}")

        return created_jobs


async def import_from_file(file_path: str, config_id: int = None):
    """从文件导入注册证号（每行一个）"""

    file = Path(file_path)
    if not file.exists():
        print(f"[ERROR] 文件不存在: {file_path}")
        return []

    # 读取注册证号列表
    with open(file, 'r', encoding='utf-8') as f:
        registration_numbers = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#')
        ]

    if not registration_numbers:
        print("[ERROR] 文件中没有有效的注册证号")
        return []

    return await import_registration_jobs(registration_numbers, config_id)


async def main():
    """主函数"""

    print("\n请选择导入方式：")
    print("1. 从列表导入（适合少量测试）")
    print("2. 从文件导入（适合批量导入）")

    choice = input("\n请输入选择 (1/2): ").strip()

    if choice == "1":
        # 方式1：直接在代码中定义
        registration_numbers = [
            "滇械注准20192140008",
            # 在这里添加更多注册证号
            # "京械注准20210001234",
            # "沪械注准20200005678",
        ]

        print(f"\n准备导入 {len(registration_numbers)} 个注册证号")
        for i, reg_no in enumerate(registration_numbers, 1):
            print(f"  {i}. {reg_no}")

        confirm = input("\n确认导入？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return

        job_ids = await import_registration_jobs(registration_numbers)

    elif choice == "2":
        # 方式2：从文件导入
        file_path = input("\n请输入文件路径（每行一个注册证号）: ").strip()
        job_ids = await import_from_file(file_path)

    else:
        print("无效选择")
        return

    # 输出执行说明
    if job_ids:
        print("\n" + "="*80)
        print("执行任务")
        print("="*80)

        print("\n方法1：通过前端看板")
        print("访问: http://127.0.0.1:8000/static/index.html")
        print("找到对应任务，点击执行")

        print("\n方法2：通过API批量执行")
        print("for job_id in range({}, {}):".format(min(job_ids), max(job_ids) + 1))
        print("    curl -X POST http://127.0.0.1:8000/api/jobs/$job_id/execute")

        print("\n方法3：通过调度器自动执行")
        print("调度器会在每30分钟扫描pending状态的任务并执行")

        print("\n" + "="*80)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            # 非交互模式：从文件导入（客户端 exe --import-jobs 调用）
            job_ids = asyncio.run(import_from_file(sys.argv[1]))
            if not job_ids:
                sys.exit(1)
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n[ERROR] 导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
