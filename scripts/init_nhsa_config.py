"""
医保局医疗器械编码查询配置初始化脚本

用途：创建医保局网站的爬虫配置和测试任务

运行：
    python -m scripts.init_nhsa_config
"""

import asyncio
import sys
from pathlib import Path

# 设置 Windows 控制台编码
if sys.platform == "win32":
    import os
    os.system("chcp 65001 > nul 2>&1")

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue


async def init_nhsa_config():
    """初始化医保局网站配置"""

    async with get_session() as session:
        try:
            # 检查配置是否已存在
            stmt = select(CrawlerConfig).where(
                CrawlerConfig.config_name == "医保局医疗器械编码查询"
            )
            result = await session.execute(stmt)
            existing_config = result.scalar_one_or_none()

            if existing_config:
                print(f"配置已存在，ID: {existing_config.id}")
                config_id = existing_config.id
            else:
                # 创建配置
                config = CrawlerConfig(
                    config_name="医保局医疗器械编码查询",
                    target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
                    need_login=False,
                    input_configs={
                        "inputs": [
                            {
                                "selector": "#regcardNm",
                                "param_key": "register_no",
                                "input_type": "text"
                            }
                        ]
                    },
                    submit_selector="#search",
                    wait_selector="#gridlist tbody tr",
                    pagination_selector="#next_gridpage",
                    max_pages=2,  # 默认2页，可根据需要调整
                    fields_mapping={
                        "iframe_levels": 2,
                        "iframe1_selector": "iframe[name='mainFrame']",
                        "iframe2_selector": "iframe[name='contentFrame']",
                        "list_selector": "#gridlist tbody tr",
                        "fields": [
                            {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
                            {"name": "医疗器械编码", "selector": "td:nth-child(2)", "attr": "text"},
                            {"name": "医疗器械名称", "selector": "td:nth-child(3)", "attr": "text"},
                            {"name": "注册证号", "selector": "td:nth-child(4)", "attr": "text"}
                        ],
                        "detail_config": {
                            "enabled": True,
                            "detail_button_selector": "td:nth-child(5) a",
                            "detail_iframe_selector": "iframe#detailIframe",
                            "wait_selector": ".detail-table",
                            "close_method": "escape",
                            "fields": [
                                {"name": "产品名称", "selector": "#productName", "attr": "text"},
                                {"name": "型号规格", "selector": "#specification", "attr": "text"},
                                {"name": "注册人名称", "selector": "#registrant", "attr": "text"},
                                {"name": "注册人住所", "selector": "#address", "attr": "text"},
                                {"name": "生产地址", "selector": "#productionAddress", "attr": "text"}
                            ],
                            "retry": {
                                "max_attempts": 3,
                                "delay_seconds": 2
                            },
                            "timeout": {
                                "iframe_load": 10000,
                                "wait_selector": 5000
                            }
                        }
                    },
                    is_active=True,
                    priority=5
                )

                session.add(config)
                await session.commit()
                await session.refresh(config)

                print(f"[OK] 配置已创建，ID: {config.id}")
                config_id = config.id

            # 创建测试任务
            job = JobQueue(
                config_id=config_id,
                query_params={"register_no": "川械注准20182170152"},
                priority=5
            )

            session.add(job)
            await session.commit()
            await session.refresh(job)

            print(f"[OK] 测试任务已创建，ID: {job.id}")
            print(f"\n可通过以下方式执行测试：")
            print(f"  1. API接口：curl -X POST http://localhost:8000/api/jobs/{job.id}/execute")
            print(f"  2. 前端看板：http://localhost:8000/static/index.html")
            print(f"\n注意：")
            print(f"  - 首次运行请手动调整 detail_config 中的选择器")
            print(f"  - 建议先在浏览器开发者工具中确认实际的HTML结构")

        except Exception as e:
            print(f"[ERROR] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("医保局医疗器械编码查询配置初始化")
    print("=" * 60)

    asyncio.run(init_nhsa_config())

    print("\n初始化完成！")
