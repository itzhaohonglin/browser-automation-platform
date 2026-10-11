"""
更新 Config 1 的详情配置为详情列表模式

根据实际页面结构，详情弹窗中包含一个表格，有多行数据需要采集。
更新配置以支持 detail_list_mode。
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from sqlalchemy.orm.attributes import flag_modified


async def update_config_detail_list():
    """更新配置为详情列表模式"""

    print("="*80)
    print("更新 Config 1 - 启用详情列表模式")
    print("="*80)

    async with get_session() as session:
        # 获取 Config 1
        config = await session.get(CrawlerConfig, 1)

        if not config:
            print("[ERROR] Config 1 不存在")
            return

        print(f"\n当前配置: {config.config_name}")
        print(f"Config ID: {config.id}")

        # 获取当前的 fields_mapping
        fields_mapping = config.fields_mapping.copy()

        # 更新输入框选择器（修正为正确的 name）
        if config.input_configs:
            input_configs = config.input_configs.copy()
            for input_cfg in input_configs:
                if input_cfg.get('selector') == "input[name='zczbh']":
                    input_cfg['selector'] = "input[name='regcardNm']"
                    print("\n[OK] 修正输入框选择器: input[name='regcardNm']")
            config.input_configs = input_configs
            flag_modified(config, "input_configs")

        # 更新提交按钮选择器
        config.submit_selector = "#search"
        print("[OK] 修正提交按钮选择器: #search")

        # 更新详情配置
        detail_config = fields_mapping.get('detail_config', {})

        # 启用详情列表模式
        detail_config['detail_list_mode'] = True
        detail_config['detail_list_selector'] = "tbody tr.jqgrow"

        # 更新详情iframe选择器（根据测试脚本验证的结果）
        detail_config['detail_iframe_selector'] = "iframe.artDialog-iframe"

        # 更新详情字段配置（8个字段，对应表格的8列）
        # 注意：第0列是序号，实际数据从第1列开始
        detail_config['fields'] = [
            {"name": "注册备案号", "selector": "td:nth-child(2)", "attr": "text"},
            {"name": "医保耗材分类编码", "selector": "td:nth-child(3)", "attr": "text"},
            {"name": "注册备案人", "selector": "td:nth-child(4)", "attr": "text"},
            {"name": "单件产品名称", "selector": "td:nth-child(5)", "attr": "text"},
            {"name": "企业名称", "selector": "td:nth-child(6)", "attr": "text"},
            {"name": "规格", "selector": "td:nth-child(7)", "attr": "text"},
            {"name": "型号", "selector": "td:nth-child(8)", "attr": "text"},
            {"name": "UDI-DI", "selector": "td:nth-child(9)", "attr": "text"}
        ]

        # 更新等待选择器（等待表格加载）
        detail_config['wait_selector'] = "tbody tr.jqgrow"

        # 更新关闭方法（使用键盘ESC更可靠）
        detail_config['close_method'] = "keyboard"

        # 更新 fields_mapping
        fields_mapping['detail_config'] = detail_config
        config.fields_mapping = fields_mapping
        flag_modified(config, "fields_mapping")

        await session.commit()

        print("\n" + "="*80)
        print("更新完成")
        print("="*80)

        print("\n详情配置更新内容：")
        print(f"  - detail_list_mode: True")
        print(f"  - detail_list_selector: {detail_config['detail_list_selector']}")
        print(f"  - detail_iframe_selector: {detail_config['detail_iframe_selector']}")
        print(f"  - 详情字段数量: {len(detail_config['fields'])}")
        print(f"  - 关闭方法: {detail_config['close_method']}")

        print("\n详情字段列表：")
        for i, field in enumerate(detail_config['fields'], 1):
            print(f"  {i}. {field['name']} - {field['selector']}")

        print("\n" + "="*80)
        print("测试建议")
        print("="*80)
        print("\n1. 执行测试任务：")
        print("   python scripts/execute_job_direct.py")
        print("\n2. 检查结果中的 detail_data 字段")
        print("   应该是一个数组，包含4条详情记录")
        print("\n3. 预期结构：")
        print("""
{
  "items": [
    {
      "list_data": {...},
      "detail_data": [
        {
          "注册备案号": "...",
          "医保耗材分类编码": "...",
          "注册备案人": "...",
          ...
        },
        {
          "注册备案号": "...",
          ...
        }
      ],
      "detail_status": "success"
    }
  ]
}
        """)

        print("="*80)


if __name__ == "__main__":
    try:
        asyncio.run(update_config_detail_list())
        print("\n[SUCCESS] 配置更新成功")
    except Exception as e:
        print(f"\n[ERROR] 更新失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
