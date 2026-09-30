"""
SQL Server CRUD 测试
测试所有模型的创建、读取、更新、删除操作
"""
import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, '.')

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus
from app.models.result import CrawlerResult


async def test_crawler_config_crud():
    """测试 CrawlerConfig CRUD 操作"""
    print("\n=== 测试 CrawlerConfig CRUD ===")

    async with AsyncSessionLocal() as session:
        # CREATE
        config = CrawlerConfig(
            config_name="测试配置",
            target_url="https://test.com",
            need_login=False,
            input_configs=[{"selector": "#input", "param_name": "query"}],
            submit_selector="#submit",
            wait_selector="#results",
            fields_mapping={"list_selector": ".item", "fields": [{"name": "title", "selector": ".title"}]},
            max_pages=3,
            priority=5,
            is_active=True
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        config_id = config.id
        print(f"[OK] CREATE: 创建配置 ID={config_id}")

        # READ
        result = await session.execute(select(CrawlerConfig).where(CrawlerConfig.id == config_id))
        config = result.scalar_one()
        assert config.id == config_id
        assert len(config.input_configs) == 1
        assert config.fields_mapping["list_selector"] == ".item"
        print(f"[OK] READ: 读取配置 ID={config_id}")

        # UPDATE
        config.max_pages = 10
        config.is_active = False
        await session.commit()
        print(f"[OK] UPDATE: 更新配置 ID={config_id}")

        # 验证更新
        await session.refresh(config)
        assert config.max_pages == 10
        assert config.is_active == False
        print(f"[OK] UPDATE VERIFY: 验证更新成功")

        # DELETE (soft delete)
        config.deleted_at = datetime.now()
        await session.commit()
        print(f"[OK] DELETE: 软删除配置 ID={config_id}")


async def test_job_queue_crud():
    """测试 JobQueue CRUD 操作"""
    print("\n=== 测试 JobQueue CRUD ===")

    async with AsyncSessionLocal() as session:
        # 首先创建一个配置
        config = CrawlerConfig(
            config_name="任务测试配置",
            target_url="https://test.com",
            need_login=False,
            input_configs=[],
            submit_selector="#submit",
            wait_selector="#results",
            fields_mapping={},
            max_pages=1
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)

        # CREATE
        job = JobQueue(
            config_id=config.id,
            query_params={"keyword": "test", "date": "2024-01-01"},
            status=JobStatus.PENDING,
            priority=5
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id
        print(f"[OK] CREATE: 创建任务 ID={job_id}")

        # READ
        result = await session.execute(select(JobQueue).where(JobQueue.id == job_id))
        job = result.scalar_one()
        assert job.query_params["keyword"] == "test"
        assert job.status == JobStatus.PENDING
        print(f"[OK] READ: 读取任务 ID={job_id}")

        # UPDATE
        job.status = JobStatus.PROCESSING
        job.retry_count = 1
        await session.commit()
        print(f"[OK] UPDATE: 更新任务状态")

        # 验证更新
        await session.refresh(job)
        assert job.status == JobStatus.PROCESSING
        assert job.retry_count == 1
        print(f"[OK] UPDATE VERIFY: 验证更新成功")

        # DELETE
        await session.delete(job)
        await session.delete(config)
        await session.commit()
        print(f"[OK] DELETE: 删除任务和配置")


async def test_crawler_result_crud():
    """测试 CrawlerResult CRUD 操作"""
    print("\n=== 测试 CrawlerResult CRUD ===")

    async with AsyncSessionLocal() as session:
        # 创建配置和任务
        config = CrawlerConfig(
            config_name="结果测试配置",
            target_url="https://test.com",
            need_login=False,
            input_configs=[],
            submit_selector="#submit",
            wait_selector="#results",
            fields_mapping={},
            max_pages=1
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)

        job = JobQueue(
            config_id=config.id,
            query_params={"keyword": "result_test"},
            status=JobStatus.PROCESSING,
            priority=5
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        # CREATE
        result = CrawlerResult(
            job_id=job.id,
            config_id=config.id,
            query_params={"keyword": "result_test"},
            extracted_data=[
                {"title": "结果1", "url": "http://test1.com"},
                {"title": "结果2", "url": "http://test2.com"}
            ]
        )
        session.add(result)
        await session.commit()
        await session.refresh(result)
        result_id = result.id
        print(f"[OK] CREATE: 创建结果 ID={result_id}")

        # READ
        db_result = await session.execute(select(CrawlerResult).where(CrawlerResult.id == result_id))
        result = db_result.scalar_one()
        assert len(result.extracted_data) == 2
        assert result.extracted_data[0]["url"] == "http://test1.com"
        print(f"[OK] READ: 读取结果 ID={result_id}")

        # UPDATE
        new_data = result.extracted_data.copy()
        new_data.append({"title": "结果3", "url": "http://test3.com"})
        result.extracted_data = new_data
        await session.commit()
        print(f"[OK] UPDATE: 追加结果数据")

        # 验证更新
        await session.refresh(result)
        assert len(result.extracted_data) == 3
        print(f"[OK] UPDATE VERIFY: 验证更新成功")

        # DELETE
        await session.delete(result)
        await session.delete(job)
        await session.delete(config)
        await session.commit()
        print(f"[OK] DELETE: 删除结果、任务和配置")


async def test_json_complex_data():
    """测试复杂 JSON 数据"""
    print("\n=== 测试复杂 JSON 数据 ===")

    async with AsyncSessionLocal() as session:
        # 创建包含复杂 JSON 的配置
        config = CrawlerConfig(
            config_name="复杂JSON测试",
            target_url="https://complex.com",
            need_login=True,
            auth_profile="test_profile",
            input_configs=[
                {
                    "label": "输入框1",
                    "selector": "#input1",
                    "param_name": "param1",
                    "required": True,
                    "default_value": "默认值"
                },
                {
                    "label": "输入框2",
                    "selector": "#input2",
                    "param_name": "param2",
                    "required": False
                }
            ],
            submit_selector="#submit",
            wait_selector="#results",
            fields_mapping={
                "list_selector": ".item",
                "fields": [
                    {"name": "title", "selector": ".title", "attr": "text"},
                    {"name": "link", "selector": "a", "attr": "href"},
                    {"name": "date", "selector": ".date", "attr": "text"}
                ],
                "detail_config": {
                    "enabled": True,
                    "button_selector": ".detail-btn",
                    "fields": [
                        {"name": "content", "selector": ".content"}
                    ]
                }
            },
            timeout_config={
                "page_load": 30000,
                "wait_selector": 15000,
                "element_click": 5000
            },
            extraction_config={
                "filters": [
                    {"field": "title", "pattern": ".*test.*"}
                ],
                "retry": {
                    "max_attempts": 3,
                    "delay": 2
                }
            },
            max_pages=5
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)

        # 验证复杂 JSON 数据
        assert len(config.input_configs) == 2
        assert config.input_configs[0]["default_value"] == "默认值"
        assert config.fields_mapping["detail_config"]["enabled"] == True
        assert config.timeout_config["page_load"] == 30000
        assert config.extraction_config["retry"]["max_attempts"] == 3
        print(f"[OK] 复杂 JSON 数据存储和读取正常")

        # 清理
        await session.delete(config)
        await session.commit()


async def main():
    print("=" * 60)
    print("SQL Server 数据库 CRUD 测试")
    print("=" * 60)

    try:
        await test_crawler_config_crud()
        await test_job_queue_crud()
        await test_crawler_result_crud()
        await test_json_complex_data()

        print("\n" + "=" * 60)
        print("[SUCCESS] 所有测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
