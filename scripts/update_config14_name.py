"""
重新创建Config 14 - 国家医保局注册证号查询配置
使用修复后的数据库排序规则
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from sqlalchemy import select


async def recreate_config_14():
    """重新创建Config 14"""

    async with get_session() as session:
        # 检查是否已存在
        result = await session.execute(
            select(CrawlerConfig).where(CrawlerConfig.id == 14)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Config 14 已存在")
            print(f"  当前名称: {repr(existing.config_name)}")
            print(f"  创建时间: {existing.created_at}")

            # 更新名称
            existing.config_name = "国家医保局-注册证号查询（含详情）"
            await session.commit()

            print(f"\n已更新名称为: {existing.config_name}")
            print("请刷新HTML查看器验证中文是否正确")
        else:
            print("Config 14 不存在，需要重新创建")

            config = CrawlerConfig(
                config_name="国家医保局-注册证号查询（含详情）",
                target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
                need_login=False,
                input_configs=[
                    {
                        "selector": "input[name='regcardNm']",
                        "param_name": "registration_no",
                        "label": "注册证号",
                        "required": True
                    }
                ],
                submit_selector="#search",
                wait_selector=".ui-jqgrid-btable",
                fields_mapping={
                    "iframe_levels": 2,
                    "iframe1_selector": "iframe#dataInfo",
                    "iframe2_selector": "iframe.els-iframe.active",
                    "list_selector": "tbody tr.jqgrow",
                    "fields": [
                        {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
                        {"name": "医用耗材代码", "selector": "td:nth-child(2)", "attr": "text"},
                        {"name": "一级分类", "selector": "td:nth-child(3)", "attr": "text"},
                        {"name": "二级分类", "selector": "td:nth-child(4)", "attr": "text"},
                        {"name": "三级分类", "selector": "td:nth-child(5)", "attr": "text"},
                        {"name": "标准规格", "selector": "td:nth-child(6)", "attr": "text"},
                        {"name": "型号", "selector": "td:nth-child(7)", "attr": "text"},
                        {"name": "材质特征", "selector": "td:nth-child(8)", "attr": "text"},
                        {"name": "医疗器械分类", "selector": "td:nth-child(9)", "attr": "text"},
                        {"name": "医疗器械代码", "selector": "td:nth-child(10)", "attr": "text"},
                        {"name": "耗材名称", "selector": "td:nth-child(11)", "attr": "text"},
                        {"name": "生产企业", "selector": "td:nth-child(12)", "attr": "text"}
                    ],
                    "detail_config": {
                        "enabled": True,
                        "detail_button_selector": "a[onclick*='goodsDetail']",
                        "click_method": "javascript",
                        "detail_iframe_selector": "iframe.artDialog-iframe",
                        "wait_selector": "table, .content, div",
                        "close_method": "auto",
                        "close_selector": "button.ui-dialog-close, .close-btn",
                        "retry": {"max_attempts": 3, "delay_seconds": 2},
                        "timeout": {
                            "click": 10000,
                            "iframe_load": 10000,
                            "wait_selector": 5000,
                            "close": 5000
                        },
                        "fields": [
                            {"name": "序号", "selector": "td, div", "attr": "text"},
                            {"name": "产品名称", "selector": "td, div", "attr": "text"},
                            {"name": "规格型号", "selector": "td, div", "attr": "text"},
                            {"name": "注册人", "selector": "td, div", "attr": "text"},
                            {"name": "生产地址", "selector": "td, div", "attr": "text"},
                            {"name": "产品标准", "selector": "td, div", "attr": "text"},
                            {"name": "适用范围", "selector": "td, div", "attr": "text"}
                        ]
                    }
                },
                pagination_selector=None,
                max_pages=1,
                timeout_config={
                    "page_load": 30000,
                    "wait_selector": 15000,
                    "click": 10000
                },
                extraction_config={
                    "wait_times": {
                        "before_extraction": 3000,
                        "after_click": 1000,
                        "between_pages": 2000
                    },
                    "retry": {"max_attempts": 2, "delay_seconds": 3}
                },
                priority=5,
                is_active=True
            )

            session.add(config)
            await session.commit()
            await session.refresh(config)

            print(f"Config 已创建，ID: {config.id}")
            print(f"名称: {config.config_name}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(recreate_config_14())
