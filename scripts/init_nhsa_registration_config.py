"""
国家医保局医用耗材查询配置初始化脚本（带详情采集）

查询方式：注册证号查询
测试注册证号：滇械注准20192140008

功能：
1. 列表数据采集（医用耗材基本信息）
2. 详情数据采集（注册证详细信息）

使用方法：
python scripts/init_nhsa_registration_config.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue


async def init_nhsa_registration_config():
    """初始化国家医保局注册证号查询配置（带详情）"""

    print("="*80)
    print("国家医保局 - 注册证号查询配置（带详情采集）")
    print("="*80)

    config = CrawlerConfig(
        config_name="国家医保局-注册证号查询（含详情）",
        target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
        need_login=False,

        # 输入配置（注册证号查询）
        input_configs=[
            {
                "selector": "input[name='zczbh']",  # 注册证号输入框
                "param_name": "registration_no",
                "label": "注册证号",
                "required": True
            }
        ],

        # 提交和等待
        submit_selector="button:has-text('查询')",
        wait_selector=".ui-jqgrid-btable",

        # 字段映射（列表数据 + 详情配置）
        fields_mapping={
            # iframe配置
            "iframe_levels": 2,
            "iframe1_selector": "iframe#dataInfo",
            "iframe2_selector": "iframe.els-iframe.active",

            # 列表选择器
            "list_selector": "tbody tr.jqgrow",

            # 列表字段
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

            # 详情采集配置
            "detail_config": {
                "enabled": True,  # 启用详情采集

                # 详情按钮定位
                "detail_button_selector": "a:has-text('详情')",

                # 详情iframe（需要根据实际情况调整）
                # 可能在dialog弹窗中，也可能是独立iframe
                "detail_iframe_selector": "iframe[src*='detail']",

                # 等待详情内容加载
                "wait_selector": "table, .detail-content, .form-group",

                # 详情字段配置（根据实际页面结构调整）
                "fields": [
                    {"name": "注册证号", "selector": "input[name='zczbh'], td:contains('注册证号') + td", "attr": "text"},
                    {"name": "产品名称", "selector": "input[name='productName'], td:contains('产品名称') + td", "attr": "text"},
                    {"name": "规格型号", "selector": "input[name='specification'], td:contains('规格型号') + td", "attr": "text"},
                    {"name": "注册人名称", "selector": "input[name='registrant'], td:contains('注册人') + td", "attr": "text"},
                    {"name": "生产地址", "selector": "input[name='productionAddress'], td:contains('生产地址') + td", "attr": "text"},
                    {"name": "产品标准", "selector": "input[name='productStandard'], td:contains('产品标准') + td", "attr": "text"},
                    {"name": "适用范围", "selector": "textarea[name='scope'], td:contains('适用范围') + td", "attr": "text"}
                ],

                # 关闭详情窗口
                "close_method": "auto",  # 自动选择（优先按钮，失败用ESC）
                "close_selector": "button:has-text('关闭'), button:has-text('取消'), .close-btn",

                # 重试配置
                "retry": {
                    "max_attempts": 3,
                    "delay_seconds": 2
                },

                # 超时配置
                "timeout": {
                    "click": 10000,
                    "iframe_load": 10000,
                    "wait_selector": 5000,
                    "close": 5000
                }
            }
        },

        # 分页配置（暂不支持，先单页测试）
        pagination_selector=None,
        max_pages=1,

        # 超时配置
        timeout_config={
            "page_load": 30000,
            "wait_selector": 15000,
            "click": 10000
        },

        # 提取配置
        extraction_config={
            "wait_times": {
                "before_extraction": 3000,
                "after_click": 1000,
                "between_pages": 2000
            },
            "retry": {
                "max_attempts": 2,
                "delay_seconds": 3
            }
        }
    )

    async with get_session() as session:
        # 创建配置
        session.add(config)
        await session.commit()
        await session.refresh(config)

        print(f"\n✓ 配置已创建，ID: {config.id}")

        # 创建测试任务
        test_job = JobQueue(
            config_id=config.id,
            query_params={
                "registration_no": "滇械注准20192140008"
            }
        )
        session.add(test_job)
        await session.commit()
        await session.refresh(test_job)

        print(f"✓ 测试任务已创建，ID: {test_job.id}")

        print("\n" + "="*80)
        print("配置详情")
        print("="*80)
        print(f"配置名称: {config.config_name}")
        print(f"查询方式: 注册证号查询")
        print(f"测试参数: registration_no=滇械注准20192140008")
        print(f"详情采集: ✓ 已启用")
        print(f"列表字段: {len(config.fields_mapping['fields'])} 个")
        print(f"详情字段: {len(config.fields_mapping['detail_config']['fields'])} 个")

        print("\n" + "="*80)
        print("执行测试")
        print("="*80)
        print("\n方法1：API接口")
        print(f"curl -X POST http://127.0.0.1:8000/api/jobs/{test_job.id}/execute")

        print("\n方法2：前端看板")
        print("访问: http://127.0.0.1:8000/static/index.html")
        print(f"找到任务 ID: {test_job.id}，点击执行")

        print("\n方法3：直接创建任务并执行")
        print(f'curl -X POST http://127.0.0.1:8000/api/jobs \\')
        print(f'  -H "Content-Type: application/json" \\')
        print(f'  -d \'{{"config_id": {config.id}, "query_params": {{"registration_no": "滇械注准20192140008"}}}}\'')

        print("\n" + "="*80)
        print("调试说明")
        print("="*80)
        print("\n由于无法实际访问网站，以下选择器可能需要调整：")
        print("1. detail_button_selector - 详情按钮位置")
        print("2. detail_iframe_selector - 详情弹窗iframe")
        print("3. detail fields[].selector - 详情字段选择器")
        print("\n调试方法：")
        print("1. 执行任务后查看日志，找到失败的选择器")
        print("2. 使用浏览器开发者工具检查实际HTML结构")
        print("3. 修改 crawler_configs 表中的 fields_mapping.detail_config")
        print("4. 重新执行任务")
        print("\n详细调试指南：docs/detail_extraction_debug_guide.md")

        print("\n" + "="*80)
        print("数据结构预览")
        print("="*80)
        print("""
{
  "items": [
    {
      "list_data": {
        "序号": "1",
        "医用耗材代码": "...",
        "耗材名称": "..."
      },
      "detail_data": {
        "注册证号": "滇械注准20192140008",
        "产品名称": "...",
        "规格型号": "..."
      },
      "detail_status": "success"
    }
  ],
  "summary": {
    "total_items": 5,
    "detail_success": 5,
    "detail_failed": 0
  }
}
        """)

        print("="*80)
        print("初始化完成！")
        print("="*80)

        return config.id, test_job.id


if __name__ == "__main__":
    try:
        config_id, job_id = asyncio.run(init_nhsa_registration_config())
        print(f"\n配置ID: {config_id}")
        print(f"任务ID: {job_id}")
    except Exception as e:
        print(f"\n[ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
