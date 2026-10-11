"""
快速创建测试任务
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from app.core.database import get_session
from app.models.job import JobQueue


async def create_test_jobs():
    """创建3个测试任务"""

    # 测试用的注册证号
    test_registration_numbers = [
        "国械注准20183130456",
        "国械注准20183130457",
        "国械注准20183130458"
    ]

    print("\n" + "="*60)
    print("  创建测试任务")
    print("="*60 + "\n")

    async with get_session() as db:
        # 首先验证配置是否存在
        from app.models.config import CrawlerConfig
        from sqlalchemy import select

        stmt = select(CrawlerConfig).where(CrawlerConfig.is_active == True)
        result = await db.execute(stmt)
        configs = result.scalars().all()

        if not configs:
            print("[错误] 数据库中没有可用的配置")
            print("\n请先运行初始化脚本：")
            print("  python scripts/init_nhsa_registration_config.py")
            return

        # 使用第一个可用配置
        config = configs[0]
        config_id = config.id

        print(f"配置ID: {config_id}")
        print(f"配置名称: {config.config_name}")
        print(f"任务数量: {len(test_registration_numbers)}\n")

        job_ids = []

        for i, reg_no in enumerate(test_registration_numbers, 1):
            print(f"[{i}/{len(test_registration_numbers)}] 创建任务: {reg_no}")

            job = JobQueue(
                config_id=config_id,
                query_params={"registration_no": reg_no}
            )
            db.add(job)
            await db.flush()
            job_ids.append(job.id)
            print(f"  任务ID: {job.id}")

        await db.commit()

        print("\n" + "="*60)
        print("  任务创建完成！")
        print("="*60 + "\n")

        print("执行任务的方式：\n")

        print("1. 通过 API 文档（推荐）")
        print("   访问: http://127.0.0.1:8000/docs")
        print("   找到 POST /task/run 接口")
        print(f"   参数: config_id={config_id}, limit=1")
        print()

        print("2. 通过命令行")
        print(f"   curl -X POST \"http://127.0.0.1:8000/task/run?config_id={config_id}&limit=1\"")
        print()

        print("3. 通过 Python 脚本")
        print(f"   python scripts/execute_job_manual.py --config-id {config_id} --limit 1")
        print()

        print(f"已创建任务ID: {min(job_ids)} - {max(job_ids)}")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(create_test_jobs())
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n[ERROR] 创建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
