"""
修复配置ID 14的输入选择器
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig


async def fix_config():
    """修复配置"""

    async with get_session() as session:
        # 获取配置
        config = await session.get(CrawlerConfig, 14)

        if not config:
            print("Config 14 not found")
            return

        print(f"Current config: {config.config_name}")
        print(f"Current input selector: {config.input_configs[0]['selector']}")

        # 修复选择器
        config.input_configs = [
            {
                "selector": "input[name='regcardNm']",  # 正确的选择器
                "param_name": "registration_no",
                "label": "注册证号",
                "required": True
            }
        ]

        await session.commit()

        print(f"\nFixed! New selector: input[name='regcardNm']")
        print(f"\nNow create a new job and execute it:")
        print(f"  python scripts/create_job_id14.py")
        print(f"  python scripts/execute_job_direct.py 10")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(fix_config())
