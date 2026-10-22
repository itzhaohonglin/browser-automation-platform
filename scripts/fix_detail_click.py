"""修复详情按钮点击问题：添加 JavaScript 点击方法"""
import asyncio
import sys
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified


async def fix_detail_click():
    """添加 click_method: 'javascript' 到详情配置"""
    # 设置输出编码
    sys.stdout.reconfigure(encoding='utf-8')

    async with get_session() as session:
        # 查询配置
        result = await session.execute(
            select(CrawlerConfig).where(CrawlerConfig.id == 1)
        )
        config = result.scalar_one_or_none()

        if not config:
            print("❌ 未找到配置 ID=1")
            return

        # 检查并更新 fields_mapping
        fields_mapping = config.fields_mapping
        if not fields_mapping:
            print("❌ fields_mapping 为空")
            return

        if 'detail_config' not in fields_mapping:
            print("❌ 未配置 detail_config")
            return

        # 添加 click_method
        fields_mapping['detail_config']['click_method'] = 'javascript'

        # 标记字段已修改（重要！）
        flag_modified(config, 'fields_mapping')

        await session.commit()

        print("✓ 已更新配置，添加 click_method: 'javascript'")
        print()
        print("更新后的 detail_config:")
        print(json.dumps(fields_mapping['detail_config'], ensure_ascii=False, indent=2))
        print()
        print("说明：")
        print("- JavaScript 点击方法可以绕过元素遮挡问题")
        print("- 适用于详情按钮被弹窗或 iframe 遮挡的情况")
        print("- 无需重启服务，配置立即生效")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(fix_detail_click())
