"""
修复配置的按钮选择器（避免中文编码问题）
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig


async def fix_submit_selector():
    """修复按钮选择器"""

    async with get_session() as session:
        config = await session.get(CrawlerConfig, 14)

        if not config:
            print("Config 14 not found")
            return

        print(f"Current submit_selector: {config.submit_selector}")

        # 使用更通用的选择器（避免中文编码问题）
        config.submit_selector = "button[type='button'].btn-primary, button.search-btn, input[type='submit']"

        await session.commit()

        print(f"Fixed! New selector: {config.submit_selector}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(fix_submit_selector())
