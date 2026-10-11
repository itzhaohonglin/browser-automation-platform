"""
修复详情采集 - 使用JavaScript点击
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig


async def fix_detail_click():
    """修复详情点击方法"""

    async with get_session() as session:
        config = await session.get(CrawlerConfig, 14)

        if not config:
            print("Config 14 not found")
            return

        # 启用JavaScript点击（避免遮挡问题）
        config.fields_mapping["detail_config"]["click_method"] = "javascript"

        await session.commit()

        print("Fixed! Detail click method set to 'javascript'")
        print("\nNow test again:")
        print("  python scripts/create_job_id14.py")
        print("  python scripts/execute_job_direct.py 13")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(fix_detail_click())
