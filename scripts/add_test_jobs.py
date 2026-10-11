"""批量添加测试任务到现有配置"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.job import JobQueue


async def add_test_jobs():
    """为配置 ID=3 添加测试任务"""

    # 测试注册证号列表
    test_registration_numbers = [
        "滇械注准20192140008",
        "京械注准20210001234",
        "沪械注准20200005678",
        "粤械注准20190012345",
        "川械注准20180009876"
    ]

    config_id = 3  # NHSA 配置 ID

    async with get_session() as session:
        print(f"准备为配置 ID={config_id} 添加 {len(test_registration_numbers)} 个任务")

        created_jobs = []
        for reg_no in test_registration_numbers:
            job = JobQueue(
                config_id=config_id,
                query_params={"registration_no": reg_no}
            )
            session.add(job)
            created_jobs.append(reg_no)

        await session.commit()

        print(f"\n✅ 成功创建 {len(created_jobs)} 个任务:")
        for idx, reg_no in enumerate(created_jobs, 1):
            print(f"  {idx}. {reg_no}")

        print(f"\n执行任务:")
        print(f"1. 前端看板: http://127.0.0.1:8000/static/index.html")
        print(f"2. API 接口: POST http://127.0.0.1:8000/api/jobs/{{job_id}}/execute")


if __name__ == "__main__":
    asyncio.run(add_test_jobs())
