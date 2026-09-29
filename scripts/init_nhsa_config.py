"""
医保局配置初始化脚本

创建医保局医用耗材信息采集配置（包含详情采集功能）

使用方法：
运行：python scripts/init_nhsa_config.py

注意：选择器需要实际测试后调整
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig


async def init_nhsa_config():
    """初始化医保局配置"""

    print("开始创建医保局配置...")

    config = CrawlerConfig(
        config_name="医保局-医用耗材信息",
        target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
        need_login=False,

        # 输入配置
        input_configs={
            "inputs": [
                {
                    "selector": "#registrationNumber",
                    "param_key": "registration_number",
                    "input_type": "text"
                }
            ]
        },

        # 提交和等待
        submit_selector="#searchBtn",
        wait_selector="table#jqGrid tbody tr",

        # 字段映射（需实际测试后调整）
        fields_mapping={
            "iframe_levels": 2,
            "iframe1_selector": "#iframe1",
            "iframe2_selector": "#contentIframe",

            "list_selector": "table#jqGrid tbody tr",
            "fields": [
                {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
                {"name": "医保编码", "selector": "td:nth-child(2)", "attr": "text"},
                {"name": "产品名称", "selector": "td:nth-child(3)", "attr": "text"},
                {"name": "注册证号", "selector": "td:nth-child(4)", "attr": "text"},
                {"name": "规格", "selector": "td:nth-child(5)", "attr": "text"},
                {"name": "型号", "selector": "td:nth-child(6)", "attr": "text"}
            ],

            "detail_config": {
                "enabled": True,
                "detail_button_selector": "a.detail-link",
                "wait_selector": ".modal-body",
                "detail_iframe_selector": "#detailIframe",
                "fields": [
                    {"name": "注册人名称", "selector": ".registrant-name", "attr": "text"},
                    {"name": "生产企业名称", "selector": ".manufacturer-name", "attr": "text"},
                    {"name": "生产地址", "selector": ".address", "attr": "text"},
                    {"name": "产品标准", "selector": ".standard", "attr": "text"},
                    {"name": "产品描述", "selector": ".description", "attr": "text"}
                ],
                "close_method": "auto",
                "close_selector": ".close-btn",
                "timeout": {
                    "click": 10000,
                    "wait_selector": 5000,
                    "iframe_load": 10000,
                    "close": 5000
                },
                "retry": {
                    "max_attempts": 3,
                    "delay_seconds": 2
                }
            }
        },

        # 分页配置
        pagination_selector="#next_page",
        max_pages=5,

        # 超时配置
        timeout_config={
            "page_load": 30000,
            "wait_selector": 15000,
            "click": 10000
        }
    )

    async with get_session() as session:
        session.add(config)
        await session.commit()
        await session.refresh(config)

        print("\n" + "="*60)
        print("✓ 配置创建成功")
        print("="*60)
        print(f"配置 ID: {config.id}")
        print(f"配置名称: {config.config_name}")
        print(f"目标 URL: {config.target_url}")
        print(f"详情采集: {'启用' if config.fields_mapping.get('detail_config', {}).get('enabled') else '禁用'}")
        print()
        print("下一步:")
        print(f"1. 访问 http://localhost:8000/static/config_manager.html?id={config.id}")
        print("2. 根据实际网站结构调整选择器")
        print("3. 点击「测试配置」验证")
        print("4. 确认无误后保存配置")
        print("="*60)

        return config.id


if __name__ == "__main__":
    try:
        config_id = asyncio.run(init_nhsa_config())
    except Exception as e:
        print(f"\n✗ 配置创建失败: {e}")
        sys.exit(1)
