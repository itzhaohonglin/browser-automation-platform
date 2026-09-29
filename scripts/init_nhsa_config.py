"""
国家医保局医用耗材查询配置初始化脚本

根据 docs/nhsa_medical_config.md 实际网站结构创建配置

使用方法：
运行：python scripts/init_nhsa_config.py

测试查询参数：
{"medical_code": "C01010100113038"}
预期结果：2条记录
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
    """初始化国家医保局配置"""

    print("开始创建国家医保局配置...")

    config = CrawlerConfig(
        config_name="国家医保局-医用耗材信息查询",
        target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
        need_login=False,

        # 输入配置
        input_configs=[
            {
                "selector": "input[name='specificationCode']",
                "param_name": "medical_code",
                "label": "医用耗材代码",
                "required": True,
                "iframe_levels": 2,
                "iframe1_selector": "iframe#dataInfo",
                "iframe2_selector": "iframe.els-iframe.active"
            }
        ],

        # 提交和等待
        submit_selector="button:has-text('查询')",
        wait_selector=".ui-jqgrid-btable",

        # 字段映射
        fields_mapping={
            "iframe_levels": 2,
            "iframe1_selector": "iframe#dataInfo",
            "iframe2_selector": "iframe.els-iframe.active",
            "table_selector": ".ui-jqgrid-btable",
            "row_selector": "tbody tr.jqgrow",
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

            # 禁用详情采集（NHSA无详情页）
            "detail_config": {
                "enabled": False
            }
        },

        # 分页配置（无分页）
        pagination_selector=None,
        max_pages=1,

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
        print("[OK] 配置创建成功")
        print("="*60)
        print(f"配置 ID: {config.id}")
        print(f"配置名称: {config.config_name}")
        print(f"目标 URL: {config.target_url}")
        print(f"详情采集: {'启用' if config.fields_mapping.get('detail_config', {}).get('enabled') else '禁用'}")
        print(f"字段数量: {len(config.fields_mapping['fields'])} 个")
        print()
        print("测试命令:")
        print(f'curl -X POST http://127.0.0.1:8000/api/jobs -H "Content-Type: application/json" -d \'{{"config_id": {config.id}, "query_params": {{"medical_code": "C01010100113038"}}}}\'')
        print()
        print("下一步:")
        print("1. 启动服务: uvicorn app.main:app --reload")
        print("2. 执行测试查询（预期返回2条记录）")
        print("3. 查看结果: http://127.0.0.1:8000/static/index.html")
        print("="*60)

        return config.id


if __name__ == "__main__":
    try:
        config_id = asyncio.run(init_nhsa_config())
    except Exception as e:
        print(f"\n[ERROR] 配置创建失败: {e}")
        sys.exit(1)
