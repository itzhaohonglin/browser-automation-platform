"""
完整更新详情采集配置
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy.orm import attributes

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig


async def update_detail_config():
    """完整更新详情配置"""

    async with get_session() as session:
        config = await session.get(CrawlerConfig, 14)

        if not config:
            print("Config 14 not found")
            return

        # 复制整个字典
        fields_mapping = dict(config.fields_mapping)

        # 更新详情配置
        fields_mapping['detail_config'] = {
            "enabled": True,
            "detail_button_selector": "a[aria-describedby*='详情']",
            "click_method": "javascript",  # 使用JavaScript点击
            "detail_iframe_selector": "iframe.artDialog-iframe",  # 正确的iframe选择器
            "wait_selector": "table, .content, div",
            "close_method": "auto",
            "close_selector": "button.ui-dialog-close, .close-btn",
            "retry": {
                "max_attempts": 3,
                "delay_seconds": 2
            },
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

        # 重新赋值
        config.fields_mapping = fields_mapping
        attributes.flag_modified(config, 'fields_mapping')

        await session.commit()

        print("Updated detail_config:")
        print(f"  detail_button_selector: {fields_mapping['detail_config']['detail_button_selector']}")
        print(f"  click_method: {fields_mapping['detail_config']['click_method']}")
        print(f"  detail_iframe_selector: {fields_mapping['detail_config']['detail_iframe_selector']}")

        # 验证
        await session.refresh(config)
        dc = config.fields_mapping.get('detail_config', {})
        print(f"\nVerified:")
        print(f"  click_method: {dc.get('click_method')}")
        print(f"  iframe: {dc.get('detail_iframe_selector')}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(update_detail_config())
