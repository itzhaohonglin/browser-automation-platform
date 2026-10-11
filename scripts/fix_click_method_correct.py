"""
正确更新JSON字段中的click_method
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy.orm import attributes

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig


async def fix_click_method():
    """修复click_method"""

    async with get_session() as session:
        config = await session.get(CrawlerConfig, 14)

        if not config:
            print("Config 14 not found")
            return

        print(f"Current click_method: {config.fields_mapping.get('detail_config', {}).get('click_method', 'NOT SET')}")

        # 正确方式：复制整个字典，修改后重新赋值
        fields_mapping = dict(config.fields_mapping)
        if 'detail_config' not in fields_mapping:
            fields_mapping['detail_config'] = {}

        fields_mapping['detail_config']['click_method'] = 'javascript'

        # 重新赋值以触发SQLAlchemy的change tracking
        config.fields_mapping = fields_mapping

        # 标记为已修改
        attributes.flag_modified(config, 'fields_mapping')

        await session.commit()

        print(f"Fixed! click_method is now: javascript")

        # 验证
        await session.refresh(config)
        print(f"Verified: {config.fields_mapping.get('detail_config', {}).get('click_method', 'NOT SET')}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(fix_click_method())
