"""
完整的配置更新脚本

使用方法：
1. 访问 https://code.nhsa.gov.cn/toSearch.html?sysflag=1004
2. 打开浏览器开发者工具 (F12)
3. 手动操作并记录选择器
4. 填写下面的选择器变量
5. 运行此脚本更新配置
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig


# ========================================
# 在这里填写正确的选择器（用户提供）
# ========================================

# 提交按钮选择器（查询按钮）
SUBMIT_SELECTOR = "#search"

# iframe选择器（如果有变化）
IFRAME1_SELECTOR = "iframe#dataInfo"
IFRAME2_SELECTOR = "iframe.els-iframe.active"

# 列表行选择器
LIST_SELECTOR = "tbody tr.jqgrow"

# 详情按钮选择器（在每一行中）
DETAIL_BUTTON_SELECTOR = "a[aria-describedby*='详情']"

# 详情iframe选择器
DETAIL_IFRAME_SELECTOR = "iframe.artDialog-iframe"


async def update_config():
    """更新配置"""

    async with get_session() as session:
        config = await session.get(CrawlerConfig, 14)

        if not config:
            print("ERROR: Config 14 not found")
            return

        print("="*80)
        print("当前配置")
        print("="*80)
        print(f"配置名称: {config.config_name}")
        print(f"输入框: {config.input_configs[0]['selector']}")
        print(f"提交按钮: {config.submit_selector}")
        print(f"等待选择器: {config.wait_selector}")
        print(f"iframe1: {config.fields_mapping.get('iframe1_selector')}")
        print(f"iframe2: {config.fields_mapping.get('iframe2_selector')}")
        print(f"列表选择器: {config.fields_mapping.get('list_selector')}")

        print("\n" + "="*80)
        print("更新配置")
        print("="*80)

        # 更新提交按钮
        config.submit_selector = SUBMIT_SELECTOR
        print(f"[OK] 提交按钮: {SUBMIT_SELECTOR}")

        # 更新iframe选择器
        config.fields_mapping["iframe1_selector"] = IFRAME1_SELECTOR
        config.fields_mapping["iframe2_selector"] = IFRAME2_SELECTOR
        print(f"[OK] iframe1: {IFRAME1_SELECTOR}")
        print(f"[OK] iframe2: {IFRAME2_SELECTOR}")

        # 更新列表选择器
        config.fields_mapping["list_selector"] = LIST_SELECTOR
        print(f"[OK] 列表: {LIST_SELECTOR}")

        # 更新详情配置
        if "detail_config" in config.fields_mapping:
            config.fields_mapping["detail_config"]["detail_button_selector"] = DETAIL_BUTTON_SELECTOR
            config.fields_mapping["detail_config"]["detail_iframe_selector"] = DETAIL_IFRAME_SELECTOR
            print(f"[OK] 详情按钮: {DETAIL_BUTTON_SELECTOR}")
            print(f"[OK] 详情iframe: {DETAIL_IFRAME_SELECTOR}")

        # 提交更改
        await session.commit()

        print("\n" + "="*80)
        print("配置更新成功！")
        print("="*80)
        print("\n下一步：")
        print("1. python scripts/create_job_id14.py")
        print("2. python scripts/execute_job_direct.py 12")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(update_config())
